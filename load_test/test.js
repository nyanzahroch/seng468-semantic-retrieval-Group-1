import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE_URL = 'http://localhost:8080';
const pdfs = [
	{ name: 'biology_paper.pdf', data: open('./pdfs/biology_paper.pdf', 'b') },
	{ name: 'course_outline.pdf', data: open('./pdfs/course_outline.pdf', 'b') },
	{ name: 'Courseoutline_STAT354.pdf', data: open('./pdfs/Courseoutline_STAT354.pdf', 'b') },
	{ name: 'CSC_Final_Exam.pdf', data: open('./pdfs/CSC_Final_Exam.pdf', 'b') },
	{ name: 'CSC_Midterm_Exam.pdf', data: open('./pdfs/CSC_Midterm_Exam.pdf', 'b') },
	{ name: 'EPHE155_Course_Outline', data: open('./pdfs/EPHE155_Course_Outline.pdf', 'b') },
	{ name: 'quantum_algorithms_course_outline.pdf', data: open('./pdfs/quantum_algorithms_course_outline.pdf', 'b') },
	{ name: 'SAMtools_paper.pdf', data: open('./pdfs/SAMtools_paper.pdf', 'b') },
	{ name: 'SENG310_Outline.pdf', data: open('./pdfs/SENG310_Outline.pdf', 'b') },
	{ name: 'syllabus_math212.pdf', data: open('./pdfs/syllabus_math212.pdf', 'b') },
];

export const options = {};

function login(username, password) {
	const req = http.post(
		`${BASE_URL}/auth/login`,
		JSON.stringify({
			username,
			password,
		}),
		{
			headers: { 'Content-Type': 'application/json' },
		}
	);
	check(req, {
		'login success': (r) => r.status === 200,
	});
	const body = JSON.parse(req.body);
	return body.token;
}

export default function() {
	const userId = __VU;
	const username = `user${userId}`;
	const password = `pass${userId}`;
	const token = login(username, password);
	const authHeaders = {
		headers: {
			Authorization: `Bearer ${token}`,
		},
	};

	const searchReq = http.get(
		`${BASE_URL}/search?q=math%20statistics`,
		authHeaders
	);
	check(searchReq, {
		'search success': (r) => r.status === 200,
	});

	const docReq = http.get(
		`${BASE_URL}/documents`,
		authHeaders
	);
	check(docReq, {
		'documents success': (r) => r.status === 200,
	});

	for (let i = 0; i < 3; i ++) {
		const file = pdfs[Math.floor(Math.random() * pdfs.length)];
		const uploadReq = http.post(
			`${BASE_URL}/documents`,
			{
				file: http.file(file.data, file.name),
			},
			{
				headers: {
					Authorization: `Bearer ${token}`,
				},
			}
		);
		check(uploadReq, {
			'upload accepted': (r) => r.status === 202,
		});
	}

	sleep(1);
}
