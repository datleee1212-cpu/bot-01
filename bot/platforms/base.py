from __future__ import annotations

import time

import requests

from ..store import Post


class PlatformError(RuntimeError):
    pass


class Publisher:
    name = "base"

    def publish(self, post: Post) -> dict:
        """Đăng bài, trả về {"id": ..., "url": ...}."""
        raise NotImplementedError


def check(resp: requests.Response, what: str) -> dict:
    try:
        data = resp.json()
    except ValueError:
        data = {"raw": resp.text[:500]}
    err = data.get("error") if isinstance(data, dict) else None
    if isinstance(err, dict) and err.get("code") == "ok":  # TikTok trả error.code = "ok" khi thành công
        err = None
    if resp.status_code >= 400 or err:
        raise PlatformError(f"{what} lỗi HTTP {resp.status_code}: {data}")
    return data


def poll(fn, done, timeout: int = 300, every: int = 10):
    """Gọi fn() lặp lại cho tới khi done(kết quả) đúng hoặc hết thời gian."""
    deadline = time.time() + timeout
    while True:
        result = fn()
        if done(result):
            return result
        if time.time() > deadline:
            raise PlatformError(f"Hết thời gian chờ xử lý: {result}")
        time.sleep(every)
