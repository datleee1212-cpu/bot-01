"""Đăng bài bằng cách tự thao tác trình duyệt, dùng tài khoản bạn đã đăng nhập sẵn.

Không cần khoá API. Mỗi nền tảng có một hồ sơ trình duyệt riêng trong .profiles/<nền tảng>,
bạn đăng nhập một lần bằng `python -m bot login <nền tảng>`, bot dùng lại phiên đó.

LƯU Ý RỦI RO: điều khoản của Facebook, Instagram, X và TikTok không cho phép tự động hoá
ngoài API chính thức. Tài khoản có thể bị hạn chế hoặc khoá. Bot cố tình đăng chậm, ít,
và KHÔNG vượt captcha hay kiểm tra bảo mật: khi gặp, bot dừng lại và chờ bạn tự xử lý.
"""
from __future__ import annotations

import os
import random
import re
import time
from contextlib import contextmanager
from pathlib import Path

from .. import config
from ..platforms.base import PlatformError

PROFILES_DIR = Path(os.getenv("PROFILES_DIR", config.ROOT / ".profiles"))

# Dấu hiệu nền tảng đang yêu cầu xác minh (captcha, checkpoint, đăng nhập lại)
CHECKPOINT_URL = re.compile(r"checkpoint|challenge|captcha|two_step|login|signin|accounts/suspended",
                            re.I)


class NeedsHuman(PlatformError):
    """Nền tảng đòi đăng nhập hoặc xác minh, cần bạn tự làm."""


def human_pause(lo: float = 0.8, hi: float = 2.5) -> None:
    time.sleep(random.uniform(lo, hi) * float(os.getenv("BROWSER_SPEED", "1")))


@contextmanager
def open_browser(platform: str, headless: bool | None = None):
    """Mở trình duyệt với hồ sơ đã đăng nhập của nền tảng."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise PlatformError(
            "Chưa cài Playwright: pip install playwright && playwright install chromium") from exc
    if headless is None:
        headless = os.getenv("BROWSER_HEADLESS", "false").lower() == "true"
    profile = PROFILES_DIR / platform
    profile.mkdir(parents=True, exist_ok=True)
    kwargs = {"headless": headless, "viewport": {"width": 1280, "height": 900},
              "locale": os.getenv("BROWSER_LOCALE", "vi-VN")}
    channel = os.getenv("BROWSER_CHANNEL")  # "chrome" để dùng Chrome đã cài trên máy
    if channel:
        kwargs["channel"] = channel
    exe = os.getenv("BROWSER_EXECUTABLE")
    if exe:
        kwargs["executable_path"] = exe
    with sync_playwright() as pw:
        context = pw.chromium.launch_persistent_context(str(profile), **kwargs)
        try:
            page = context.pages[0] if context.pages else context.new_page()
            page.set_default_timeout(int(os.getenv("BROWSER_TIMEOUT_MS", "30000")))
            yield page
        finally:
            context.close()


def first_visible(page, selectors: list[str], timeout: int = 15000):
    """Trả về phần tử hiện ra đầu tiên trong danh sách selector (hỗ trợ giao diện Việt/Anh)."""
    deadline = time.time() + timeout / 1000
    while time.time() < deadline:
        for sel in selectors:
            loc = page.locator(sel).first
            try:
                if loc.is_visible():
                    return loc
            except Exception:
                pass
        page.wait_for_timeout(300)
    raise PlatformError(f"Không tìm thấy phần tử trên trang: {selectors}")


def click(page, selectors: list[str], timeout: int = 15000) -> None:
    human_pause(0.4, 1.2)
    first_visible(page, selectors, timeout).click()


def type_text(page, selectors: list[str], text: str) -> None:
    box = first_visible(page, selectors)
    box.click()
    human_pause(0.3, 0.8)
    for i, line in enumerate(text.split("\n")):
        if i:
            page.keyboard.press("Shift+Enter")
        if line:
            page.keyboard.type(line, delay=random.randint(25, 70))


def attach_files(page, files: list[Path], selector: str = "input[type=file]") -> None:
    if not files:
        return
    page.locator(selector).first.set_input_files([str(f) for f in files])
    human_pause(2, 4)


def _blocked(page) -> bool:
    if CHECKPOINT_URL.search(page.url):
        return True
    try:  # còn ô nhập mật khẩu hoặc khung captcha nghĩa là chưa đăng nhập / đang bị kiểm tra
        return page.locator('input[type="password"], iframe[src*="captcha"]').first.is_visible()
    except Exception:
        return False


def guard_checkpoint(page, platform: str, wait_seconds: int | None = None) -> None:
    """Nếu nền tảng đòi đăng nhập/xác minh: chờ bạn tự xử lý trong cửa sổ trình duyệt.

    Bot không tự giải captcha. Hết thời gian chờ thì báo lỗi và dừng.
    """
    if not _blocked(page):
        return
    wait_seconds = wait_seconds if wait_seconds is not None else int(
        os.getenv("HUMAN_WAIT_SECONDS", "300"))
    print(f"[cần bạn] {platform} đang yêu cầu đăng nhập hoặc xác minh ({page.url}). "
          f"Hãy tự xử lý trong cửa sổ trình duyệt, bot chờ {wait_seconds} giây.")
    deadline = time.time() + wait_seconds
    while time.time() < deadline:
        page.wait_for_timeout(3000)
        if not _blocked(page):
            return
    raise NeedsHuman(f"{platform}: cần đăng nhập/xác minh. Chạy `python -m bot login {platform}`")


class BrowserPublisher:
    name = "base"
    home_url = ""

    def publish(self, post) -> dict:
        with open_browser(self.name) as page:
            page.goto(self.start_url(post))
            human_pause(2, 4)
            guard_checkpoint(page, self.name)
            return self.post(page, post)

    def start_url(self, post) -> str:
        return self.home_url

    def post(self, page, post) -> dict:
        raise NotImplementedError


def login(platform: str, url: str) -> None:
    """Mở trình duyệt để bạn tự đăng nhập; phiên được lưu trong .profiles/."""
    with open_browser(platform, headless=False) as page:
        page.goto(url)
        input(f"Đăng nhập {platform} trong cửa sổ vừa mở, xong thì quay lại đây bấm Enter... ")
    print(f"Đã lưu phiên đăng nhập {platform} vào {PROFILES_DIR / platform}")
