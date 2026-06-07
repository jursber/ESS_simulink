"""扩展负荷曲线：24h → 1440min（每分钟一个点）。

对 data/load/ 下的 16 个典型日负荷曲线 CSV 执行：
1. 三次样条插值（24h → 1440min）
2. 叠加高斯随机噪声（σ 自适应，个别点偏大）
3. 确保非负、保持原始形状

输出格式：minute,load_MW（1440 行），覆盖原文件。
"""
from pathlib import Path
import numpy as np
from scipy.interpolate import CubicSpline

LOAD_DIR = Path(__file__).resolve().parent.parent / "data" / "load"

# 中文名称映射
LABELS = {
    "steady_24h": "全天平稳生产",
    "daytime_single_shift": "白天生产,一班制",
    "daytime_single_shift_v2": "白天生产,一班制(变体)",
    "night_winter": "夜间生产-冬季",
    "night_summer": "夜间生产-夏季",
    "night_single_shift": "夜间生产,一班制",
    "night_uneven": "夜间非均匀生产",
    "night_rising": "夜间增长型生产",
    "all_day_production": "全天候生产",
    "all_day_two_shifts": "全天候生产,两班制",
    "all_day_daytime_high": "全天候生产,白天偏高",
    "continuous_24h": "全天24小时生产",
    "first_half_night": "前半夜生产",
    "second_half_night": "后半夜生产",
    "noon_evening_peak": "午间晚间高峰生产",
    "daytime_multi_peak": "白天生产,多峰制",
}


def expand_profile(hour_values: list[float], seed: int = 42) -> list[float]:
    """将 24 个小时值扩展为 1440 个分钟值。

    Args:
        hour_values: 24 个小时级负荷值 (MW)
        seed: 随机种子（可复现）

    Returns:
        1440 个分钟级负荷值 (MW)
    """
    rng = np.random.default_rng(seed)

    # 三次样条插值（周期性：首尾相接）
    y_ext = hour_values + [hour_values[0]]  # 追加首点使首尾相同
    hours = np.arange(25)
    cs = CubicSpline(hours, y_ext, bc_type='periodic')
    minutes = np.arange(1440) / 60.0
    interpolated = cs(minutes)

    # 计算相邻点差值的统计量，用于自适应噪声
    diffs = np.abs(np.diff(interpolated))
    sigma_base = np.mean(diffs) * 0.15

    # 生成噪声：98% 的点用小噪声，2% 的点用大噪声
    noise = rng.normal(0, sigma_base, 1440)
    outlier_mask = rng.random(1440) < 0.02
    noise[outlier_mask] *= 2.0  # 极个别点偏大

    result = interpolated + noise

    # 确保非负
    result = np.maximum(result, 0.0)

    return result.tolist()


def process_all():
    """处理 load/ 下所有 CSV 文件。"""
    csv_files = sorted(LOAD_DIR.glob("*.csv"))
    if not csv_files:
        print("未找到 CSV 文件")
        return

    for f in csv_files:
        if f.parent.name == "custom":
            continue  # 跳过 custom 目录

        # 读取原文件
        import pandas as pd
        df = pd.read_csv(f)
        if "hour" not in df.columns or "load_MW" not in df.columns:
            print(f"跳过 {f.name}：格式不匹配")
            continue

        hour_values = df["load_MW"].tolist()
        if len(hour_values) != 24:
            print(f"跳过 {f.name}：不是 24 行")
            continue

        # 用文件名 hash 作为种子，保证可复现
        seed = hash(f.stem) % (2**31)
        minute_values = expand_profile(hour_values, seed=seed)

        # 写回（覆盖）
        out_df = pd.DataFrame({
            "minute": range(1440),
            "load_MW": minute_values,
        })
        out_df.to_csv(f, index=False)

        label = LABELS.get(f.stem, f.stem)
        avg_val = np.mean(minute_values)
        max_val = np.max(minute_values)
        print(f"[OK] {label} ({f.name}): avg={avg_val:.4f} MW, max={max_val:.4f} MW")

    print(f"\n处理完成，共 {len(csv_files)} 个文件")


if __name__ == "__main__":
    process_all()
