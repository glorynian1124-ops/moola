"""支付宝账单 CSV 解析器。

兼容支付宝官方导出的账单文件（借鉴小遥账单 + skx6 的解析经验）：
- 编码：GBK（支付宝默认导出为 GBK）
- 表头前有 4 行左右的废行 → 动态找表头（含「交易时间」和「金额」的行）
- 列序不固定 → 按表头名称定位列，兼容不同版本
- 字段大致：交易时间/交易创建时间, 交易分类, 交易对方, 对方账号, 商品说明,
  收/支, 金额, 收/付款方式, 交易状态, 交易订单号, 商家订单号, 备注
"""
import csv
import io
from pathlib import Path


def _decode(path: Path) -> str:
    """读取文件内容，自动处理 GBK / UTF-8（含 BOM）。"""
    raw = path.read_bytes()
    for enc in ("gbk", "utf-8-sig", "utf-8"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"无法识别文件编码：{path}")


def parse_alipay_csv(path: str | Path) -> list[dict]:
    """解析支付宝账单 CSV，返回标准交易记录列表。

    每条记录：{amount, category, merchant, note, trans_time, source, raw_data}
    - amount：支出为负，收入为正
    - category：暂为空，由 classify 步骤填充
    - source：csv_alipay
    """
    p = Path(path)
    text = _decode(p)
    rows = list(csv.reader(io.StringIO(text)))

    header_idx = None
    for i, row in enumerate(rows):
        joined = "".join(row)
        if row and ("交易时间" in joined or "交易创建时间" in joined) and "金额" in joined:
            header_idx = i
            break
    if header_idx is None:
        raise ValueError(f"未找到支付宝账单表头：{path}")

    header = [h.strip() for h in rows[header_idx]]

    def col(*names) -> int | None:
        for n in names:
            for j, h in enumerate(header):
                if h == n:
                    return j
        return None

    idx = {
        "time": col("交易时间", "交易创建时间"),
        "peer": col("交易对方"),
        "goods": col("商品说明", "商品"),
        "inout": col("收/支", "资金流向", "收支"),
        "amount": col("金额", "金额(元)"),
        "status": col("交易状态", "状态"),
        "note": col("备注"),
    }

    def get(row, key: str) -> str:
        j = idx[key]
        if j is None or j >= len(row):
            return ""
        return row[j].strip()

    records = []
    for row in rows[header_idx + 1:]:
        t = get(row, "time")
        if not t:
            continue
        # 跳过统计行（「导出时间」「共N笔」）
        if "共" in t or "导出" in t:
            continue

        inout = get(row, "inout")
        amt_raw = get(row, "amount")
        try:
            amount = float(amt_raw.replace(",", "").replace("¥", "").strip())
        except ValueError:
            continue
        if inout == "支出":
            amount = -abs(amount)
        elif inout == "收入":
            amount = abs(amount)
        else:
            continue  # 中性交易跳过

        goods = get(row, "goods")
        note = get(row, "note")
        full_note = "/".join(x for x in (goods, note) if x)

        records.append({
            "amount": amount,
            "category": "",
            "merchant": get(row, "peer"),
            "note": full_note,
            "trans_time": _norm_time(t),
            "source": "csv_alipay",
            "raw_data": ",".join(row).strip(),
        })
    return records


def _norm_time(t: str) -> str:
    """'2026/07/01 12:30:45' → '2026-07-01 12:30:45'。"""
    return t.replace("/", "-").strip()


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: python3 -m app.parser.alipay_csv <支付宝账单.csv>")
        sys.exit(1)
    records = parse_alipay_csv(sys.argv[1])
    print(f"共解析 {len(records)} 笔交易")
    for r in records[:10]:
        print(r)
