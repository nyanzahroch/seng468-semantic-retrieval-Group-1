from flask import Blueprint, jsonify, request, Response
from sqlalchemy import select, func
from collections import OrderedDict
import json

from src.core.config import settings
from src.core.embeddings import embed_texts
from src.database.models import Document, Paragraph
from src.database.session import SessionLocal
from src.security.jwt import decode_token

search_bp = Blueprint("search", __name__)


def _embed_query(query_text: str) -> list[float]:
    return embed_texts([query_text])[0]


@search_bp.get("/")
def search():
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Missing or invalid token"}), 401

    token = auth_header.split(" ")[1]
    try:
        payload = decode_token(token)
        user_id = int(payload["user_id"])
    except Exception:
        return jsonify({"error": "Invalid token"}), 401

    query_text = (request.args.get("q") or "").strip()
    if not query_text:
        return jsonify({"error": "Missing query parameter: q"}), 400

    try:
        query_embedding = _embed_query(query_text)
    except Exception:
        return jsonify({"error": "Embedding model unavailable"}), 503

    if len(query_embedding) != settings.embedding_dimensions:
        return jsonify({"error": "Embedding dimension mismatch"}), 500

    score = func.greatest(
        0.0,
        func.least(1.0, 1 - Paragraph.embedding.cosine_distance(query_embedding)),
    ).label("score")

    db = SessionLocal()
    try:
        stmt = (
            select(
                Paragraph.text.label("text"),
                score,
                Paragraph.document_id.label("document_id"),
                Document.filename.label("filename"),
            )
            .join(Document, Paragraph.document_id == Document.id)
            .where(Document.user_id == user_id)
            .order_by(score.desc())
            .limit(5)
        )
        rows = db.execute(stmt).all()

        response = []
        for row in rows:
            response.append(OrderedDict([
                ("text", row.text),
                ("score", round(float(row.score), 3)),
                ("document_id", str(row.document_id)),
                ("filename", row.filename)
            ]))
        # response = [
        #     {
        #         "text": row.text,
        #         "score": round(float(row.score), 3),
        #         "document_id": str(row.document_id),
        #         "filename": row.filename,
        #     }
        #     for row in rows
        # ]

        # return jsonify(response), 200
        return Response(
            json.dumps(response, indent=4),
            status=200,
            mimetype="application/json"
        )
    finally:
        db.close()
