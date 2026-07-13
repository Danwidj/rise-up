import os
from pathlib import Path

# install boto3
import boto3
from dotenv import load_dotenv

load_dotenv()

BUCKET = os.getenv("R2_BUCKET")

s3 = boto3.client(
    "s3",
    endpoint_url=f"https://{os.getenv('R2_ACCOUNT_ID')}.r2.cloudflarestorage.com",
    aws_access_key_id=os.getenv("R2_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("R2_SECRET_KEY"),
    region_name="auto",
)


def upload_file(local_path: str | Path, object_key: str) -> None:
    """Upload a single file to R2."""
    s3.upload_file(str(local_path), BUCKET, object_key)


def download_file(object_key: str, local_path: str | Path) -> None:
    """Download a single file from R2."""
    Path(local_path).parent.mkdir(parents=True, exist_ok=True)
    s3.download_file(BUCKET, object_key, str(local_path))


def delete_file(object_key: str) -> None:
    """Delete a file from R2."""
    s3.delete_object(Bucket=BUCKET, Key=object_key)


def upload_dataset(local_directory: str | Path, prefix: str = "") -> None:
    """
    Recursively upload every file inside a directory.
    """
    local_directory = Path(local_directory)

    for file in local_directory.rglob("*"):
        if not file.is_file():
            continue

        relative = file.relative_to(local_directory).as_posix()
        object_key = f"{prefix}/{relative}" if prefix else relative

        s3.upload_file(
            str(file),
            BUCKET,
            object_key,
        )

        print(f"{file} uploaded to {object_key}")


def download_dataset(prefix: str, destination: str | Path) -> None:
    """
    Download every object whose key starts with prefix.
    """
    destination = Path(destination)

    paginator = s3.get_paginator("list_objects_v2")

    for page in paginator.paginate(Bucket=BUCKET, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]

            relative = Path(key).relative_to(prefix)
            output = destination / relative

            output.parent.mkdir(parents=True, exist_ok=True)

            s3.download_file(
                BUCKET,
                key,
                str(output),
            )


def delete_dataset(prefix: str) -> None:
    """
    Delete every object under a prefix.
    """
    paginator = s3.get_paginator("list_objects_v2")

    for page in paginator.paginate(Bucket=BUCKET, Prefix=prefix):
        objects = [
            {"Key": obj["Key"]}
            for obj in page.get("Contents", [])
        ]

        if objects:
            s3.delete_objects(
                Bucket=BUCKET,
                Delete={"Objects": objects},
            )


def list_objects(prefix: str = "") -> list[str]:
    """Return every object key."""
    paginator = s3.get_paginator("list_objects_v2")

    keys = []

    for page in paginator.paginate(Bucket=BUCKET, Prefix=prefix):
        keys.extend(
            obj["Key"]
            for obj in page.get("Contents", [])
        )

    return keys


def file_exists(object_key: str) -> bool:
    """Check if an object exists."""
    try:
        s3.head_object(
            Bucket=BUCKET,
            Key=object_key,
        )
        return True

    except Exception:
        return False


def generate_presigned_url(
    object_key: str,
    expires_in: int = 3600,
) -> str:
    """
    Generate a temporary download URL.
    """
    return s3.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": BUCKET,
            "Key": object_key,
        },
        ExpiresIn=expires_in,
    )