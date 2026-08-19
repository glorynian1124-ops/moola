"""微信账单 CSV 解析器。

兼容微信官方导出的账单文件：
- 编码：GBK 或 UTF-8 自动检测
- 表头：「微信支付账单明细」说明行 + 空行 + 表头行 + 数据行 + 统计行
- 字段：交易时间, 交易类型, 交易对方, 商品, 收/支, 金额(元), 支付方式, 当前状态, 交易单号, 商户单号, 备注
"""
import csv
import io
from pathlib import Path
from typing import Optional

# 微信 CSV 的标准表头（不同版本可能有细微差异，按位置解析最稳）
WECHAT_HEADER = "交易时间,交易类型,交易对方,商品,收/支,金额(元),支付方式,当前状态,交易单号,商户单号,备注"


def _decode(path: Path) -> str:
    """读取文件内容，自动处理 GBK / UTF-8（含 BOM）。"""
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "gbk", "utf-8"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"无法识别文件编码：{path}")


def parse_wechat_csv(path: str | Path) -> list[dict]:
    """解析微信账单 CSV，返回标准交易记录列表。

    每条记录：{amount, category, merchant, note, trans_time, source}
    - amount：支出为负，收入为正
    - category：暂为空，由 classify 步骤填充
    - source：csv_wechat
    """
    p = Path(path)
    text = _decode(p)
    reader = csv.reader(io.StringIO(text))

    # 微信账单 CSV 前面有说明行和空行，跳过直到找到表头
    header_idx = None
    rows = list(reader)
    for i, row in enumerate(rows):
        if row and "交易时间" in row[0] and "金额" in "".join(row):
            header_idx = i
            break
    if header_idx is None:
        raise ValueError(f"未找到微信账单表头：{path}")

    header = rows[header_idx]
    # 字段位置（微信标准列顺序）
    idx = {
        "time": 0, "type": 1, "peer": 2, "goods": 3, "inout": 4,
        "amount": 5, "status": 7, "note": 10,
    }
    max_col = max(idx.values())

    records = []
    for row in rows[header_idx + 1:]:
        if len(row) <= max_col or not row[idx["time"]]:
            continue
        # 跳过统计行（如「导出时间」「共N笔」）
        if "共" in row[idx["time"]] or "导出" in row[idx["time"]]:
            continue

        status = row[idx["status"]].strip()
        if status == "已全额退款":
            continue  # 退款不重复记账（原单已记，退款单独记）

        inout = row[idx["inout"]].strip()
        try:
            amount = float(row[idx["amount"]].replace(",", "").strip())
        except ValueError:
            continue
        if inout == "支出":
            amount = -abs(amount)
        elif inout == "收入":
            amount = abs(amount)
        else:
            continue  # 中性交易（如零钱提现）跳过

        merchant = row[idx["peer"]].strip()
        goods = row[idx["goods"]].strip()
        note = row[idx["note"]].strip()
        full_note = "/".join(x for x in (goods, note) if x)

        records.append({
            "amount": amount,
            "category": "",
            "merchant": merchant,
            "note": full_note,
            "trans_time": _norm_time(row[idx["time"]].strip()),
            "source": "csv_wechat",
        })
    return records


def _norm_time(t: str) -> str:
    """'2026-08-01 12:30:45' → 统一 ISO 格式（微信导出即此格式）。"""
    t = t.replace("/", "-")
    return t.strip()


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: python3 -m app.parser.wechat_csv <微信账单.csv>")
        sys.exit(1)
    records = parse_wechat_csv(sys.argv[1])
    print(f"共解析 {len(records)} 笔交易")
    for r in records[:10]:
        print(r)
