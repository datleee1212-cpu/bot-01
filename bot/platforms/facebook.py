"""Facebook Page qua Graph API (Pages API).

Cần: FB_PAGE_ID, FB_PAGE_TOKEN (Page access token dài hạn có quyền pages_manage_posts,
pages_read_engagement, pages_show_list; thêm publish_video nếu đăng video).
Chỉ đăng được lên Page, không đăng lên trang cá nhân hay group.
"""
from __future__ import annotations

import json

import requests

from .. import config
from ..store import Post
from .base import PlatformError, Publisher, check


class FacebookPublisher(Publisher):
    name = "facebook"

    def __init__(self):
        self.page_id = config.env("FB_PAGE_ID")
        self.token = config.env("FB_PAGE_TOKEN")
        self.base = f"https://graph.facebook.com/{config.GRAPH_VERSION}"

    def publish(self, post: Post) -> dict:
        text = post.text_for(self.name)
        if post.videos:
            return self._video(post.videos[0], text)
        if post.images:
            return self._photos(post.images, text, post.link)
        data = {"message": text, "access_token": self.token}
        if post.link:
            data["link"] = post.link
        res = check(requests.post(f"{self.base}/{self.page_id}/feed", data=data, timeout=60),
                    "Facebook feed")
        return {"id": res["id"], "url": f"https://www.facebook.com/{res['id']}"}

    def _upload_photo(self, path, published: bool, caption: str = "") -> dict:
        with open(path, "rb") as fh:
            resp = requests.post(
                f"{self.base}/{self.page_id}/photos",
                data={"published": str(published).lower(), "caption": caption,
                      "access_token": self.token},
                files={"source": fh}, timeout=300,
            )
        return check(resp, "Facebook photo")

    def _photos(self, images, text: str, link: str | None) -> dict:
        if link:
            text = f"{text}\n\n{link}"
        if len(images) == 1:
            res = self._upload_photo(images[0], True, text)
            pid = res.get("post_id") or res["id"]
            return {"id": pid, "url": f"https://www.facebook.com/{pid}"}
        media_ids = [self._upload_photo(img, False)["id"] for img in images]
        data = {"message": text, "access_token": self.token}
        for i, mid in enumerate(media_ids):
            data[f"attached_media[{i}]"] = json.dumps({"media_fbid": mid})
        res = check(requests.post(f"{self.base}/{self.page_id}/feed", data=data, timeout=60),
                    "Facebook album")
        return {"id": res["id"], "url": f"https://www.facebook.com/{res['id']}"}

    def _video(self, path, text: str) -> dict:
        with open(path, "rb") as fh:
            resp = requests.post(
                f"https://graph-video.facebook.com/{config.GRAPH_VERSION}/{self.page_id}/videos",
                data={"description": text, "access_token": self.token},
                files={"source": fh}, timeout=1800,
            )
        res = check(resp, "Facebook video")
        if "id" not in res:
            raise PlatformError(f"Facebook video không trả id: {res}")
        return {"id": res["id"], "url": f"https://www.facebook.com/{res['id']}"}
