from flask import Flask, jsonify
from sqlalchemy import text
import time
from .core.config import settings
from .router.auth import auth_bp
from .router.documents import documents_bp
from .router.search import search_bp
from .database.models import Base
from .database.session import engine


# def wait_for_database(max_attempts=30, delay_seconds=2):
#     """Retry DB connection to handle transient Docker DNS/network startup races."""
#     for attempt in range(1, max_attempts + 1):
#         try:
#             with engine.connect() as conn:
#                 conn.execute(text("SELECT 1"))
#             return
#         except Exception as exc:
#             if attempt == max_attempts:
#                 raise RuntimeError(
#                     f"Database unavailable after {max_attempts} attempts"
#                 ) from exc
#             print(
#                 f"Waiting for database (attempt {attempt}/{max_attempts}): {exc}"
#             )
#             time.sleep(delay_seconds)

def create_app():
    app = Flask(__name__)

    # wait_for_database()

    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    Base.metadata.create_all(bind=engine)

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

