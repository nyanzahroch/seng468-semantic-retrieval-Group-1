from pydantic_settings import BaseSettings
from minio import Minio
from minio.error import S3Error 

class Settings(BaseSettings):
    database_url: str
    jwt_secret: str
    jwt_algorithm: str = "HS256"

    postgres_user: str
    postgres_password: str
    postgres_db: str

    minio_endpoint: str 
    minio_access_key: str 
    minio_secret_key: str 
    minio_bucket: str 

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
    if not minio_client.bucket_exists(settings.minio_bucket):
        minio_client.make_bucket(settings.minio_bucket)
        print(f"Created bucket: {settings.minio_bucket}")
    else:
        print(f"Bucket already exists: {settings.minio_bucket}")

ensure_bucket()