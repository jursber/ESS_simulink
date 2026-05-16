"""负荷数据处理脚本。

对 data/raw/load_raw/{region}/ 下的所有每日 CSV 执行：
1. 计算 Load_real = load - storage
2. 删除 load, storage, soc 列
3. 分钟级 → 小时级（算术平均）
4. 缺失值处理：零星缺失→插值，全天/大半缺失→全月对应小时均值
5. 合并为一张大表，保存到 data/processed/load/load_{region}.csv
"""

import sys
import os
from pathlib import Path

import pandas as pd
import numpy as np

# 项目根目录
ROOT = Path(__file__).resolve().parent.parent


def process_one_day(filepath: str) -> pd.DataFrame:
    """读取单日 CSV，计算 Load_real，聚合到小时级。"""
    df = pd.read_csv(filepath, parse_dates=["time"])

    df["Load_real"] = df["load"] - df["storage"]
    df["date"] = df["time"].dt.date
    df["hour"] = df["time"].dt.hour

    hourly = df.groupby(["date", "hour"], as_index=False)["Load_real"].mean()
    return hourly


def fill_missing(df: pd.DataFrame) -> pd.DataFrame:
    """处理缺失值。

    - 零星缺失（同一日期内缺失 ≤ 6 小时）：线性插值
    - 大面积缺失（同一日期内缺失 > 6 小时）：用全月同一时刻的均值填补
    """
    value_col = "Load_real"
    max_interp_gap = 6

    df = df.sort_values(["date", "hour"]).copy()

    # 构建完整的 (date, hour) 网格
    all_dates = sorted(df["date"].unique())
    hours = list(range(24))
    records = []
    for d in all_dates:
        for h in hours:
            row = df[(df["date"] == d) & (df["hour"] == h)]
            if len(row) == 0:
                records.append({"date": d, "hour": h, value_col: np.nan})
            else:
                records.append({"date": d, "hour": h, value_col: row[value_col].iloc[0]})

    df_full = pd.DataFrame(records)

    # 统计每天缺失小时数
    df_full["_miss"] = df_full[value_col].isna().astype(int)
    daily_missing = df_full.groupby("date")["_miss"].sum()

    # 计算全月各小时均值（仅用完整天）
    complete_dates = [d for d in all_dates if daily_missing.get(d, 24) <= max_interp_gap]
    monthly_mean = (
        df_full[df_full["date"].isin(complete_dates)]
        .groupby("hour")[value_col]
        .mean()
    )

    # 逐日处理
    result_parts = []
    for d in all_dates:
        day_data = df_full[df_full["date"] == d].sort_values("hour").copy()
        n_miss = daily_missing.get(d, 0)

        if n_miss == 0:
            pass  # 无缺失
        elif n_miss <= max_interp_gap:
            # 零星缺失：线性插值 + 边界填充
            day_data[value_col] = day_data[value_col].interpolate(
                method="linear", limit_direction="both"
            )
            day_data[value_col] = day_data[value_col].bfill().ffill()
        else:
            # 大面积缺失：用全月对应小时均值填补
            for h in range(24):
                mask = day_data["hour"] == h
                if day_data.loc[mask, value_col].isna().any():
                    fill_val = monthly_mean.get(h, 0)
                    day_data.loc[mask, value_col] = fill_val

        result_parts.append(day_data)

    result = pd.concat(result_parts, ignore_index=True)
    return result[["date", "hour", value_col]]


def process_region(region: str) -> None:
    raw_dir = ROOT / "data" / "raw" / "load_raw" / region
    out_dir = ROOT / "data" / "processed" / "load"
    out_dir.mkdir(parents=True, exist_ok=True)

    csv_files = sorted(raw_dir.glob("*.csv"))
    if not csv_files:
        print(f"[警告] {raw_dir} 下没有 CSV 文件")
        return

    print(f"处理 {region} 负荷数据，共 {len(csv_files)} 个文件...")

    # Step 1: 逐文件处理并聚合到小时
    hourly_dfs = []
    for f in csv_files:
        hourly = process_one_day(str(f))
        hourly_dfs.append(hourly)

    combined = pd.concat(hourly_dfs, ignore_index=True)

    # Step 2: 缺失值处理
    print(f"  合并前缺失小时数: {combined['Load_real'].isna().sum()}")
    combined = fill_missing(combined)
    print(f"  填补后缺失小时数: {combined['Load_real'].isna().sum()}")

    # Step 3: 保存
    combined["source"] = region
    combined = combined.sort_values(["date", "hour"]).reset_index(drop=True)

    out_path = out_dir / f"load_{region}.csv"
    combined.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"  已保存至 {out_path}")
    print(f"  数据形状: {combined.shape}")
    print(f"  日期范围: {combined['date'].min()} ~ {combined['date'].max()}")


if __name__ == "__main__":
    region = sys.argv[1] if len(sys.argv) > 1 else "henan"
    process_region(region)
