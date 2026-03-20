from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename
from src.security.jwt import decode_token
from src.database.session import SessionLocal
from src.database.models import Document
from src.core.config import minio_client, settings
import uuid
from collections import OrderedDict 

documents_bp = Blueprint("documents", __name__)

@documents_bp.route("/", methods=["POST"])
def upload_document():
    # check the auth token is valid
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Missing or invalid token"}), 401

    token = auth_header.split(" ")[1]

    try:
        payload = decode_token(token)
        user_id = payload["user_id"]
    except Exception:
        return jsonify({"error": "Invalid token"}), 401

    # check that the pdf is valid
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    filename = secure_filename(file.filename)

    if not filename.lower().endswith(".pdf"):
        return jsonify({"error": "Only PDF files allowed"}), 400

    # create a document id
    document_id = str(uuid.uuid4())

    # upload the pdf to minio bucket pdfs
    minio_path = f"{user_id}/{document_id}.pdf"

    minio_client.put_object(
        settings.minio_bucket,
        minio_path,
        file.stream,
        length=-1,
        part_size=10 * 1024 * 1024
    )

    # add the data to posgres table documents
    db = SessionLocal()
    doc = Document(
        id=document_id,
        user_id=user_id,
        filename=filename,
        status="processing",
        page_count=None
    )
    db.add(doc)
    db.commit()

    # send the user a 202 accepted message
    return jsonify(OrderedDict([
        ("message", "PDF uploaded, processing started"),
        ("document_id", document_id),
        ("status", "processing")
    ])), 202

