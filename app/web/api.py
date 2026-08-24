"""API 蓝图：前端原型 ↔ 后端数据库 的对接接口。

前缀 /api。所有金额 amount：负=支出，正=收入；时间 trans_time: YYYY-MM-DD HH:MM:SS。
"""
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from flask import Blueprint, jsonify, request

from .. import models
from ..analyzer import stats as stats_mod

api = Blueprint("api", __name__, url_prefix="/api")


def _ledger_id(value: object) -> Optional[int]:
    """解析并校验 ledger_id。空值/None → None（全库，向后兼容）。
    非法值抛 ValueError；账本不存在抛 LookupError。"""
    if value in (None, ""):
        return None
    try:
        lid = int(value)
    except (TypeError, ValueError):
        raise ValueError("ledger_id 必须为整数")
    if not models.get_ledger(lid):
        raise LookupError("账本不存在")
    return lid


# ---------- 账本 ----------

@api.get("/ledgers")
def list_ledgers():
    return jsonify({"ledgers": models.list_ledgers()})


@api.post("/ledgers")
def add_ledger():
    data = request.get_json(force=True)
    name = str(data.get("name") or "").strip()
    if not name:
        return jsonify({"ok": False, "error": "name 必填"}), 400
    new_id = models.add_ledger(
        name=name,
        type=str(data.get("type") or "标准账本"),
        icon=str(data.get("icon") or "ic_accounts.png"),
    )
    return jsonify({"ok": True, "id": new_id, "row": models.get_ledger(new_id)}), 201


@api.get("/ledgers/<int:ledger_id>")
def get_ledger(ledger_id: int):
    row = models.get_ledger(ledger_id)
    return jsonify(row) if row else (jsonify({"ok": False, "error": "账本不存在"}), 404)


@api.put("/ledgers/<int:ledger_id>")
def update_ledger(ledger_id: int):
    data = request.get_json(force=True)
    name = data.get("name")
    if name is not None and not str(name).strip():
        return jsonify({"ok": False, "error": "name 不能为空"}), 400
    ok = models.update_ledger(
        ledger_id,
        name=str(name).strip() if name else None,
        type=data.get("type"),
        icon=data.get("icon"),
    )
    if not ok:
        return jsonify({"ok": False, "error": "账本不存在"}), 404
    return jsonify({"ok": True, "row": models.get_ledger(ledger_id)})


@api.delete("/ledgers/<int:ledger_id>")
def delete_ledger(ledger_id: int):
    if models.ledger_count() <= 1:
        return jsonify({"ok": False, "error": "至少保留一个账本"}), 400
    deleted = models.delete_ledger(ledger_id)
    if deleted is None:
        return jsonify({"ok": False, "error": "账本不存在"}), 404
    return jsonify({"ok": True, "deleted_transactions": deleted})


# ---------- 账单 ----------

@api.get("/transactions")
def list_transactions():
    month = request.args.get("month", "") or None
    category = request.args.get("category", "") or None
    limit = int(request.args.get("limit", 500))
    try:
        ledger_id = _ledger_id(request.args.get("ledger_id"))
    except LookupError:
        return jsonify({"ok": False, "error": "账本不存在"}), 404
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    return jsonify(models.list_transactions(
        ledger_id=ledger_id, month=month, category=category, limit=limit))


@api.get("/transactions/group")
def transactions_group():
    """按日期分组，喂给前端明细页（数据同构）。支持 ledger_id。"""
    month = request.args.get("month", "") or None
    try:
        ledger_id = _ledger_id(request.args.get("ledger_id"))
    except LookupError:
        return jsonify({"ok": False, "error": "账本不存在"}), 404
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    return jsonify(models.list_transactions_grouped(ledger_id=ledger_id, month=month))


@api.get("/transactions/<int:tx_id>")
def get_transaction(tx_id: int):
    row = models.get_transaction(tx_id)
    return jsonify(row) if row else (jsonify({"ok": False}), 404)


@api.post("/transactions")
def add_transaction():
    data = request.get_json(force=True)
    try:
        amount = float(data["amount"])
    except (KeyError, ValueError):
        return jsonify({"ok": False, "error": "amount 必填且为数字"}), 400
    try:
        ledger_id = _ledger_id(data.get("ledger_id"))
    except LookupError:
        return jsonify({"ok": False, "error": "账本不存在"}), 404
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    new_id = models.add_transaction(
        amount=amount,
        category=data.get("category", "其他支出"),
        merchant=data.get("merchant", ""),
        note=data.get("note", ""),
        trans_time=data.get("trans_time") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        source=data.get("source", "manual"),
        ledger_id=ledger_id or 1,
    )
    if new_id is None:
        return jsonify({"ok": False, "duplicate": True})
    row = models.get_transaction(new_id)
    return jsonify({"ok": True, "id": new_id, "row": row})


