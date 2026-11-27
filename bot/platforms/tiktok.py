"""TikTok qua Content Posting API.

Mặc định dùng chế độ "inbox" (scope video.upload): bot đẩy video vào hộp nháp TikTok,
bạn mở app TikTok, chỉnh và bấm đăng. Đây là cách hợp lệ cho bot cá nhân, vì TikTok
không duyệt (audit) công cụ nội bộ, và app chưa audit chỉ đăng thẳng được ở chế độ riêng tư.

TIKTOK_MODE=direct dùng Direct Post (scope video.publish), bài sẽ ở chế độ SELF_ONLY
(chỉ mình tôi) cho tới khi app qua audit.

Cần: TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET, TIKTOK_REFRESH_TOKEN (lấy bằng
`python -m bot tiktok-login`). Token mới được lưu tự động vào .secrets/tokens.json.
"""
from __future__ import annotations

import math
import os
import time

import requests

from .. import config
from ..store import Post
from .base import PlatformError, Publisher, check, poll

API = "https://open.tiktokapis.com/v2"
CHUNK = 10 * 1024 * 1024  # 5–64 MB mỗi phần
MIN_CHUNK = 5 * 1024 * 1024


def chunk_plan(size: int) -> tuple[int, int]:
    """Trả (chunk_size, total_chunk_count) theo quy tắc của TikTok."""
    if size <= MIN_CHUNK:
        return size, 1
    count = max(1, size // CHUNK)  # phần cuối được phép lớn hơn (tới 128 MB)
    return CHUNK, count


class TikTokPublisher(Publisher):
    name = "tiktok"

    def __init__(self, store: config.TokenStore | None = None):
        self.client_key = config.env("TIKTOK_CLIENT_KEY")
        self.client_secret = config.env("TIKTOK_CLIENT_SECRET")
        self.store = store or config.TokenStore()
        self.mode = os.getenv("TIKTOK_MODE", "inbox")

    # --- token ---
    def access_token(self) -> str:
        saved = self.store.get("tiktok")
        if saved.get("access_token") and saved.get("expires_at", 0) > time.time() + 300:
            return saved["access_token"]
        refresh = saved.get("refresh_token") or config.env("TIKTOK_REFRESH_TOKEN")
        res = check(requests.post(f"{API}/oauth/token/", data={
            "client_key": self.client_key, "client_secret": self.client_secret,
            "grant_type": "refresh_token", "refresh_token": refresh,
        }, timeout=60), "TikTok làm mới token")
        self.store.set("tiktok", {
            "access_token": res["access_token"],
            "refresh_token": res.get("refresh_token", refresh),
            "expires_at": time.time() + int(res.get("expires_in", 86400)),
        })
        return res["access_token"]

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.access_token()}",
                "Content-Type": "application/json; charset=UTF-8"}

    # --- đăng ---
    def publish(self, post: Post) -> dict:
        if not post.videos:
            raise PlatformError("TikTok: bot hiện chỉ hỗ trợ đăng video (mp4/mov/webm)")
        video = post.videos[0]
        size = video.stat().st_size
        chunk_size, count = chunk_plan(size)
        source = {"source": "FILE_UPLOAD", "video_size": size,
                  "chunk_size": chunk_size, "total_chunk_count": count}
        if self.mode == "direct":
            url = f"{API}/post/publish/video/init/"
            body = {"post_info": {"title": post.text_for(self.name)[:2200],
                                  "privacy_level": post.options.get("tiktok_privacy", "SELF_ONLY"),
                                  "disable_comment": False},
                    "source_info": source}
        else:
            url = f"{API}/post/publish/inbox/video/init/"
            body = {"source_info": source}
        init = check(requests.post(url, headers=self._headers(), json=body, timeout=60),
                     "TikTok khởi tạo")["data"]
        self._upload(video, init["upload_url"], size, chunk_size, count)
        status = poll(lambda: self._status(init["publish_id"]),
                      lambda s: s.get("status") in (
                          "SEND_TO_USER_INBOX", "PUBLISH_COMPLETE", "FAILED"),
                      timeout=600, every=10)
        if status.get("status") == "FAILED":
            raise PlatformError(f"TikTok thất bại: {status}")
        return {"id": init["publish_id"], "url": None, "status": status.get("status")}

    def _upload(self, path, upload_url: str, size: int, chunk_size: int, count: int) -> None:
        with open(path, "rb") as fh:
            for i in range(count):
                start = i * chunk_size
                end = size - 1 if i == count - 1 else start + chunk_size - 1
                fh.seek(start)
                data = fh.read(end - start + 1)
                resp = requests.put(upload_url, data=data, timeout=600, headers={
                    "Content-Type": "video/mp4",
                    "Content-Length": str(len(data)),
                    "Content-Range": f"bytes {start}-{end}/{size}",
                })
                if resp.status_code not in (200, 201, 206):
                    raise PlatformError(f"TikTok tải video lỗi {resp.status_code}: {resp.text}")

    def _status(self, publish_id: str) -> dict:
        res = check(requests.post(f"{API}/post/publish/status/fetch/", headers=self._headers(),
                                  json={"publish_id": publish_id}, timeout=60),
                    "TikTok trạng thái")
        return res.get("data", {})
