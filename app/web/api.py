"""API 蓝图：前端原型 ↔ 后端数据库 的对接接口。

前缀 /api。所有金额 amount：负=支出，正=收入；时间 trans_time: YYYY-MM-DD HH:MM:SS。
"""
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
