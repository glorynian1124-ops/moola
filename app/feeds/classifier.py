"""文章主题分类：标题+摘要 → 财经主题（关键词规则优先，LLM 兜底）。

借鉴 app/analyzer/classify.py 的「规则优先 + LLM 兜底 + 每日限流」模式，
把文章打上 config.yaml 里预设的财经主题标签（存 articles.topic）。
"""
import os
import re
from typing import Optional

from .. import models
from ..analyzer.classify import _LIMITER, _load_config


_TOPIC_KEYWORDS = {
    "宏观": ["CPI", "PPI", "GDP", "降息", "降准", "通胀", "美联储", "央行", "利率",
             "货币政策", "财政部", "美债", "经济数据", "加息"],
    "股市": ["A股", "港股", "美股", "纳指", "标普", "道指", "指数", "涨停", "跌停",
             "板块", "估值", "牛市", "熊市", "开盘", "收盘", "科技股", "创业板"],
    "公司": ["财报", "净利润", "营收", "业绩", "年报", "季报", "上市", "IPO", "并购",
             "重组", "公司", "股东"],
    "黄金": ["黄金", "金价", "贵金属", "金条", "COMEX", "避险"],
    "债券": ["债券", "国债", "收益率", "债市", "信用债", "利率债", "发债"],
    "政策": ["政策", "监管", "法规", "国务院", "发改委", "证监会", "部委", "改革",
             "条例", "规划"],
    "科技": ["AI", "人工智能", "芯片", "半导体", "算力", "英伟达", "大模型", "科技",
             "互联网", "5G", "云计算", "存储芯片", "光通信"],
    "房地产": ["房地产", "房价", "楼市", "地产", "开发商", "商品房", "房贷", "土地"],
}


def list_topics() -> list[str]:
    """返回 config.yaml 里预设的主题列表。"""
    cfg = _load_config()
    return cfg.get("feeds", {}).get("topics", [])


def _rule_classify(text: str) -> Optional[str]:
    """关键词规则分类：按命中次数打分，返回最高分主题；无命中返回 None。"""
    scores: dict[str, int] = {}
    for topic, kws in _TOPIC_KEYWORDS.items():
        s = sum(1 for kw in kws if kw in text)
        if s:
            scores[topic] = s
    if not scores:
        return None
    return max(scores, key=scores.get)


def _llm_classify(title: str, summary: str) -> Optional[str]:
    """LLM 兜底分类，从预设主题里选一个。失败或无 key 返回 None。"""
    api_key = os.environ.get("MOOLA_API_KEY", "")
    cfg = _load_config().get("llm", {})
    if not api_key:
        api_key = cfg.get("api_key", "")
    if not api_key:
        return None
    topics = list_topics()
    import requests
    prompt = (
        f"你是财经新闻分类助手。从这些主题里选一个最合适的：{topics}。"
        f"只输出主题名，不要解释。\n标题：{title}\n内容：{(summary or '')[:200]}"
    )
    try:
        resp = requests.post(
            f"{cfg.get('base_url', 'https://api.deepseek.com/v1')}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": cfg.get("model", "deepseek-chat"),
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
                "max_tokens": 10,
            },
            timeout=15,
        )
        resp.raise_for_status()
        ans = resp.json()["choices"][0]["message"]["content"].strip()
        ans = re.sub(r"[。.、\n\"']", "", ans).strip()
        return ans if ans in topics else None
    except Exception as e:  # noqa: BLE001
        print(f"  ⚠️ 文章分类 LLM 调用失败：{e}")
        return None


def classify_article(title: str, summary: str) -> str:
    """给一篇文章打主题标签。规则优先，LLM 兜底，都失败返回空串。"""
    text = f"{title} {(summary or '')}"
    topic = _rule_classify(text)
    if topic:
        return topic
    limit = int(_load_config().get("llm", {}).get("max_calls_per_day", 30))
    if _LIMITER.acquire(limit):
        topic = _llm_classify(title, summary)
        if topic:
            return topic
    return ""


def classify_unclassified(limit: int = 500) -> int:
    """给未分类（topic 为空）的文章打标签。返回处理篇数。"""
    rows = [a for a in models.list_articles(limit=limit) if not a.get("topic")]
    n = 0
    for a in rows:
        topic = classify_article(a["title"], a.get("summary") or "")
        if topic:
            from ..db import get_conn
            conn = get_conn()
            try:
                conn.execute("UPDATE articles SET topic = ? WHERE id = ?", (topic, a["id"]))
                conn.commit()
            finally:
                conn.close()
            n += 1
    return n