@api.put("/transactions/<int:tx_id>")
def update_transaction(tx_id: int):
    data = request.get_json(force=True)
    if "ledger_id" in data and data["ledger_id"] is not None:
        try:
            data["ledger_id"] = _ledger_id(data["ledger_id"])
        except LookupError:
            return jsonify({"ok": False, "error": "账本不存在"}), 404
        except ValueError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400
    return jsonify({"ok": models.update_transaction(tx_id, **data)})


@api.delete("/transactions/<int:tx_id>")
def delete_transaction(tx_id: int):
    return jsonify({"ok": models.delete_transaction(tx_id)})


# ---------- 统计 / 日历 ----------

@api.get("/stats/trend")
def stats_trend():
    try:
        ledger_id = _ledger_id(request.args.get("ledger_id"))
    except LookupError:
        return jsonify({"ok": False, "error": "账本不存在"}), 404
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    return jsonify(stats_mod.trend(
        period=request.args.get("period", "week"),
        cat=request.args.get("cat", "expense"),
        end=request.args.get("end"),
        ledger_id=ledger_id,
    ))


@api.get("/stats/category")
def stats_category():
    try:
        ledger_id = _ledger_id(request.args.get("ledger_id"))
    except LookupError:
        return jsonify({"ok": False, "error": "账本不存在"}), 404
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    return jsonify(stats_mod.category_share(
        month=request.args.get("month", "") or None,
        cat=request.args.get("cat", "expense"),
        ledger_id=ledger_id,
    ))


@api.get("/calendar")
def api_calendar():
    try:
        ledger_id = _ledger_id(request.args.get("ledger_id"))
    except LookupError:
        return jsonify({"ok": False, "error": "账本不存在"}), 404
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    return jsonify(stats_mod.daily_calendar(
        request.args.get("month", "") or None, ledger_id=ledger_id))


# ---------- 搜索 ----------

@api.get("/search")
def api_search():
    try:
        ledger_id = _ledger_id(request.args.get("ledger_id"))
    except LookupError:
        return jsonify({"ok": False, "error": "账本不存在"}), 404
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    return jsonify(models.search_transactions(
        ledger_id=ledger_id,
        q=request.args.get("q", ""),
        mode=request.args.get("mode", "bill"),
        sort=request.args.get("sort", "time"),
        order=request.args.get("order", "desc"),
    ))


# ---------- 分类 ----------

@api.get("/categories")
def list_categories():
    return jsonify(models.list_categories())


@api.post("/categories")
def add_category():
    data = request.get_json(force=True)
    ok = models.add_category(data.get("name", ""), data.get("kind", "expense"))
    return jsonify({"ok": ok})


# ---------- 导入（CSV 上传） ----------

@api.post("/import/<source>")
def import_csv(source: str):
    """POST multipart: file=<CSV>。source: wechat | alipay。"""
    if source not in ("wechat", "alipay"):
        return jsonify({"ok": False, "error": "source 仅支持 wechat/alipay"}), 400
    f = request.files.get("file")
    if not f:
        return jsonify({"ok": False, "error": "缺少文件字段 file"}), 400

    tmp = Path(tempfile.gettempdir()) / f"moola_import_{datetime.now().strftime('%H%M%S')}.csv"
    f.save(tmp)
    try:
        if source == "wechat":
            from ..parser.wechat_csv import parse_wechat_csv
            records = parse_wechat_csv(tmp)
        else:
            from ..parser.alipay_csv import parse_alipay_csv
            records = parse_alipay_csv(tmp)
    finally:
        tmp.unlink(missing_ok=True)

    added, skipped = models.add_many(records)
    classified = 0
    if added:
        # 导入即自动分类（规则优先，LLM 受限流保护）
        from ..analyzer.classify import classify_unclassified
        classified = classify_unclassified()
    return jsonify({
        "ok": True, "parsed": len(records), "added": added, "skipped": skipped,
        "classified": classified,
    })


# ---------- 报告（复用现有） ----------

@api.get("/report")
def api_report():
    from ..analyzer.report import monthly_report
    try:
        ledger_id = _ledger_id(request.args.get("ledger_id"))
    except LookupError:
        return jsonify({"ok": False, "error": "账本不存在"}), 404
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    return jsonify(monthly_report(
        request.args.get("month", "") or None, ledger_id=ledger_id))


