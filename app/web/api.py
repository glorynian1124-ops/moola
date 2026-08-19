"""API 蓝图：前端原型 ↔ 后端数据库 的对接接口。

前缀 /api。所有金额 amount：负=支出，正=收入；时间 trans_time: YYYY-MM-DD HH:MM:SS。
"""
import tempfile
from datetime import datetime
from pathlib import Path

from flask import Blueprint, jsonify, request

from .. import models
from ..analyzer import stats as stats_mod

api = Blueprint("api", __name__, url_prefix="/api")


# ---------- 账单 ----------

@api.get("/transactions")
def list_transactions():
    month = request.args.get("month", "") or None
    category = request.args.get("category", "") or None
    limit = int(request.args.get("limit", 500))
    return jsonify(models.list_transactions(month=month, category=category, limit=limit))


@api.get("/transactions/group")
def transactions_group():
    """按日期分组，喂给前端明细页（数据同构）。"""
    month = request.args.get("month", "") or None
    return jsonify(models.list_transactions_grouped(month=month))


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
    new_id = models.add_transaction(
        amount=amount,
        category=data.get("category", "其他支出"),
        merchant=data.get("merchant", ""),
        note=data.get("note", ""),
        trans_time=data.get("trans_time") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        source=data.get("source", "manual"),
    )
    if new_id is None:
        return jsonify({"ok": False, "duplicate": True})
    row = models.get_transaction(new_id)
    return jsonify({"ok": True, "id": new_id, "row": row})


@api.put("/transactions/<int:tx_id>")
def update_transaction(tx_id: int):
    data = request.get_json(force=True)
    return jsonify({"ok": models.update_transaction(tx_id, **data)})


@api.delete("/transactions/<int:tx_id>")
def delete_transaction(tx_id: int):
    return jsonify({"ok": models.delete_transaction(tx_id)})


# ---------- 统计 / 日历 ----------

@api.get("/stats/trend")
def stats_trend():
    return jsonify(stats_mod.trend(
        period=request.args.get("period", "week"),
        cat=request.args.get("cat", "expense"),
        end=request.args.get("end"),
    ))


@api.get("/stats/category")
def stats_category():
    return jsonify(stats_mod.category_share(
        month=request.args.get("month", "") or None,
        cat=request.args.get("cat", "expense"),
    ))


@api.get("/calendar")
def api_calendar():
    return jsonify(stats_mod.daily_calendar(request.args.get("month", "") or None))


# ---------- 搜索 ----------

@api.get("/search")
def api_search():
    return jsonify(models.search_transactions(
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
    return jsonify({"ok": True, "parsed": len(records), "added": added, "skipped": skipped})


# ---------- 报告（复用现有） ----------

@api.get("/report")
def api_report():
    from ..analyzer.report import monthly_report
    return jsonify(monthly_report(request.args.get("month", "") or None))
