"""扩展光伏出力曲线：24h → 1440min。

对 data/pv_curves/ 下的 CSV 文件执行三次样条插值。
输出格式：minute,output（1440 行），覆盖原文件。
"""
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.interpolate import CubicSpline

PV_DIR = Path(__file__).resolve().parent.parent / "data" / "pv_curves"

LABELS = {
    "annual_avg": "全年日均",
    "cloudy": "阴天",
    "sunny": "晴天",
}


def expand_curve(hour_values: list[float]) -> list[float]:
    """将 24 个小时值扩展为 1440 个分钟值（三次样条插值）。"""
    y_ext = hour_values + [hour_values[0]]
    hours = np.arange(25)
    cs = CubicSpline(hours, y_ext, bc_type='periodic')
    minutes = np.arange(1440) / 60.0
    result = cs(minutes)
    result = np.maximum(result, 0.0)
    result = np.minimum(result, 1.0)
    return result.tolist()


def process_all():
    for region_dir in sorted(PV_DIR.iterdir()):
        if not region_dir.is_dir() or region_dir.name == "custom":
            continue
        for f in sorted(region_dir.glob("*.csv")):
            df = pd.read_csv(f, comment='#')
            cols = [str(c) for c in df.columns]
            if not all(str(h) in cols for h in range(24)):
                print(f"Skip {f.name}: no 24h columns")
                continue
            hour_values = [float(df.iloc[0][str(h)]) for h in range(24)]
            minute_values = expand_curve(hour_values)
            out = pd.DataFrame({
                "minute": range(1440),
                "output": minute_values,
            })
            out.to_csv(f, index=False)
            label = LABELS.get(f.stem, f.stem)
            print(f"[OK] {region_dir.name}/{label} ({f.name})")


if __name__ == "__main__":
    process_all()
