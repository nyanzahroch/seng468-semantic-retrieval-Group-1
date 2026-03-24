from functools import lru_cache
from math import sqrt
from flask import Blueprint, jsonify, request
from sqlalchemy import select, func
from fastembed import TextEmbedding

from src.core.config import settings
from src.database.models import Document, Paragraph
from src.database.session import SessionLocal
from src.security.jwt import decode_token

search_bp = Blueprint("search", __name__)


@lru_cache(maxsize=1)
def _get_embedder() -> TextEmbedding:
    return TextEmbedding(model_name=settings.embedding_model_name)


def _embed_query(query_text: str) -> list[float]:
    vector = list(_get_embedder().embed([query_text]))[0].tolist()
    norm = sqrt(sum(value * value for value in vector))
    if norm > 0:
        vector = [value / norm for value in vector]
    return vector


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

        response = [
            {
                "text": row.text,
                "score": round(float(row.score), 3),
                "document_id": str(row.document_id),
                "filename": row.filename,
            }
            for row in rows
        ]

        return jsonify(response), 200
    finally:
        db.close()
