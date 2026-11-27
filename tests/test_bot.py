from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest
import yaml

from bot import rss
from bot.platforms.tiktok import chunk_plan
from bot.platforms.x import fit_text
from bot.store import State, due_jobs, load_post, load_posts

TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def make_post(root, name, **fields):
    folder = root / name
    folder.mkdir()
    data = {"text": "xin chào", "publish_at": "2026-12-01T09:00:00", **fields}
    (folder / "post.yaml").write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return folder


def test_load_post_defaults_and_timezone(tmp_path):
    post = load_post(make_post(tmp_path, "a"), tz="Asia/Ho_Chi_Minh")
    assert post.platforms == ["facebook", "instagram", "x", "tiktok"]
    assert post.publish_at.utcoffset().total_seconds() == 7 * 3600
    assert post.status == "approved"


def test_per_platform_text(tmp_path):
    post = load_post(make_post(tmp_path, "a", text_x="ngắn"))
    assert post.text_for("x") == "ngắn"
    assert post.text_for("facebook") == "xin chào"


def test_missing_media_and_bad_platform_are_skipped(tmp_path, capsys):
    make_post(tmp_path, "a", media=["khong-co.jpg"])
    make_post(tmp_path, "b", platforms=["myspace"])
    make_post(tmp_path, "c")
    assert [p.id for p in load_posts(tmp_path)] == ["c"]
    assert "bỏ qua" in capsys.readouterr().out


def test_due_jobs_respects_time_status_and_state(tmp_path):
    make_post(tmp_path, "som", platforms=["x", "facebook"])
    make_post(tmp_path, "muon", publish_at="2027-01-01T00:00:00")
    make_post(tmp_path, "nhap", status="draft")
    state = State(tmp_path / "state.json")
    state.record("som", "x", {"id": "1"})
    jobs = due_jobs(load_posts(tmp_path), state, datetime(2026, 12, 2, tzinfo=TZ))
    assert [(p.id, pl) for p, pl in jobs] == [("som", "facebook")]
    assert State(tmp_path / "state.json").done("som", "x")


def test_fit_text():
    assert fit_text("abc", None) == "abc"
    long = fit_text("a" * 400, "https://example.com/x")
    assert len(long.split("\n\n")[0]) == 280 - 25
    assert long.endswith("https://example.com/x")


@pytest.mark.parametrize("size,expected", [
    (1000, (1000, 1)),
    (5 * 1024 * 1024, (5 * 1024 * 1024, 1)),
    (25 * 1024 * 1024, (10 * 1024 * 1024, 2)),
])
def test_chunk_plan(size, expected):
    assert chunk_plan(size) == expected


def test_rss_creates_drafts_once(tmp_path):
    entries = [{"title": "Tin nóng hôm nay!", "link": "https://news.example/1"}]
    fake = lambda url: SimpleNamespace(entries=entries, feed={"title": "Báo Mẫu"})
    state = State(tmp_path / "state.json")
    posts = tmp_path / "posts"
    posts.mkdir()
    feeds = [{"url": "https://news.example/rss"}]
    created = rss.fetch(feeds, state, posts, parse=fake)
    assert len(created) == 1
    post = load_post(created[0])
    assert post.status == "draft" and post.link == "https://news.example/1"
    assert "Nguồn: Báo Mẫu" in post.text
    assert rss.fetch(feeds, state, posts, parse=fake) == []
