from src.core.celery_app import celery_app
from src.core.config import minio_client, settings
from src.core.indexing import index_document_bytes
from src.database.models import Document
from src.database.session import SessionLocal


@celery_app.task(name=settings.index_document_task_name, bind=True)
def index_document_task(self, document_id: str, user_id: int) -> dict:
    db = SessionLocal()
    document = None
    minio_response = None

    try:
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.user_id == user_id,
        ).first()

        if not document:
            return {
                "document_id": document_id,
                "status": "not_found",
            }

        document.status = "processing"
        db.commit()

        minio_path = f"{user_id}/{document_id}.pdf"
        minio_response = minio_client.get_object(settings.minio_bucket, minio_path)
        pdf_bytes = minio_response.read()

        page_count, chunk_count = index_document_bytes(db, document, pdf_bytes)
        return {
            "document_id": document_id,
            "status": "ready",
            "page_count": page_count,
            "chunk_count": chunk_count,
        }
    except Exception as exc:
        if document is not None:
            try:
                document.status = "failed"
                db.commit()
            except Exception:
                db.rollback()
        raise exc
    finally:
        if minio_response is not None:
            minio_response.close()
            minio_response.release_conn()
        db.close()
