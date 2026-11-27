"""Tạo đường link công khai cho ảnh/video.

Instagram (ảnh) và TikTok (ảnh) bắt buộc file phải có link công khai để họ tự tải về.
Hai cách:
  1. MEDIA_BASE_URL: thư mục posts/ đã được đưa lên web (ví dụ link raw GitHub).
     Link = MEDIA_BASE_URL/<id bài>/<tên file>
  2. S3_BUCKET (+ S3_ENDPOINT_URL cho Cloudflare R2): bot tự tải file lên rồi lấy link.
"""
from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote


def public_url(post_id: str, path: Path) -> str:
    base = os.getenv("MEDIA_BASE_URL")
    if base:
        return f"{base.rstrip('/')}/{quote(post_id)}/{quote(path.name)}"
    bucket = os.getenv("S3_BUCKET")
    if bucket:
        return _upload_s3(bucket, f"{post_id}/{path.name}", path)
    raise RuntimeError(
        "Cần link công khai cho file media. Đặt MEDIA_BASE_URL hoặc S3_BUCKET trong .env"
    )


def _upload_s3(bucket: str, key: str, path: Path) -> str:
    try:
        import boto3
    except ImportError as exc:
        raise RuntimeError("Cài boto3 để dùng S3/R2: pip install boto3") from exc
    client = boto3.client("s3", endpoint_url=os.getenv("S3_ENDPOINT_URL") or None)
    client.upload_file(str(path), bucket, key)
    public_base = os.getenv("S3_PUBLIC_BASE_URL")
    if public_base:
        return f"{public_base.rstrip('/')}/{quote(key)}"
    return client.generate_presigned_url(
        "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=6 * 3600
    )
