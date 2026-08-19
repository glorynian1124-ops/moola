#!/usr/bin/env python3
"""Moola CLI 入口：AI 记账 + 个人财务管家。

用法：
    python3 main.py init                # 初始化数据库
    python3 main.py import <csv路径>    # 导入微信账单 CSV
    python3 main.py classify [月份]      # AI 自动分类（未分类的记录）
    python3 main.py report [月份]       # 月度消费报告
    python3 main.py web                 # 启动本地 Web 界面
"""
import argparse
import os
import sys
from pathlib import Path

# 保证从项目根目录运行时能 import app 包
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app import db, models  # noqa: E402
from app.parser.wechat_csv import parse_wechat_csv  # noqa: E402


def cmd_init(_args) -> None:
    db.init_db()
    print(f"✅ 数据库已初始化：{db.DB_PATH}")


def cmd_import(args) -> None:
    path = Path(args.csv)
    if not path.exists():
        print(f"❌ 文件不存在：{path}")
        sys.exit(1)
    print(f"正在解析：{path.name} ...")
    records = parse_wechat_csv(path)
    print(f"解析到 {len(records)} 笔交易，写入数据库 ...")
    added, skipped = models.add_many(records)
    print(f"✅ 新增 {added} 笔，跳过重复 {skipped} 笔")
    print(f"数据库现有 {models.transaction_count()} 笔记录")
    # 解析后提示分类
    if added:
        print("提示：运行 `python3 main.py classify` 进行 AI 自动分类")


def cmd_classify(args) -> None:
    from app.analyzer.classify import classify_unclassified
    month = args.month
    n = classify_unclassified(month=month)
    print(f"✅ 已分类 {n} 笔（未分类的）")


def cmd_report(args) -> None:
    from app.analyzer.report import monthly_report
    month = args.month
    data = monthly_report(month)
    if not data:
        print(f"该月（{month}）没有数据")
        return
    print(f"\n📊 Moola 月度消费报告 — {month}\n")
    print(f"总支出：¥{data['total_expense']:,.2f}   总收入：¥{data['total_income']:,.2f}")
    print(f"净支出：¥{data['net']:,.2f}\n")
    print("消费结构：")
    for cat, amount in sorted(data["by_category"].items(), key=lambda x: -x[1]):
        pct = amount / data["total_expense"] * 100 if data["total_expense"] else 0
        print(f"  {cat:<6} ¥{amount:>10,.2f}  {pct:>5.1f}%")
    if data["anomalies"]:
        print("\n⚠️ 异常提醒：")
        for a in data["anomalies"]:
            print(f"  - {a}")


def cmd_web(args) -> None:
    from app.web.app import create_app
    app = create_app()
    host = args.host
    port = args.port
    print(f"🌐 Moola Web 已启动：http://{host}:{port}")
    print("   手机连同一 WiFi 后，用电脑 IP 访问（如 http://192.168.x.x:5001）")
    app.run(host=host, port=port, debug=args.debug)


def main() -> None:
    parser = argparse.ArgumentParser(description="Moola — AI 记账 + 个人财务管家")
    sub = parser.add_subparsers(dest="cmd")

    p_init = sub.add_parser("init", help="初始化数据库")
    p_init.set_defaults(fn=cmd_init)

    p_import = sub.add_parser("import", help="导入微信账单 CSV")
    p_import.add_argument("csv", help="CSV 文件路径")
    p_import.set_defaults(fn=cmd_import)

    p_classify = sub.add_parser("classify", help="AI 自动分类")
    p_classify.add_argument("month", nargs="?", default=None, help="月份 YYYY-MM（默认全部未分类）")
    p_classify.set_defaults(fn=cmd_classify)

    p_report = sub.add_parser("report", help="月度消费报告")
    p_report.add_argument("month", nargs="?", default=None, help="月份 YYYY-MM（默认最近有数据的月份）")
    p_report.set_defaults(fn=cmd_report)

    p_web = sub.add_parser("web", help="启动本地 Web")
    p_web.add_argument("--host", default="0.0.0.0")
    p_web.add_argument("--port", type=int, default=5001)
    p_web.add_argument("--debug", action="store_true")
    p_web.set_defaults(fn=cmd_web)

    args = parser.parse_args()
    if not getattr(args, "cmd", None):
        parser.print_help()
        sys.exit(0)
    args.fn(args)


if __name__ == "__main__":
    main()
