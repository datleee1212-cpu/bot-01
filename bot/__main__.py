"""Dòng lệnh của bot.

  python -m bot list              Xem hàng đợi và trạng thái
  python -m bot run --dry-run     Xem bài nào sắp được đăng, không đăng thật
  python -m bot run               Đăng các bài đã đến giờ
  python -m bot loop              Chạy liên tục, kiểm tra mỗi 5 phút
  python -m bot rss               Lấy tin từ config/feeds.yaml thành bản nháp
  python -m bot tiktok-login      Lấy refresh token TikTok lần đầu
"""
from __future__ import annotations

import argparse
import secrets
import time
import traceback
from datetime import datetime
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

import requests

from . import config, rss
from .store import State, due_jobs, load_posts


def now() -> datetime:
    return datetime.now(ZoneInfo(config.TIMEZONE))


def cmd_list(_args) -> None:
    state = State()
    for post in load_posts():
        marks = []
        for p in post.platforms:
            marks.append(f"{p}:{'✓' if state.done(post.id, p) else '·'}")
        print(f"{post.publish_at:%Y-%m-%d %H:%M}  [{post.status:8}] {post.id}  {' '.join(marks)}")


def cmd_run(args) -> int:
    from .platforms import PUBLISHERS

    state = State()
    jobs = due_jobs(load_posts(), state, now())
    if args.only:
        jobs = [j for j in jobs if j[1] in args.only]
    if not jobs:
        print("Không có bài nào cần đăng.")
        return 0
    publishers, failures = {}, 0
    for post, platform in jobs:
        label = f"{post.id} → {platform}"
        if args.dry_run:
            media = ", ".join(m.name for m in post.media) or "không có media"
            print(f"[thử] {label}: {post.text_for(platform)[:60]!r} ({media})")
            continue
        try:
            if platform not in publishers:
                publishers[platform] = PUBLISHERS[platform]()
            result = publishers[platform].publish(post)
            result["at"] = now().isoformat()
            state.record(post.id, platform, result)
            print(f"[xong] {label}: {result.get('url') or result.get('status') or result['id']}")
        except Exception as exc:
            failures += 1
            print(f"[lỗi] {label}: {exc}")
            if args.verbose:
                traceback.print_exc()
    return 1 if failures else 0


def cmd_loop(args) -> None:
    print(f"Bot đang chạy, kiểm tra mỗi {args.every} giây. Ctrl+C để dừng.")
    while True:
        cmd_run(args)
        time.sleep(args.every)


def cmd_rss(_args) -> None:
    created = rss.fetch(rss.load_feeds(), State())
    for folder in created:
        print(f"[nháp] {folder.name}")
    print(f"Tạo {len(created)} bản nháp. Sửa nội dung rồi đổi status thành approved để đăng.")


def cmd_tiktok_login(args) -> None:
    key = config.env("TIKTOK_CLIENT_KEY")
    secret = config.env("TIKTOK_CLIENT_SECRET")
    redirect = config.env("TIKTOK_REDIRECT_URI")
    scope = "video.publish" if args.direct else "video.upload"
    url = "https://www.tiktok.com/v2/auth/authorize/?" + urlencode({
        "client_key": key, "scope": f"user.info.basic,{scope}", "response_type": "code",
        "redirect_uri": redirect, "state": secrets.token_urlsafe(8)})
    print("1. Mở link sau, đăng nhập TikTok và đồng ý:\n" + url)
    code = input("2. Dán giá trị 'code' trên thanh địa chỉ sau khi chuyển hướng: ").strip()
    res = requests.post("https://open.tiktokapis.com/v2/oauth/token/", data={
        "client_key": key, "client_secret": secret, "code": code,
        "grant_type": "authorization_code", "redirect_uri": redirect}, timeout=60).json()
    if "refresh_token" not in res:
        raise SystemExit(f"Lỗi: {res}")
    config.TokenStore().set("tiktok", {
        "access_token": res["access_token"], "refresh_token": res["refresh_token"],
        "expires_at": time.time() + int(res.get("expires_in", 86400))})
    print("Đã lưu token vào .secrets/tokens.json")


def main() -> int:
    parser = argparse.ArgumentParser(prog="bot", description="Bot tự động đăng bài")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list").set_defaults(fn=cmd_list)
    for name, fn in (("run", cmd_run), ("loop", cmd_loop)):
        p = sub.add_parser(name)
        p.add_argument("--dry-run", action="store_true", help="chỉ in ra, không đăng thật")
        p.add_argument("--only", nargs="+", choices=["facebook", "instagram", "x", "tiktok"])
        p.add_argument("-v", "--verbose", action="store_true")
        if name == "loop":
            p.add_argument("--every", type=int, default=300)
        p.set_defaults(fn=fn)
    sub.add_parser("rss").set_defaults(fn=cmd_rss)
    p = sub.add_parser("tiktok-login")
    p.add_argument("--direct", action="store_true", help="xin quyền video.publish")
    p.set_defaults(fn=cmd_tiktok_login)
    args = parser.parse_args()
    return args.fn(args) or 0


if __name__ == "__main__":
    raise SystemExit(main())