# ---------- AI 服务 Key（管理平台：查看/分配/修改） ----------

@api.get("/ai-keys")
def list_ai_keys():
    """列表（api_key 脱敏）。可 ?scope=system|user 过滤。"""
    scope = request.args.get("scope") or None
    return jsonify({"keys": models.list_ai_keys(scope)})


@api.post("/ai-keys")
def add_ai_key():
    data = request.get_json(force=True)
    name = str(data.get("name") or "").strip()
    api_key = str(data.get("api_key") or "").strip()
    if not name or not api_key:
        return jsonify({"ok": False, "error": "name 与 api_key 必填"}), 400
    new_id = models.add_ai_key(
        name=name,
        api_key=api_key,
        provider=str(data.get("provider") or "deepseek"),
        base_url=str(data.get("base_url") or "https://api.deepseek.com/v1"),
        model=str(data.get("model") or "deepseek-v4-flash"),
        scope=str(data.get("scope") or "user"),
        user_ref=str(data.get("user_ref") or ""),
        status=1 if int(data.get("status", 1)) else 0,
        quota=float(data.get("quota") or 0),
        note=str(data.get("note") or ""),
    )
    return jsonify({"ok": True, "id": new_id, "row": models.get_ai_key(new_id)}), 201


@api.get("/ai-keys/<int:key_id>")
def get_ai_key(key_id: int):
    """详情（含真实 api_key，管理端查看）。"""
    row = models.get_ai_key(key_id)
    return jsonify(row) if row else (jsonify({"ok": False, "error": "Key 不存在"}), 404)


@api.put("/ai-keys/<int:key_id>")
def update_ai_key(key_id: int):
    data = request.get_json(force=True)
    fields = {k: data.get(k) for k in (
        "name", "provider", "base_url", "model",
        "api_key", "scope", "user_ref", "note")}
    if "status" in data:
        fields["status"] = 1 if int(data["status"]) else 0
    if "quota" in data and data["quota"] is not None:
        fields["quota"] = float(data["quota"])
    ok = models.update_ai_key(
        key_id, **{k: v for k, v in fields.items() if v is not None})
    if not ok:
        return jsonify({"ok": False, "error": "Key 不存在"}), 404
    return jsonify({"ok": True, "row": models.get_ai_key(key_id)})


@api.delete("/ai-keys/<int:key_id>")
def delete_ai_key(key_id: int):
    ok = models.delete_ai_key(key_id)
    return (jsonify({"ok": True}) if ok
            else (jsonify({"ok": False, "error": "Key 不存在"}), 404))


# ---------- AI 聊天会话（经济分析 · 可回溯存储） ----------

@api.get("/ai/conversations")
def list_ai_conversations():
    """会话列表：{conversations:[{id,title,created_at,updated_at}]}。"""
    return jsonify({"conversations": models.list_ai_conversations()})


@api.get("/ai/conversations/<int:conv_id>")
def get_ai_conversation(conv_id: int):
    """会话详情：{conversation:{id,title,created_at,updated_at,messages:[{role,content}]}}。"""
    row = models.get_ai_conversation(conv_id)
    if not row:
        return jsonify({"ok": False, "error": "会话不存在"}), 404
    return jsonify({"conversation": row})


@api.post("/ai/conversations")
def save_ai_conversation():
    """创建/保存会话快照。body: {id?, title?, messages?:[{role,content}]}
    - 无 id → 新建会话；有 id → 更新 title 并按 messages 重建消息（快照替换）。"""
    data = request.get_json(force=True)
    conv_id = data.get("id")
    if conv_id is not None:
        try:
            conv_id = int(conv_id)
        except (TypeError, ValueError):
            return jsonify({"ok": False, "error": "id 必须为整数"}), 400
    messages = data.get("messages")
    if messages is not None and not isinstance(messages, list):
        return jsonify({"ok": False, "error": "messages 必须为数组"}), 400
    new_id = models.save_ai_conversation(
        conv_id=conv_id, title=data.get("title"), messages=messages)
    if new_id is None:
        return jsonify({"ok": False, "error": "会话不存在"}), 404
    return jsonify({
        "ok": True, "id": new_id,
        "conversation": models.get_ai_conversation(new_id),
    }), 201


@api.delete("/ai/conversations/<int:conv_id>")
def delete_ai_conversation(conv_id: int):
    ok = models.delete_ai_conversation(conv_id)
    return (jsonify({"ok": True}) if ok
            else (jsonify({"ok": False, "error": "会话不存在"}), 404))


# ---------- AI 聊天代理（后端转发 DeepSeek + 自动落库） ----------

