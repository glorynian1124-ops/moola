import os
import sqlite3
import tempfile
from pathlib import Path

import pytest


@pytest.fixture()
def tmp_db(monkeypatch):
    """用临时数据库隔离测试，不碰 data/moola.db。"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    monkeypatch.setattr("app.db.DB_PATH", Path(path))
    from app.db import init_db
    from app import models
    init_db()
    # 保证 source_id=1 有效（articles.source_id 有外键约束，且 PRAGMA foreign_keys=ON）
    models.add_source("测试源", "http://example.com/feed")
    yield
    os.unlink(path)


def test_add_article_dedup(tmp_db):
    from app import models
    ok1 = models.add_article(source_id=1, title="t", url="http://a.com/1", summary="s")
    ok2 = models.add_article(source_id=1, title="t", url="http://a.com/1", summary="s")
    assert ok1 is True
    assert ok2 is False
    assert len(models.list_articles()) == 1


def test_list_articles_filters_by_date(tmp_db):
    from app import models
    models.add_article(1, "旧", "http://a.com/2", "", publish_time="2026-08-20 08:00:00")
    models.add_article(1, "新", "http://a.com/3", "", publish_time="2026-08-24 08:00:00")
    today = models.list_articles(date="2026-08-24")
    assert len(today) == 1
    assert today[0]["title"] == "新"


def test_delete_source(tmp_db):
    from app import models
    models.add_source("财新", "http://rss.example.com")
    # fixture 已塞入"测试源"，这里只删刚新增的"财新"并校验其消失
    sid = next(s["id"] for s in models.list_sources() if s["name"] == "财新")
    assert models.delete_source(sid) is True
    assert all(s["id"] != sid for s in models.list_sources())


def test_delete_source_with_articles(tmp_db):
    from app import models
    models.add_source("源A", "http://rss.a.com")
    sid = next(s["id"] for s in models.list_sources() if s["name"] == "源A")
    models.add_article(sid, "文章", "http://a.com/art1", "")
    assert models.delete_source(sid) is True
    # 文章保留，source_id 被置空
    arts = models.list_articles()
    assert len(arts) == 1
    assert arts[0]["source_id"] is None


def test_build_briefing_prompt_lists_titles():
    from app.feeds.summarizer import build_briefing_prompt
    arts = [
        {"title": "CPI 环比回落", "summary": "居民消费价格涨幅收窄"},
        {"title": "央行降准", "summary": "释放长期流动性"},
    ]
    p = build_briefing_prompt(arts)
    assert "CPI 环比回落" in p
    assert "央行降准" in p
    assert "投资建议" in p or "不涉及" in p
