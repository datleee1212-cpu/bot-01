"""Đăng lên Facebook bằng trình duyệt.

FB_TARGET_URL: nơi đăng, ví dụ trang cá nhân (https://www.facebook.com/me),
một Page bạn quản lý (đang dùng Facebook với tư cách Page đó), hoặc group bạn là thành viên.
Không đặt thì đăng lên bảng tin của bạn.
"""
from __future__ import annotations

import os

from . import BrowserPublisher, attach_files, click, human_pause, type_text

COMPOSER = [
    'div[role="button"]:has-text("Bạn đang nghĩ gì")',
    'div[role="button"]:has-text("on your mind")',
    'div[role="button"]:has-text("Viết gì đó")',
    'div[role="button"]:has-text("Write something")',
    'div[role="button"]:has-text("Tạo bài viết công khai")',
    'div[role="button"]:has-text("Create a public post")',
]
DIALOG = 'div[role="dialog"]'
TEXTBOX = [f'{DIALOG} div[role="textbox"][contenteditable="true"]']
PHOTO_BUTTON = [f'{DIALOG} div[aria-label="Ảnh/video"]', f'{DIALOG} div[aria-label="Photo/video"]']
NEXT_BUTTON = [f'{DIALOG} div[role="button"][aria-label="Tiếp"]',
               f'{DIALOG} div[role="button"][aria-label="Next"]']
POST_BUTTON = [f'{DIALOG} div[role="button"][aria-label="Đăng"]',
               f'{DIALOG} div[role="button"][aria-label="Post"]']


class FacebookBrowser(BrowserPublisher):
    name = "facebook"

    def start_url(self, post) -> str:
        return os.getenv("FB_TARGET_URL", "https://www.facebook.com/")

    def post(self, page, post) -> dict:
        click(page, COMPOSER)
        text = post.text_for(self.name)
        if post.link:
            text = f"{text}\n\n{post.link}"
        type_text(page, TEXTBOX, text)
        if post.media:
            if not page.locator(f'{DIALOG} input[type=file]').count():
                click(page, PHOTO_BUTTON)
            attach_files(page, post.media, f'{DIALOG} input[type=file]')
            human_pause(3, 6)
        # giao diện mới có thể có bước "Tiếp" trước "Đăng"
        if any(page.locator(s).count() for s in NEXT_BUTTON):
            click(page, NEXT_BUTTON)
        click(page, POST_BUTTON)
        page.locator(DIALOG).first.wait_for(state="detached", timeout=300000)
        human_pause(2, 4)
        return {"id": f"browser-{post.id}", "url": None, "method": "browser"}
