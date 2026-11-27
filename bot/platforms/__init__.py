"""Chọn cách đăng cho từng nền tảng.

POST_METHOD=browser (mặc định): tự thao tác trình duyệt, không cần khoá API.
POST_METHOD=api: dùng API chính thức (an toàn hơn cho tài khoản, cần khoá API).
Có thể chọn riêng từng nền tảng: POST_METHOD_X=api, POST_METHOD_TIKTOK=browser...
"""
import os


def method_for(platform: str) -> str:
    return (os.getenv(f"POST_METHOD_{platform.upper()}") or os.getenv("POST_METHOD")
            or "browser").lower()


def get_publisher(platform: str):
    if method_for(platform) == "api":
        from .facebook import FacebookPublisher
        from .instagram import InstagramPublisher
        from .tiktok import TikTokPublisher
        from .x import XPublisher
        classes = {"facebook": FacebookPublisher, "instagram": InstagramPublisher,
                   "x": XPublisher, "tiktok": TikTokPublisher}
    else:
        from ..browser.facebook import FacebookBrowser
        from ..browser.instagram import InstagramBrowser
        from ..browser.tiktok import TikTokBrowser
        from ..browser.x import XBrowser
        classes = {"facebook": FacebookBrowser, "instagram": InstagramBrowser,
                   "x": XBrowser, "tiktok": TikTokBrowser}
    return classes[platform]()
