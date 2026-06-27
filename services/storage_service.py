import boto3
import uuid
from config import STORJ_ACCESS_KEY, STORJ_SECRET_KEY, STORJ_BUCKET, STORJ_ENDPOINT

s3 = boto3.client(
    "s3",
    endpoint_url=STORJ_ENDPOINT,
    aws_access_key_id=STORJ_ACCESS_KEY,
    aws_secret_access_key=STORJ_SECRET_KEY,
)

def upload_file(file_bytes: bytes, filename: str, content_type: str) -> str:
    key = f"{uuid.uuid4()}_{filename}"
    s3.put_object(
        Bucket=STORJ_BUCKET,
        Key=key,
        Body=file_bytes,
        ContentType=content_type,
        ACL="public-read",
    )
    return f"{STORJ_ENDPOINT}/{STORJ_BUCKET}/{key}"
