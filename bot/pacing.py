"""Nhịp đăng giống người thật: giới hạn số bài mỗi ngày và khoảng cách giữa hai bài.

Mục đích là không đăng dồn dập như spam, giảm nguy cơ tài khoản bị hạn chế.
Chỉnh trong .env:
  MAX_PER_DAY_FACEBOOK=5   MAX_PER_DAY_INSTAGRAM=3   MAX_PER_DAY_X=8   MAX_PER_DAY_TIKTOK=2
  MIN_GAP_MINUTES=30       (khoảng cách tối thiểu giữa hai bài trên cùng nền tảng)
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta

from .store import State

DEFAULT_MAX = {"facebook": 5, "instagram": 3, "x": 8, "tiktok": 2}


def max_per_day(platform: str) -> int:
    return int(os.getenv(f"MAX_PER_DAY_{platform.upper()}", DEFAULT_MAX[platform]))


def min_gap() -> timedelta:
    return timedelta(minutes=float(os.getenv("MIN_GAP_MINUTES", "30")))


def posted_times(state: State, platform: str) -> list[datetime]:
    times = []
    for platforms in state.data.get("posts", {}).values():
        at = platforms.get(platform, {}).get("at")
        if at:
            times.append(datetime.fromisoformat(at))
    return times


def why_wait(state: State, platform: str, now: datetime) -> str | None:
    """Trả lý do phải chờ, hoặc None nếu được đăng ngay."""
    times = posted_times(state, platform)
    today = [t for t in times if t.astimezone(now.tzinfo).date() == now.date()]
    if len(today) >= max_per_day(platform):
        return f"đã đủ {max_per_day(platform)} bài hôm nay"
    if times:
        last = max(times)
        if now - last < min_gap():
            wait = min_gap() - (now - last)
            return f"chờ thêm {int(wait.total_seconds() // 60) + 1} phút cho giãn cách"
    return None
