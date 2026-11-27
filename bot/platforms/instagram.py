"""Instagram qua Instagram Graph API (đăng nhập bằng Facebook Login).

Cần: IG_USER_ID (ID tài khoản Instagram chuyên nghiệp liên kết với Page) và
IG_TOKEN (thường dùng luôn Page token có quyền instagram_basic, instagram_content_publish).

- Ảnh: chỉ JPEG, phải có link công khai (xem bot/media.py).
- Video: đăng dạng Reels, bot tải trực tiếp file lên (resumable upload), không cần link công khai.
- Nhiều ảnh: carousel (tối đa 10).
- Giới hạn khoảng 50 bài / 24 giờ; bot kiểm tra trước khi đăng.
"""
from __future__ import annotations

import os

import requests

from .. import config
from ..media import public_url
from ..store import Post
from .base import PlatformError, Publisher, check, poll


class InstagramPublisher(Publisher):
    name = "instagram"

    def __init__(self):
        self.ig_id = config.env("IG_USER_ID")
        self.token = os.getenv("IG_TOKEN") or config.env("FB_PAGE_TOKEN")
        self.base = f"https://graph.facebook.com/{config.GRAPH_VERSION}"

    def _post(self, path: str, **data) -> dict:
        data["access_token"] = self.token
        return check(requests.post(f"{self.base}/{path}", data=data, timeout=120),
                     f"Instagram {path}")

    def _get(self, path: str, **params) -> dict:
        params["access_token"] = self.token
        return check(requests.get(f"{self.base}/{path}", params=params, timeout=60),
                     f"Instagram {path}")

    def quota_left(self) -> int | None:
        try:
            res = self._get(f"{self.ig_id}/content_publishing_limit", fields="quota_usage,config")
            item = res["data"][0]
            return item["config"]["quota_total"] - item["quota_usage"]
        except Exception:
            return None

    def publish(self, post: Post) -> dict:
        left = self.quota_left()
        if left is not None and left <= 0:
            raise PlatformError("Instagram đã hết hạn mức đăng trong 24 giờ")
        caption = post.text_for(self.name)
        if post.videos:
            container = self._reel(post.videos[0], caption)
        elif len(post.images) == 1:
            container = self._image(post, post.images[0], caption=caption)
        elif len(post.images) > 1:
            children = [self._image(post, img, carousel=True) for img in post.images[:10]]
            container = self._post(f"{self.ig_id}/media", media_type="CAROUSEL",
                                   children=",".join(children), caption=caption)["id"]
        else:
            raise PlatformError("Instagram bắt buộc phải có ảnh hoặc video")
        self._wait(container)
        media_id = self._post(f"{self.ig_id}/media_publish", creation_id=container)["id"]
        link = self._get(media_id, fields="permalink").get("permalink")
        return {"id": media_id, "url": link}

    def _image(self, post: Post, path, caption: str = "", carousel: bool = False) -> str:
        if path.suffix.lower() not in (".jpg", ".jpeg"):
            raise PlatformError(f"Instagram chỉ nhận ảnh JPEG: {path.name}")
        data = {"image_url": public_url(post.id, path)}
        if carousel:
            data["is_carousel_item"] = "true"
        else:
            data["caption"] = caption
        return self._post(f"{self.ig_id}/media", **data)["id"]

    def _reel(self, path, caption: str) -> str:
        container = self._post(f"{self.ig_id}/media", media_type="REELS",
                               upload_type="resumable", caption=caption)["id"]
        size = path.stat().st_size
        with open(path, "rb") as fh:
            resp = requests.post(
                f"https://rupload.facebook.com/ig-api-upload/{config.GRAPH_VERSION}/{container}",
                headers={"Authorization": f"OAuth {self.token}", "offset": "0",
                         "file_size": str(size)},
                data=fh, timeout=1800,
            )
        check(resp, "Instagram tải video")
        return container

    def _wait(self, container: str) -> None:
        res = poll(lambda: self._get(container, fields="status_code"),
                   lambda r: r.get("status_code") in ("FINISHED", "ERROR", "EXPIRED"),
                   timeout=600, every=15)
        if res.get("status_code") != "FINISHED":
            raise PlatformError(f"Instagram xử lý media thất bại: {res}")
