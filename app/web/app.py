"""Flask Web 界面（MVP：首页记账 + 统计页）。"""
from datetime import date

from flask import Flask, jsonify, render_template, request

from .. import models
from ..analyzer.report import monthly_report


def create_app() -> Flask:
    app = Flask(__name__)

    @app.route("/")
    def index():
        """首页：本月消费概览 + 最近账单。"""
        month = date.today().strftime("%Y-%m")
        report = monthly_report(month) or {}
        txs = models.list_transactions(month=month, limit=20)
        return render_template(
            "index.html",
            month=month,
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
