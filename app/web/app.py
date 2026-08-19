"""Flask Web 界面（MVP：首页记账 + 统计页）。"""
from datetime import date

from flask import Flask, jsonify, render_template, request

from .. import models
from ..analyzer.report import monthly_report
from ..db import get_conn
from .api import api


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

    @app.after_request
    def add_cors_headers(resp):
        """允许前端原型（8088）跨域调用本 API（5001）。"""
        resp.headers.setdefault("Access-Control-Allow-Origin", "*")
        resp.headers.setdefault("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        resp.headers.setdefault("Access-Control-Allow-Headers", "Content-Type, Authorization")
        return resp

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

    app.register_blueprint(api)

    @app.route("/api/<path:_path>", methods=["OPTIONS"])
    def cors_preflight(_path):
        """跨域预检（OPTIONS）直接放行，交给 after_request 补充 CORS 头。"""
        return ("", 204)

    return app
