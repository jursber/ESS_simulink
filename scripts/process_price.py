"""现货电价数据处理脚本。

对 data/raw/spot_price_minute/{region}/ 下的分钟级电价数据：
1. 去重到小时级（每小时内所有分钟的值相同）
2. 0:00~0:59 记为 0 点，以此类推
3. 保存到 data/processed/spot_price/price_{region}.csv
"""

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent


def process_region(region: str) -> None:
    raw_dir = ROOT / "data" / "raw" / "spot_price_minute" / region
    out_dir = ROOT / "data" / "processed" / "spot_price"
    out_dir.mkdir(parents=True, exist_ok=True)

    csv_files = sorted(raw_dir.glob("*.csv"))
    if not csv_files:
        print(f"[警告] {raw_dir} 下没有 CSV 文件")
        return

    print(f"处理 {region} 现货电价数据，共 {len(csv_files)} 个文件...")

    dfs = []
    for f in csv_files:
        df = pd.read_csv(f)
        dfs.append(df)

    combined = pd.concat(dfs, ignore_index=True)

    # 去重到小时级：每个 (date, hour) 取第一行
    hourly = combined.groupby(["date", "hour"], as_index=False).first()

    # 只保留需要的列
    hourly = hourly[["date", "hour", "day_ahead", "real_time"]].copy()
    hourly["source"] = region
    hourly = hourly.sort_values(["date", "hour"]).reset_index(drop=True)

    out_path = out_dir / f"price_{region}.csv"
    hourly.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"  已保存至 {out_path}")
    print(f"  数据形状: {hourly.shape}")
    print(f"  日期范围: {hourly['date'].min()} ~ {hourly['date'].max()}")
    print(f"  day_ahead 范围: {hourly['day_ahead'].min():.2f} ~ {hourly['day_ahead'].max():.2f} 元/MWh")
    print(f"  real_time 范围: {hourly['real_time'].min():.2f} ~ {hourly['real_time'].max():.2f} 元/MWh")


if __name__ == "__main__":
    region = sys.argv[1] if len(sys.argv) > 1 else "henan"
    process_region(region)
