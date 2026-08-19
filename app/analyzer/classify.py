"""AI 自动分类：商户名 + 备注 → 分类。

策略（成本优先）：
1. 先走本地关键词规则库（config.yaml category_rules），命中即用，零成本
2. 规则未命中的才调大模型 API（DeepSeek，默认每日上限 30 次）
"""
import os
import re
from pathlib import Path
from typing import Optional

import yaml

from .. import models

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def _load_config() -> dict:
    cfg_path = BASE_DIR / "config.yaml"
    if cfg_path.exists():
        return yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    return {}


def _rules() -> dict[str, list[str]]:
    cfg = _load_config()
    return cfg.get("category_rules", {})


def _rule_classify(text: str) -> Optional[str]:
    """关键词规则分类，命中返回分类名，未命中返回 None。"""
    text = text or ""
    for cat, keywords in _rules().items():
        for kw in keywords:
            if kw and kw in text:
                return cat
    return None


def _llm_classify(merchant: str, note: str) -> Optional[str]:
    """调大模型 API 分类。返回分类名；失败或无 key 返回 None。"""
    api_key = os.environ.get("MOOLA_API_KEY", "")
    cfg = _load_config().get("llm", {})
    if not api_key:
        api_key = cfg.get("api_key", "")
    if not api_key:
        return None

    import requests

    categories = [c["name"] for c in models.list_categories() if c["kind"] == "expense"]
    prompt = (
        f"你是记账分类助手。根据交易对方和备注，从这些分类中选一个最合适的："
        f"{categories}。只输出分类名，不要解释。\n"
        f"交易对方：{merchant}\n备注：{note or '无'}"
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
        # 过滤模型可能输出的多余字符
        ans = re.sub(r"[。.、\n\"']", "", ans).strip()
        valid = {c["name"] for c in models.list_categories()}
        return ans if ans in valid else None
    except Exception as e:  # noqa: BLE001 —— 分类失败不阻断主流程
        print(f"  ⚠️ LLM 调用失败：{e}")
        return None


def classify_unclassified(month: Optional[str] = None) -> int:
    """给未分类的账单打分类。返回处理笔数。"""
    from ..db import get_conn

    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM transactions WHERE category IS NULL OR category = ''"
        ).fetchall()
        rows = [dict(r) for r in rows]
    finally:
        conn.close()

    if month:
        rows = [r for r in rows if r["trans_time"] and r["trans_time"][:7] == month]

    if not rows:
        print("没有未分类的记录 ✅")
        return 0

    print(f"待分类 {len(rows)} 笔（规则优先，未命中再调 LLM）")
    done = 0
    for r in rows:
        text = f"{r['merchant']} {r['note']}"
        cat = _rule_classify(text)
        source = "rule"
        if cat is None:
            cat = _llm_classify(r["merchant"], r["note"])
            source = "llm"
            if cat is None:
                cat = "其他支出"
                source = "fallback"
        conn = get_conn()
        try:
            conn.execute(
                "UPDATE transactions SET category = ? WHERE id = ?", (cat, r["id"])
            )
            conn.commit()
        finally:
            conn.close()
        done += 1
        print(f"  [{source}] {r['merchant'][:20]:<20} → {cat}")
    return done
