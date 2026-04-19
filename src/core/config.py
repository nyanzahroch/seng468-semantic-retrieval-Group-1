from pydantic_settings import BaseSettings
from minio import Minio
from minio.error import S3Error 

class Settings(BaseSettings):
    database_url: str
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    embedding_model_name: str = "BAAI/bge-small-en-v1.5"
    embedding_dimensions: int = 384

    postgres_user: str
    postgres_password: str
    postgres_db: str

    minio_endpoint: str 
    minio_access_key: str 
    minio_secret_key: str 
    minio_bucket: str 

    rabbitmq_user: str = "guest"
    rabbitmq_password: str = "guest"
    rabbitmq_host: str = "rabbitmq"
    rabbitmq_port: int = 5672

    redis_host: str = "redis"
    redis_port: int = 6379

    celery_broker_url: str = "amqp://guest:guest@rabbitmq:5672//"
    celery_result_backend: str = "redis://redis:6379/0"
    celery_index_queue: str = "indexing"
    index_document_task_name: str = "src.worker.tasks.index_document_task"

    class Config:
        env_file = ".env"

settings = Settings()


minio_client = Minio( 
    settings.minio_endpoint,
    access_key=settings.minio_access_key,
    secret_key=settings.minio_secret_key,
    secure=False
)


def ensure_bucket(): #create the minio bucket
    try:
        if not minio_client.bucket_exists(settings.minio_bucket):
            minio_client.make_bucket(settings.minio_bucket)
            print(f"Created bucket: {settings.minio_bucket}")
        else:
            print(f"Bucket already exists: {settings.minio_bucket}")
    except Exception as exc:
        print(f"Warning: MinIO unavailable, skipping bucket check: {exc}")

ensure_bucket()