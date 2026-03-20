from flask import Blueprint, jsonify

search_bp = Blueprint("search", __name__)

@search_bp.get("/")
def search():
    return jsonify({"status": "not implemented"})
