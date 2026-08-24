#!/usr/bin/env python3
"""Moola 自动分类触发脚本：实时识别新导入的账目并自动分类。

用法：
    python auto_classify.py               # 一次性：把库里所有未分类刷完
    python auto_classify.py --watch       # 轮询监控，新导入的账单自动分类
    python auto_classify.py --interval 10 # 轮询间隔秒（默认 10）
    python auto_classify.py --month 2026-08  # 只处理指定月份
    python auto_classify.py --report      # 处理完输出分类分布统计

识别策略（猜的成分有兜底）：
    商户名+备注 → ① 规则库命中（category_rules 207条 + config.yaml）→ 直接用
              → ② 未命中 → DeepSeek（flash 版，每日限流保护）
              → ③ 猜不出/无额度 → 保留未分类（等下次）或归「其他支出」
"""
import argparse
import sys
import time
from pathlib import Path

# 保证从项目根目录运行时可 import app
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Windows GBK 控制台兼容
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def _uncat_count() -> int:
    """当前未分类（category 为空）的记录数。"""
    from app.db import get_conn

    conn = get_conn()
    try:
        return conn.execute(
            "SELECT COUNT(*) FROM transactions "
            "WHERE category IS NULL OR category = ''"
        ).fetchone()[0]
    finally:
        conn.close()


def _print_report() -> None:
    """输出当前分类分布（便于查看猜测效果）。"""
    from app.db import get_conn

    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT COALESCE(NULLIF(category, ''), '未分类') AS cat, "
            "COUNT(*) AS n, ROUND(SUM(amount), 2) AS s "
            "FROM transactions GROUP BY cat ORDER BY n DESC"
        ).fetchall()
    finally:
        conn.close()
    print("\n📊 当前分类分布：")
    for cat, n, s in rows:
        print(f"  {cat:<8} {n:>4} 笔  {s:>10,.2f} 元")


def run_once(month=None, report=False) -> int:
    """一次性处理所有未分类记录。"""
    from app.analyzer.classify import classify_unclassified

    pending = _uncat_count()
    if pending == 0:
        print("没有未分类的记录 ✅")
        return 0
    print(f"待分类 {pending} 笔，开始 ...")
    n = classify_unclassified(month=month)
    print(f"本轮处理 {n} 笔，剩余未分类 {_uncat_count()} 笔")
    if report:
        _print_report()
    return n


def watch(interval: int = 10, month=None) -> None:
    """轮询监控：发现未分类即自动处理。"""
    print(f"👀 监控模式：每 {interval}s 扫描一次未分类记录（Ctrl+C 退出）")
    notified = False
    while True:
        pending = _uncat_count()
        if pending:
            print(f"\n发现 {pending} 笔未分类，自动处理 ...")
            run_once(month=month, report=False)
            notified = False
        else:
            if not notified:
                print("当前无未分类，等待新导入 ...")
                notified = True
        time.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Moola 自动分类触发脚本：导入后实时识别并分类"
    )
    parser.add_argument(
        "--watch", action="store_true", help="轮询监控模式（默认一次性）"
    )
    parser.add_argument(
        "--interval", type=int, default=10, help="轮询间隔秒（默认 10）"
    )
    parser.add_argument("--month", default=None, help="只处理指定月份 YYYY-MM")
    parser.add_argument("--report", action="store_true", help="处理后输出分类分布")
    args = parser.parse_args()

    if args.watch:
        watch(args.interval, args.month)
    else:
        run_once(args.month, args.report)


if __name__ == "__main__":
    main()
