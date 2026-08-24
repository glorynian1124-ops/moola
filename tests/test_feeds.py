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
