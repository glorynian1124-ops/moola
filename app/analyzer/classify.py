"""AI 自动分类：商户名 + 备注 → 分类。

策略（成本优先，借鉴 actual-ai 工程模式）：
1. 先走分类规则库（category_rules 表 + config.yaml 兜底），命中即用，零成本
2. 规则未命中的才调大模型 API（DeepSeek，每日限流保护）
3. 规则命中会累计 hit_count → 学习权重；用户纠正分类可 learn_from_correction 写库
"""
import json
import os
import re
from datetime import date
from pathlib import Path
from typing import Optional

import yaml

from .. import models

BASE_DIR = Path(__file__).resolve().parent.parent.parent
_USAGE_FILE = BASE_DIR / "data" / "llm_usage.json"


def _load_config() -> dict:
    cfg_path = BASE_DIR / "config.yaml"
    if cfg_path.exists():
        return yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    return {}


# ---------- 简易每日限流器（借鉴 actual-ai：控制 API 费用不失控） ----------

class _DailyLimiter:
    """按天计数 LLM 调用次数，持久化到 data/llm_usage.json（重启不超）。"""

    def __init__(self) -> None:
        self._count = 0
        self._date = ""
        self._load()

    def _load(self) -> None:
        today = date.today().isoformat()
        self._date = today
        if _USAGE_FILE.exists():
            try:
                data = json.loads(_USAGE_FILE.read_text(encoding="utf-8"))
                self._count = data.get("count", 0)
                self._date = data.get("date", "")
            except Exception:  # noqa: BLE001
                self._count = 0
        if self._date != today:
            self._count = 0
            self._date = today

    def acquire(self, limit: int) -> bool:
        today = date.today().isoformat()
        if self._date != today:
            self._count = 0
            self._date = today
        if self._count >= limit:
            return False
        self._count += 1
        _USAGE_FILE.write_text(
            json.dumps({"date": self._date, "count": self._count}),
            encoding="utf-8",
        )
        return True


_LIMITER = _DailyLimiter()


def _config_rules() -> dict[str, list[str]]:
    """config.yaml 里的默认规则（兜底）。"""
    cfg = _load_config()
    return cfg.get("category_rules", {})


def _match_rule(
    text: str,
    db_rules: list[dict],
    config_rules: dict[str, list[str]],
) -> tuple[Optional[str], Optional[int]]:
    """① 数据库规则（用户/AI 学习，优先级高）② config 兜底。返回 (分类名, 规则id)。"""
    text = text or ""
    for r in db_rules:
        kw = str(r.get("keyword") or "").strip()
        if kw and kw in text:
            return r["category"], r["id"]
    for cat, keywords in config_rules.items():
        for kw in keywords:
            kw = str(kw).strip()
            if kw and kw in text:
                return cat, None
    return None, None


def learn_from_correction(merchant: str, category: str, source: str = "ai") -> bool:
    """用户手动纠正分类后调用：把商户关键词写入规则库（"越用越准"）。"""
    merchant = (merchant or "").strip()
    if not merchant or len(merchant) < 2:
        return False
    return models.add_rule(keyword=merchant, category=category, source=source)


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
        rows = [dict(r) for r in conn.execute(
            "SELECT * FROM transactions WHERE category IS NULL OR category = ''"
        ).fetchall()]
    finally:
        conn.close()

    if month:
        rows = [r for r in rows if r["trans_time"] and r["trans_time"][:7] == month]

    if not rows:
        print("没有未分类的记录 ✅")
        return 0

    db_rules = models.list_rules()          # 一次加载
    config_rules = _config_rules()
    llm_cfg = _load_config().get("llm", {})
    daily_limit = int(llm_cfg.get("max_calls_per_day", 30))
    remaining = max(0, daily_limit - _LIMITER._count)

    print(f"待分类 {len(rows)} 笔（规则优先，未命中再调 LLM，今日 LLM 余量 {remaining}）")
    done = 0
    for r in rows:
        text = f"{r['merchant']} {r['note']}"
        cat, rule_id = _match_rule(text, db_rules, config_rules)
        source = "rule"
        if cat is None:
            if _LIMITER.acquire(daily_limit):
                cat = _llm_classify(r["merchant"], r["note"])
                source = "llm"
                if cat is None:
                    cat = "其他支出"
                    source = "fallback"
            else:
                print("  ⚠️ 已达今日 LLM 上限，跳过（保留未分类，明天再跑）")
                continue
        elif rule_id:
            models.bump_rule(rule_id)       # 规则命中 → 学习权重

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
