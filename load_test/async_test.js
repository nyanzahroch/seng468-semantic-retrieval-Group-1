import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8080';
const TEST_TYPE = (__ENV.TEST_TYPE || 'baseline').toLowerCase();
const QUERY = __ENV.SEARCH_QUERY || 'machine learning optimization';
const USER_PREFIX = __ENV.USER_PREFIX || 'user';
const PASS_PREFIX = __ENV.PASS_PREFIX || 'pass';

const UPLOADS_PER_ITER = Number(__ENV.UPLOADS_PER_ITER || 3);
const WAIT_FOR_INDEX = (__ENV.WAIT_FOR_INDEX || 'true').toLowerCase() === 'true';
const POLL_INTERVAL_MS = Number(__ENV.POLL_INTERVAL_MS || 2000);
const MAX_POLL_SEC = Number(__ENV.MAX_POLL_SEC || 180);
const THINK_TIME_SEC = Number(__ENV.THINK_TIME_SEC || 1);

const uploadAcceptedRate = new Rate('upload_accepted_rate');
const indexingReadyRate = new Rate('indexing_ready_rate');
const indexingWaitMs = new Trend('indexing_wait_ms');

const pdfs = [
  {
    name: 'Final_Project_SEng_468.pdf',
    data: open('../test_pdfs/Final_Project_SEng_468.pdf', 'b'),
  },
  {
    name: 'lab_commands.pdf',
    data: open('../test_pdfs/lab_commands.pdf', 'b'),
  },
];

function loadProfile() {
  if (TEST_TYPE === 'stress') {
    return {
      scenarios: {
        stress: {
          executor: 'constant-vus',
          vus: Number(__ENV.STRESS_VUS || 10),
          duration: __ENV.STRESS_DURATION || '3m',
        },
      },
    };
  }

  if (TEST_TYPE === 'spike') {
    return {
      scenarios: {
        spike: {
          executor: 'stages',
          stages: [
            { duration: __ENV.SPIKE_BASELINE_DURATION || '3m', target: Number(__ENV.SPIKE_BASELINE_VUS || 10) },
            { duration: __ENV.SPIKE_RAMP_UP_DURATION || '20s', target: Number(__ENV.SPIKE_VUS || 40) },
            { duration: __ENV.SPIKE_HOLD_DURATION || '60s', target: Number(__ENV.SPIKE_VUS || 40) },
            { duration: __ENV.SPIKE_RAMP_DOWN_DURATION || '20s', target: Number(__ENV.SPIKE_BASELINE_VUS || 10) },
            { duration: __ENV.SPIKE_RECOVERY_DURATION || '3m', target: Number(__ENV.SPIKE_BASELINE_VUS || 10) },
          ],
        },
      },
    };
  }

  return {
    scenarios: {
      baseline: {
        executor: 'constant-vus',
        vus: Number(__ENV.BASELINE_VUS || 10),
        duration: __ENV.BASELINE_DURATION || '20m',
      },
    },
  };
}

export const options = {
  ...loadProfile(),
  thresholds: {
    http_req_failed: ['rate<0.2'],
    checks: ['rate>0.95'],
    upload_accepted_rate: ['rate>0.95'],
    indexing_ready_rate: ['rate>0.8'],
  },
};

function safeJson(resp) {
  try {
    return JSON.parse(resp.body || '{}');
  } catch (err) {
    return {};
  }
}

function login(username, password) {
  const resp = http.post(
    `${BASE_URL}/auth/login`,
    JSON.stringify({ username, password }),
    {
      headers: { 'Content-Type': 'application/json' },
      tags: { endpoint: 'auth_login' },
    }
  );

  const ok = check(resp, {
    'login success': (r) => r.status === 200,
  });

  if (!ok) {
    return null;
  }

  return safeJson(resp).token || null;
}

function pollUntilIndexed(documentId, authHeaders) {
  const startedAt = Date.now();
  const maxMs = MAX_POLL_SEC * 1000;

  while (Date.now() - startedAt < maxMs) {
    const statusResp = http.get(`${BASE_URL}/documents/${documentId}/status`, {
      ...authHeaders,
      tags: { endpoint: 'documents_status' },
    });

    if (statusResp.status !== 200) {
      sleep(POLL_INTERVAL_MS / 1000);
      continue;
    }

    const body = safeJson(statusResp);
    const state = body.state || '';
    const status = body.status || '';

    if (state === 'SUCCESS' || status === 'ready') {
      indexingWaitMs.add(Date.now() - startedAt);
      indexingReadyRate.add(true);
      return true;
    }

    if (state === 'FAILURE' || status === 'failed') {
      indexingWaitMs.add(Date.now() - startedAt);
      indexingReadyRate.add(false);
      return false;
    }

    sleep(POLL_INTERVAL_MS / 1000);
  }

  indexingWaitMs.add(Date.now() - startedAt);
  indexingReadyRate.add(false);
  return false;
}

export default function () {
  const userId = __VU;
  const username = `${USER_PREFIX}${userId}`;
  const password = `${PASS_PREFIX}${userId}`;

  const token = login(username, password);
  if (!token) {
    sleep(1);
    return;
  }

  const authHeaders = {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  };

  const docsResp = http.get(`${BASE_URL}/documents/`, {
    ...authHeaders,
    tags: { endpoint: 'documents_list' },
  });
  check(docsResp, {
    'documents success': (r) => r.status === 200,
  });

  for (let i = 0; i < UPLOADS_PER_ITER; i++) {
    const file = pdfs[Math.floor(Math.random() * pdfs.length)];

    const uploadResp = http.post(
      `${BASE_URL}/documents/`,
      { file: http.file(file.data, file.name) },
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
        tags: { endpoint: 'documents_upload' },
      }
    );

    const accepted = uploadResp.status === 202;
    uploadAcceptedRate.add(accepted);
    check(uploadResp, {
      'upload accepted': (r) => r.status === 202,
    });

    if (!accepted || !WAIT_FOR_INDEX) {
      continue;
    }

    const body = safeJson(uploadResp);
    const documentId = body.document_id;
    if (!documentId) {
      indexingReadyRate.add(false);
      continue;
    }

    pollUntilIndexed(documentId, authHeaders);
  }

  const encodedQuery = encodeURIComponent(QUERY);
  const searchResp = http.get(`${BASE_URL}/search/?q=${encodedQuery}`, {
    ...authHeaders,
    tags: { endpoint: 'search' },
  });
  check(searchResp, {
    'search success': (r) => r.status === 200,
  });

  sleep(THINK_TIME_SEC);
}
