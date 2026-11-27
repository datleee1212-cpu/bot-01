"""Đăng lên X bằng trình duyệt (x.com/compose/post)."""
from __future__ import annotations

from ..platforms.base import PlatformError
from ..platforms.x import fit_text
from . import BrowserPublisher, attach_files, click, human_pause, type_text

TEXTBOX = ['[data-testid="tweetTextarea_0"]', 'div[role="textbox"]']
POST_BUTTON = ['[data-testid="tweetButton"]', '[data-testid="tweetButtonInline"]']
FILE_INPUT = 'input[data-testid="fileInput"], input[type=file]'


class XBrowser(BrowserPublisher):
    name = "x"
    home_url = "https://x.com/compose/post"

    def post(self, page, post) -> dict:
        text = fit_text(post.text_for(self.name), post.link)
        type_text(page, TEXTBOX, text)
        media = post.videos[:1] or post.images[:4]
        if media:
            attach_files(page, media, FILE_INPUT)
            # đợi media tải xong: nút Đăng chỉ bật khi xử lý xong
            page.wait_for_selector(
                '[data-testid="tweetButton"]:not([aria-disabled="true"])', timeout=300000)
        human_pause(1, 3)
        click(page, POST_BUTTON)
        try:
            page.wait_for_selector('[data-testid="toast"]', timeout=30000)
        except Exception:
            if page.locator(TEXTBOX[0]).count() and page.locator(TEXTBOX[0]).inner_text().strip():
                raise PlatformError("X: bấm Đăng nhưng bài vẫn còn trong ô soạn, có thể bị chặn")
        human_pause(2, 4)
        return {"id": f"browser-{post.id}", "url": None, "method": "browser"}
