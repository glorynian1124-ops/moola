"""AI 摘要与简报生成（Feedly 模式的 Leo 摘要 + AI 简报）。

复用 classify.py 的每日限流器（共享分类+摘要的每日 LLM 配额），
调用 DeepSeek（OpenAI 兼容接口）。
"""
import os
from datetime import date
from typing import Optional

from .. import models
from ..analyzer.classify import _LIMITER, _load_config


def _api_key() -> str:
    """返回已配置的 API key；无则空串。"""
    api_key = os.environ.get("MOOLA_API_KEY", "")
    if not api_key:
        api_key = _load_config().get("llm", {}).get("api_key", "")
    return api_key or ""


def _llm_chat(messages: list[dict], max_tokens: int = 400) -> Optional[str]:
    """通用 LLM 调用，返回文本；失败或无 key 返回 None。"""
    api_key = _api_key()
    if not api_key:
        return None
    cfg = _load_config().get("llm", {})
    import requests
    try:
        resp = requests.post(
            f"{cfg.get('base_url', 'https://api.deepseek.com/v1')}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": cfg.get("model", "deepseek-chat"),
                "messages": messages,
                "temperature": 0.3,
                "max_tokens": max_tokens,
            },
            timeout=30,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"].strip()
        return content or None
    except Exception as e:  # noqa: BLE001 —— 失败不阻断主流程
        print(f"  ⚠️ LLM 调用失败：{e}")
        return None


def summarize_article(title: str, content: str) -> str:
    """生成 1-3 句摘要；限流用尽/失败返回空串。"""
    if not _api_key():
        return ""
    limit = int(_load_config().get("llm", {}).get("max_calls_per_day", 30))
    if not _LIMITER.acquire(limit):
        return ""
    text = (content or "").strip()[:2000]
    prompt = (
        "你是财经新闻编辑。用 1-3 句中文概括下面这篇文章的核心信息，"
        "只输出摘要，不要标题、不要解释。\n"
        f"标题：{title}\n正文/简介：{text or '（无）'}"
    )
    ans = _llm_chat([{"role": "user", "content": prompt}], max_tokens=120)
    return (ans or "").strip()


def build_briefing_prompt(articles: list[dict]) -> str:
    """纯函数：把当天文章组装成简报 prompt。"""
    lines = []
    for i, a in enumerate(articles, 1):
        lines.append(f"{i}. {a.get('title', '')}｜{a.get('summary') or '无摘要'}")
    joined = "\n".join(lines)
    return (
        "你是财经资讯助手。基于以下今日文章，写一段「今日财经要闻」汇总（150 字以内），"
        "提炼共同主题与要点。只输出通用财经知识，不涉及具体投资标的推荐、不荐股。\n"
        f"文章列表：\n{joined}"
    )


def generate_briefing(day: Optional[str] = None) -> Optional[str]:
    """生成某天简报并存入 analysis_reports；返回汇总文本，失败返回 None。

    若指定日无文章，自动回退到「最近有文章的那天」，避免当天源未更新时生成失败。
    """
    day = day or date.today().isoformat()
    articles = models.list_articles(date=day, limit=50)
    if not articles:
        latest = models.list_articles(limit=1)
        if not latest or not latest[0].get("publish_time"):
            return None
        day = latest[0]["publish_time"][:10]
        articles = models.list_articles(date=day, limit=50)
    if not articles:
        return None
    if not _api_key():
        return None
    # 简报是用户手动触发的低频操作，不占用「AI 摘要」的每日配额
    prompt = build_briefing_prompt(articles)
    ans = _llm_chat([{"role": "user", "content": prompt}], max_tokens=400)
    if ans:
        models.add_report(period=day, kind="briefing", summary=ans)
    return ans


def latest_briefing() -> Optional[dict]:
    """取最近一次简报（供回看）。"""
    rows = models.list_reports(kind="briefing", limit=1)
    return rows[0] if rows else None
