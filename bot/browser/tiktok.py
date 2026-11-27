"""Đăng video lên TikTok bằng trình duyệt (TikTok Studio)."""
from __future__ import annotations

from ..platforms.base import PlatformError
from . import BrowserPublisher, attach_files, click, first_visible, human_pause

CAPTION = ['div.public-DraftEditor-content[contenteditable="true"]',
           'div[contenteditable="true"]']
POST_BUTTON = ['button[data-e2e="post_video_button"]', 'button:has-text("Đăng")',
               'button:has-text("Post")']
UPLOADED = ['text=Đã tải lên', 'text=Uploaded']
DONE = ['text=Video của bạn đã được đăng', 'text=Your video has been uploaded',
        'text=Đã đăng', 'text=Manage your posts', 'text=Quản lý bài đăng']


class TikTokBrowser(BrowserPublisher):
    name = "tiktok"
    home_url = "https://www.tiktok.com/tiktokstudio/upload"

    def post(self, page, post) -> dict:
        if not post.videos:
            raise PlatformError("TikTok: cần một video (mp4/mov/webm)")
        attach_files(page, post.videos[:1])
        first_visible(page, UPLOADED, timeout=600000)
        box = first_visible(page, CAPTION)
        box.click()
        page.keyboard.press("Control+A")
        page.keyboard.press("Delete")
        human_pause(0.5, 1)
        page.keyboard.type(post.text_for(self.name)[:2200], delay=40)
        human_pause(2, 4)
        click(page, POST_BUTTON)
        first_visible(page, DONE, timeout=300000)
        human_pause(2, 4)
        return {"id": f"browser-{post.id}", "url": None, "method": "browser"}
