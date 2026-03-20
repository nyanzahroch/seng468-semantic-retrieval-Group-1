from flask import Flask, jsonify
from .core.config import settings
from .router.auth import auth_bp
from .router.documents import documents_bp
from .router.search import search_bp
from .database.models import Base
from .database.session import engine

def create_app():
    app = Flask(__name__)

    # Create tables
    Base.metadata.create_all(bind=engine)

    # Register routers
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(documents_bp, url_prefix="/documents")
    app.register_blueprint(search_bp, url_prefix="/search")

    @app.route("/")
    def root():
        return jsonify({"status": "API running"})

    return app

def main():
    app = create_app()
    app.run(host="0.0.0.0", port=8080)

if __name__ == "__main__":
    main()

