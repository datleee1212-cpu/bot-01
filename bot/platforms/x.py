"""X (Twitter) qua API v2, xác thực OAuth 1.0a user context (khoá không hết hạn).

Cần: X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET (app có quyền Read and Write).
Chi phí (pay-per-use 2026): khoảng $0.015 mỗi bài, $0.20 nếu bài có link.
Đặt X_INCLUDE_LINKS=false để bỏ link khỏi bài trên X và tiết kiệm chi phí.
"""
from __future__ import annotations

import math
import os

from requests_oauthlib import OAuth1Session

from .. import config
from ..store import Post
from .base import PlatformError, Publisher, check, poll

API = "https://api.x.com/2"
CHUNK = 4 * 1024 * 1024
MAX_LEN = 280
URL_LEN = 23  # X tính mọi link là 23 ký tự


def fit_text(text: str, link: str | None) -> str:
    budget = MAX_LEN - (URL_LEN + 2 if link else 0)
    if len(text) > budget:
        text = text[: budget - 1].rstrip() + "…"
    return f"{text}\n\n{link}" if link else text


class XPublisher(Publisher):
    name = "x"

    def __init__(self):
        self.session = OAuth1Session(
            config.env("X_API_KEY"), config.env("X_API_SECRET"),
            config.env("X_ACCESS_TOKEN"), config.env("X_ACCESS_SECRET"),
        )
        self.include_links = os.getenv("X_INCLUDE_LINKS", "true").lower() != "false"

    def publish(self, post: Post) -> dict:
        media = post.videos[:1] or post.images[:4]
        media_ids = [self._upload(m) for m in media]
        body = {"text": fit_text(post.text_for(self.name),
                                 post.link if self.include_links else None)}
        if media_ids:
            body["media"] = {"media_ids": media_ids}
        res = check(self.session.post(f"{API}/tweets", json=body, timeout=60), "X tạo bài")
        tid = res["data"]["id"]
        return {"id": tid, "url": f"https://x.com/i/web/status/{tid}"}

    def _upload(self, path) -> str:
        ext = path.suffix.lower()
        is_video = ext in (".mp4", ".mov", ".webm")
        mime = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
                ".webp": "image/webp", ".gif": "image/gif", ".mp4": "video/mp4",
                ".mov": "video/quicktime", ".webm": "video/webm"}[ext]
        category = "tweet_video" if is_video else ("tweet_gif" if ext == ".gif" else "tweet_image")
        size = path.stat().st_size
        init = check(self.session.post(f"{API}/media/upload/initialize", json={
            "media_type": mime, "total_bytes": size, "media_category": category}, timeout=60),
            "X khởi tạo upload")
        media_id = init["data"]["id"]
        with open(path, "rb") as fh:
            for i in range(math.ceil(size / CHUNK)):
                check(self.session.post(f"{API}/media/upload/{media_id}/append",
                                        data={"segment_index": i},
                                        files={"media": fh.read(CHUNK)}, timeout=300),
                      "X tải media")
        fin = check(self.session.post(f"{API}/media/upload/{media_id}/finalize", timeout=60),
                    "X hoàn tất upload")
        info = fin.get("data", {}).get("processing_info")
        if info:
            res = poll(
                lambda: check(self.session.get(f"{API}/media/upload", params={
                    "command": "STATUS", "media_id": media_id}, timeout=60), "X trạng thái media"),
                lambda r: r["data"].get("processing_info", {}).get("state") in
                ("succeeded", "failed", None),
                timeout=600, every=5)
            if res["data"].get("processing_info", {}).get("state") == "failed":
                raise PlatformError(f"X xử lý media thất bại: {res}")
        return media_id
