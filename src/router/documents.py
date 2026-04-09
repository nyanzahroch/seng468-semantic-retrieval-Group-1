from flask import Blueprint, jsonify, request, Response
from werkzeug.utils import secure_filename
from src.security.jwt import decode_token
from src.database.session import SessionLocal
from src.database.models import Document, Paragraph
from src.core.config import minio_client, settings
from src.core.indexing import index_document_bytes
import uuid
import json
from io import BytesIO
from collections import OrderedDict 
from minio.error import S3Error

documents_bp = Blueprint("documents", __name__)

@documents_bp.route("/", methods=["POST"])
def upload_document():
    # check the auth token is valid
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Invalid credentials"}), 401

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
    pdf_bytes = file.read()

    if not pdf_bytes:
        return jsonify({"error": "PDF is empty"}), 400

    # upload the pdf to minio bucket pdfs
    minio_path = f"{user_id}/{document_id}.pdf"

    try:
        minio_client.put_object(
            settings.minio_bucket,
            minio_path,
            BytesIO(pdf_bytes),
            length=len(pdf_bytes),
        )
    except Exception:
        return jsonify({"error": "Document storage unavailable"}), 503

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

    try:
        page_count, chunk_count = index_document_bytes(db, doc, pdf_bytes)
        return jsonify(OrderedDict([
            ("message", "PDF uploaded and indexed"),
            ("document_id", document_id),
            ("status", "ready"),
            ("page_count", page_count),
            ("chunk_count", chunk_count),
        ])), 202
    except Exception:
        doc.status = "failed"
        db.commit()
        return jsonify(OrderedDict([
            ("message", "PDF uploaded but indexing failed"),
            ("document_id", document_id),
            ("status", "failed"),
        ])), 202
    finally:
        db.close()



@documents_bp.route("/", methods=["GET"])
def get_documents():
    # check the auth token is valid
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Invalid credentials"}), 401

    token = auth_header.split(" ")[1]

    try:
        payload = decode_token(token)
        user_id = payload["user_id"]
    except Exception:
        return jsonify({"error": "Invalid token"}), 401

    # get the users documents from postgres documents db
    db = SessionLocal()
    doc_list = ( db.query(Document)
        .filter(Document.user_id == user_id)
        .order_by(Document.upload_date)
        .all())

    formatted_doc_list = []
    for document in doc_list:
        formatted_doc_list.append(OrderedDict([
            ("document_id", str(document.id)),
            ("filename", document.filename),
            ("upload_date", document.upload_date.isoformat() + "Z"),
            ("status", document.status),
            ("page_count", document.page_count)
        ]))
    
    #return jsonify(formatted_doc_list), 200
    return Response(
        json.dumps(formatted_doc_list, indent=4),
        status=200,
        mimetype="application/json"
    )


@documents_bp.route("/<document_id>", methods=["DELETE"])
def delete_document(document_id):
    # check the auth token is valid
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Invalid credentials"}), 401

    token = auth_header.split(" ")[1]

    try:
        payload = decode_token(token)
        user_id = payload["user_id"]
    except Exception:
        return jsonify({"error": "Invalid token"}), 401

    # get the document from postgres
    db = SessionLocal()
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == user_id
    ).first()

    if not document:
        db.close()
        return jsonify({"error": "Document not found or not owned by user"}), 404

    try:
        # delete the pdf from minio bucket
        minio_path = f"{user_id}/{document_id}.pdf"
        minio_client.remove_object(settings.minio_bucket, minio_path)
    except S3Error:
        # if minio delete fails, continue with database deletion
        pass

    try:
        # delete all paragraphs associated with this document
        db.query(Paragraph).filter(Paragraph.document_id == document_id).delete()

        # delete the document from database
        db.delete(document)
        db.commit()

        return jsonify(OrderedDict([
            ("message", "Document and all associated data deleted"),
            ("document_id", document_id)
        ])), 200

    except Exception:
        db.rollback()
        return jsonify({"error": "Failed to delete document"}), 500

    finally:
        db.close()
