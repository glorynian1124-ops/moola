"""Flask Web 界面（MVP：首页记账 + 统计页）。"""
from datetime import date

from flask import Flask, jsonify, render_template, request

from .. import models
from ..analyzer.report import monthly_report
from ..db import get_conn


def _available_months() -> list[str]:
    """返回有数据的月份（倒序），并确保包含当前月份，供顶部下拉框使用。"""
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT DISTINCT substr(trans_time, 1, 7) m FROM transactions "
            "WHERE trans_time != '' ORDER BY m DESC"
        ).fetchall()
        months = [r[0] for r in rows]
    finally:
        conn.close()
    current = date.today().strftime("%Y-%m")
    if current not in months:
        months.insert(0, current)
    return months


def create_app() -> Flask:
    app = Flask(__name__)

    @app.route("/")
    def index():
        """首页：月度消费概览 + 最近账单（支持 ?month=YYYY-MM 切换）。"""
        month = request.args.get("month") or date.today().strftime("%Y-%m")
        report = monthly_report(month) or {}
        txs = models.list_transactions(month=month, limit=20)
        return render_template(
            "index.html",
            month=month,
            months=_available_months(),
            report=report,
            transactions=txs,
            categories=models.list_categories(),
        )

    @app.route("/api/transactions")
    def api_transactions():
        month = request.args.get("month", "")
        rows = models.list_transactions(month=month or None, limit=500)
        return jsonify(rows)

    @app.route("/api/report")
    def api_report():
        month = request.args.get("month")
        return jsonify(monthly_report(month))

    @app.route("/api/transactions", methods=["POST"])
    def api_add_transaction():
        data = request.get_json(force=True)
        added = models.add_transaction(
            amount=float(data["amount"]),
            category=data.get("category", "其他支出"),
            merchant=data.get("merchant", ""),
            note=data.get("note", ""),
            trans_time=data.get("trans_time") or date.today().strftime("%Y-%m-%d %H:%M:%S"),
            source="manual",
        )
        return jsonify({"ok": added, "duplicate": not added})

    return app
