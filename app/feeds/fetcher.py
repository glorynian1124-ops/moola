"""RSS 抓取：遍历订阅源 → feedparser 解析 → 去重入库 → 生成摘要。"""
import time
from typing import Optional

import feedparser

from .. import models
from . import summarizer


def entry_to_article(entry, source_id: int) -> dict:
    """从 feedparser entry 提取字段（纯函数，便于测试）。"""
    title = getattr(entry, "title", "") or ""
    url = getattr(entry, "link", "") or getattr(entry, "id", "") or ""
    summary = getattr(entry, "summary", "") or getattr(entry, "description", "") or ""
    published = ""
    if getattr(entry, "published_parsed", None):
        published = time.strftime("%Y-%m-%d %H:%M:%S", entry.published_parsed)
    else:
        published = getattr(entry, "published", "") or ""
    return {
        "source_id": source_id,
        "title": title,
        "url": url,
        "summary": summary,
        "topic": "",
        "publish_time": published,
    }


def fetch_source(source: dict) -> tuple[int, int]:
    """抓取单个源，返回 (新增数, 跳过数)。"""
    try:
        parsed = feedparser.parse(source["url"])
    except Exception as e:  # noqa: BLE001 —— 单个源失败不阻断
        print(f"  ⚠️ 源「{source['name']}」抓取失败：{e}")
        return 0, 0
    added = skipped = 0
    for entry in parsed.entries:
        art = entry_to_article(entry, source["id"])
        if not art["url"]:
            continue
        ok = models.add_article(**art)
        if ok:
            added += 1
            s = summarizer.summarize_article(art["title"], art["summary"])
            if s:
                _update_summary(art["url"], s)
        else:
            skipped += 1
    return added, skipped


def _update_summary(url: str, summary: str) -> None:
    from ..db import get_conn
    conn = get_conn()
    try:
        conn.execute("UPDATE articles SET summary = ? WHERE url = ?", (summary, url))
        conn.commit()
    finally:
        conn.close()


def fetch_all() -> dict:
    """抓取所有启用源，返回 {added, skipped}。"""
    added = skipped = 0
    for src in models.list_sources():
        if not src.get("enabled", 1):
            continue
        a, s = fetch_source(src)
        added += a
        skipped += s
    return {"added": added, "skipped": skipped}
