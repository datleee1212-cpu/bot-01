"""Đăng lên Instagram bằng trình duyệt (instagram.com). Cần ít nhất một ảnh hoặc video."""
from __future__ import annotations

from ..platforms.base import PlatformError
from . import BrowserPublisher, attach_files, click, first_visible, human_pause, type_text

CREATE = ['svg[aria-label="Bài viết mới"]', 'svg[aria-label="New post"]',
          'a:has(svg[aria-label="Tạo"])', 'a:has(svg[aria-label="Create"])',
          'span:has-text("Tạo")', 'span:has-text("Create")']
POST_MENU = ['span:has-text("Bài viết")', 'span:has-text("Post")']
DIALOG = 'div[role="dialog"]'
NEXT = [f'{DIALOG} div[role="button"]:text-is("Tiếp")', f'{DIALOG} div[role="button"]:text-is("Next")']
CAPTION = [f'{DIALOG} div[aria-label="Viết chú thích..."]', f'{DIALOG} div[aria-label="Write a caption..."]',
           f'{DIALOG} div[role="textbox"]']
SHARE = [f'{DIALOG} div[role="button"]:text-is("Chia sẻ")', f'{DIALOG} div[role="button"]:text-is("Share")']
DONE = ['text=Đã chia sẻ bài viết', 'text=Your post has been shared',
        'text=Đã chia sẻ thước phim', 'text=Your reel has been shared']


class InstagramBrowser(BrowserPublisher):
    name = "instagram"
    home_url = "https://www.instagram.com/"

    def post(self, page, post) -> dict:
        media = post.videos[:1] or post.images[:10]
        if not media:
            raise PlatformError("Instagram bắt buộc phải có ảnh hoặc video")
        click(page, CREATE)
        human_pause()
        if any(page.locator(s).first.is_visible() for s in POST_MENU):
            click(page, POST_MENU)
        attach_files(page, media, f'{DIALOG} input[type=file]')
        human_pause(2, 5)
        # có thể hiện thông báo "Video được chia sẻ dưới dạng thước phim" -> OK
        ok = page.locator(f'{DIALOG} button:text-is("OK")')
        if ok.count() and ok.first.is_visible():
            ok.first.click()
        click(page, NEXT, timeout=120000)   # cắt ảnh
        click(page, NEXT)                   # bộ lọc
        type_text(page, CAPTION, post.text_for(self.name)[:2200])
        click(page, SHARE)
        first_visible(page, DONE, timeout=600000)
        human_pause(2, 4)
        return {"id": f"browser-{post.id}", "url": None, "method": "browser"}
