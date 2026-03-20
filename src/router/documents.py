from flask import Blueprint, jsonify

documents_bp = Blueprint("documents", __name__)

@documents_bp.get("/")
def list_documents():
    return jsonify({"status": "not implemented"})