@api.post("/ai/chat")
def ai_chat():
    """后端代理：统一转发到 DeepSeek（Key 不出现在前端）。
    body: {messages:[{role,content}], model?, conversation_id?}
    - 带 conversation_id 且会话存在时，自动把 user 提问 + AI 回复追加落库（可回溯）。
    返回 {ok:true, reply}。"""
    import requests  # noqa: E402

    data = request.get_json(force=True)
    messages = data.get("messages")
    if not isinstance(messages, list) or not messages:
        return jsonify({"ok": False, "error": "messages 必填且为非空数组"}), 400
    user_msgs = [m for m in messages if (m or {}).get("role") == "user"]
    if not user_msgs:
        return jsonify({"ok": False, "error": "至少需要一条 user 消息"}), 400
    prompt = str(user_msgs[-1].get("content") or "").strip()
    if not prompt:
        return jsonify({"ok": False, "error": "消息内容为空"}), 400

    # 取 Key：ai_keys 表（启用）→ 环境变量 MOOLA_API_KEY → config.yaml
    key_row = models.get_active_ai_key("deepseek")
    api_key = key_row["api_key"] if key_row else ""
    base_url = (key_row["base_url"] if key_row else "https://api.deepseek.com/v1").rstrip("/")
    model = str(data.get("model") or (key_row["model"] if key_row else "deepseek-v4-flash"))
    if not api_key:
        api_key = os.environ.get("MOOLA_API_KEY", "")
    if not api_key:
        from ..analyzer.classify import _load_config
        api_key = str((_load_config().get("llm") or {}).get("api_key") or "")
    if not api_key:
        return jsonify({"ok": False, "error": "未配置 API Key（请设 MOOLA_API_KEY 或在 ai_keys 表配置）"}), 400

    try:
        resp = requests.post(
            base_url + "/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": model, "messages": messages, "stream": False},
            timeout=60,
        )
        resp.raise_for_status()
        reply = resp.json()["choices"][0]["message"]["content"]
    except Exception as e:  # noqa: BLE001
        return jsonify({"ok": False, "error": f"AI 服务调用失败：{e}"}), 502

    # 自动落库：带 conversation_id 且存在 → 追加 user 提问 + AI 回复
    conv_id = data.get("conversation_id")
    if conv_id is not None:
        try:
            conv_id = int(conv_id)
            conv = models.get_ai_conversation(conv_id)
            if conv:
                models.save_ai_conversation(
                    conv_id=conv_id,
                    messages=conv["messages"] + [
                        {"role": "user", "content": prompt},
                        {"role": "ai", "content": reply},
                    ],
                )
        except Exception:  # noqa: BLE001 —— 落库失败不影响回复
            pass

    return jsonify({"ok": True, "reply": reply})


# ---------- 经济简讯（Feedly 模式） ----------

@api.get("/feeds/sources")
def list_feed_sources():
    return jsonify(models.list_sources())


@api.post("/feeds/sources")
def add_feed_source():
    data = request.get_json(force=True)
    if not isinstance(data, dict):
        return jsonify({"ok": False, "error": "请求体必须为 JSON 对象"}), 400
    name = str(data.get("name") or "").strip()
    url = str(data.get("url") or "").strip()
    if not name or not url:
        return jsonify({"ok": False, "error": "name 和 url 必填"}), 400
    ok = models.add_source(name, url)
    return jsonify({"ok": ok})


@api.delete("/feeds/sources/<int:source_id>")
def delete_feed_source(source_id: int):
    return jsonify({"ok": models.delete_source(source_id)})


@api.post("/feeds/fetch")
def fetch_feeds():
    from ..feeds.fetcher import fetch_all
    return jsonify(fetch_all())


@api.get("/feeds/articles")
def list_feed_articles():
    date = request.args.get("date", "") or None
    return jsonify(models.list_articles(date=date, limit=int(request.args.get("limit", 200))))


@api.post("/feeds/briefing")
def make_briefing():
    from datetime import date
    from ..feeds.summarizer import generate_briefing
    day = date.today().isoformat()
    if not models.list_articles(date=day, limit=1):
        return jsonify({"ok": False, "error": "今天没有文章"}), 404
    text = generate_briefing(day)
    if text is None:
        return jsonify({"ok": False, "error": "简报生成失败（LLM 未配置或已达限流）"}), 502
    return jsonify({"ok": True, "briefing": text})


@api.get("/feeds/briefing")
def get_briefing():
    from ..feeds.summarizer import latest_briefing
    row = latest_briefing()
    return jsonify(row) if row else (jsonify({"ok": False}), 404)
