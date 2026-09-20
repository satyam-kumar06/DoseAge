"""S3 access, with a local folder standing in when there is no AWS account."""
import base64
import os
import shutil
from typing import Any, Dict, Optional

from . import config, util


def s3_client():
    """S3 client pinned to the regional endpoint, with virtual-host addressing.

    Every presigned URL in DoseWise comes from here so that the host in the
    URL matches the region it is signed for.
    """
    import boto3
    from botocore.config import Config

    return boto3.client(
        "s3",
        region_name=config.REGION,
        endpoint_url=config.S3_ENDPOINT,
        config=Config(s3={"addressing_style": "virtual"}, signature_version="s3v4"),
    )


def _local_path(key: str) -> str:
    path = os.path.join(config.LOCAL_FILES_PATH, key)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


def presigned_upload(key: str, content_type: str = "image/jpeg", expires: int = 300) -> Dict[str, Any]:
    """Upload target for the camera screen.

    On AWS this is a real presigned PUT that expires in 5 minutes. Locally the
    frontend posts the file to the dev server instead, same shape.
    """
    if not config.IS_AWS:
        return {
            "mode": "local",
            "url": f"/local-upload/{key}",
            "method": "PUT",
            "key": key,
            "expiresIn": expires,
            "headers": {"Content-Type": content_type},
        }

    s3 = s3_client()
    url = s3.generate_presigned_url(
        "put_object",
        Params={"Bucket": config.BUCKET_NAME, "Key": key, "ContentType": content_type},
        ExpiresIn=expires,
    )
    return {
        "mode": "s3",
        "url": url,
        "method": "PUT",
        "key": key,
        "expiresIn": expires,
        "headers": {"Content-Type": content_type},
    }


def presigned_get(key: str, expires: int = 3600) -> Optional[str]:
    if not config.IS_AWS:
        return f"/local-file/{key}"
    return s3_client().generate_presigned_url(
        "get_object", Params={"Bucket": config.BUCKET_NAME, "Key": key}, ExpiresIn=expires
    )


def put_bytes(key: str, body: bytes, content_type: str = "application/octet-stream") -> str:
    if not config.IS_AWS:
        with open(_local_path(key), "wb") as fh:
            fh.write(body)
        return key
    s3_client().put_object(
        Bucket=config.BUCKET_NAME, Key=key, Body=body, ContentType=content_type
    )
    return key


def get_bytes(key: str) -> bytes:
    if not config.IS_AWS:
        with open(_local_path(key), "rb") as fh:
            return fh.read()
    return s3_client().get_object(Bucket=config.BUCKET_NAME, Key=key)["Body"].read()


def exists(key: str) -> bool:
    if not config.IS_AWS:
        return os.path.exists(_local_path(key))
    from botocore.exceptions import ClientError

    try:
        s3_client().head_object(Bucket=config.BUCKET_NAME, Key=key)
        return True
    except ClientError:
        return False


def scan_key(parent_id: str, scan_id: str, ext: str = "jpg") -> str:
    return f"scans/{parent_id}/{scan_id}.{ext}"


def crop_key(scan_id: str, index: int) -> str:
    return f"crops/{scan_id}/{index}.jpg"


def pill_key(parent_id: str, med_id: str) -> str:
    return f"pills/{parent_id}/{med_id}.jpg"


def visit_card_key(parent_id: str, card_id: str) -> str:
    return f"visit-cards/{parent_id}/{card_id}.pdf"


def save_data_url(key: str, data_url: str) -> str:
    """Accept a browser data: URL and store it as a real object."""
    if "," in data_url:
        header, payload = data_url.split(",", 1)
        content_type = header.split(";")[0].replace("data:", "") or "image/jpeg"
    else:
        payload, content_type = data_url, "image/jpeg"
    return put_bytes(key, base64.b64decode(payload), content_type)
