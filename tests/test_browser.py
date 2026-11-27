"""Chạy thử các thao tác trình duyệt trên trang giả lập (không vào mạng xã hội thật)."""
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
import yaml

from bot import pacing
from bot.store import State, load_post

playwright = pytest.importorskip("playwright.sync_api")

TZ = ZoneInfo("Asia/Ho_Chi_Minh")

X_PAGE = """<html><body>
<div data-testid="tweetTextarea_0" role="textbox" contenteditable="true"></div>
<input type="file" data-testid="fileInput" multiple>
<div data-testid="tweetButton" role="button" onclick="
  window.sent = document.querySelector('[data-testid=tweetTextarea_0]').innerText;
  window.files = document.querySelector('input[type=file]').files.length;
  document.querySelector('[data-testid=tweetTextarea_0]').innerText='';
  var t=document.createElement('div'); t.dataset.testid='toast'; t.innerText='Đã gửi';
  document.body.appendChild(t);">Đăng</div>
</body></html>"""

LOGIN_PAGE = "<html><body><input type='text'><input type='password'></body></html>"


@pytest.fixture
def browser_env(tmp_path, monkeypatch):
    monkeypatch.setenv("BROWSER_HEADLESS", "true")
    monkeypatch.setenv("BROWSER_SPEED", "0.01")
    monkeypatch.setenv("HUMAN_WAIT_SECONDS", "1")
    exe = "/opt/pw-browsers/chromium"
    if os.path.exists(exe):
        monkeypatch.setenv("BROWSER_EXECUTABLE", exe)
    import bot.browser as b
    monkeypatch.setattr(b, "PROFILES_DIR", tmp_path / "profiles")
    return tmp_path


def make_post(tmp_path, **fields):
    folder = tmp_path / "bai"
    folder.mkdir()
    (folder / "anh.jpg").write_bytes(b"\xff\xd8\xff\xd9")
    data = {"text": "Dòng một\nDòng hai", "publish_at": "2026-11-01T09:00:00", **fields}
    (folder / "post.yaml").write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return load_post(folder)


def serve(monkeypatch, html):
    """Thay mọi trang web bằng html giả lập."""
    import bot.browser as b
    real = b.open_browser

    from contextlib import contextmanager

    @contextmanager
    def fake(platform, headless=None):
        with real(platform, headless=True) as page:
            page.context.route("**/*", lambda route: route.fulfill(
                status=200, content_type="text/html; charset=utf-8", body=html))
            yield page
            fake.last = page.evaluate("({sent: window.sent, files: window.files})")

    monkeypatch.setattr(b, "open_browser", fake)
    return fake


def test_x_browser_flow(browser_env, monkeypatch):
    from bot.browser.x import XBrowser
    post = make_post(browser_env, media=["anh.jpg"], link="https://vd.vn/a")
    fake = serve(monkeypatch, X_PAGE)
    result = XBrowser().publish(post)
    assert result["method"] == "browser"
    assert fake.last["files"] == 1
    assert "Dòng một" in fake.last["sent"] and "Dòng hai" in fake.last["sent"]
    assert "https://vd.vn/a" in fake.last["sent"]


def test_login_wall_stops_and_asks_human(browser_env, monkeypatch):
    from bot.browser import NeedsHuman
    from bot.browser.x import XBrowser
    post = make_post(browser_env)
    serve(monkeypatch, LOGIN_PAGE)
    with pytest.raises(NeedsHuman):
        XBrowser().publish(post)


def test_pacing_daily_cap_and_gap(tmp_path, monkeypatch):
    monkeypatch.setenv("MAX_PER_DAY_X", "2")
    monkeypatch.setenv("MIN_GAP_MINUTES", "30")
    state = State(tmp_path / "s.json")
    now = datetime(2026, 12, 1, 12, 0, tzinfo=TZ)
    assert pacing.why_wait(state, "x", now) is None
    state.record("a", "x", {"id": "1", "at": (now - timedelta(minutes=10)).isoformat()})
    assert "giãn cách" in pacing.why_wait(state, "x", now)
    assert pacing.why_wait(state, "facebook", now) is None
    state.record("b", "x", {"id": "2", "at": (now - timedelta(hours=2)).isoformat()})
    assert "đủ 2 bài" in pacing.why_wait(state, "x", now + timedelta(hours=1))
    assert pacing.why_wait(state, "x", now + timedelta(days=1)) is None
