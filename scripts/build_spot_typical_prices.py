"""生成现货电价典型月曲线。

输出到 data/spot_typical_prices/，每条曲线表示某省某年月的 24 小时
日前/实时现货电价平均曲线，单位保持为 元/MWh。
"""
from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = DATA_DIR / "spot_typical_prices"

SOURCE_ROOT = Path(r"C:\Users\Administrator\Desktop\ess数据\spot_fixed")
HOURLY_ESS_DIR = SOURCE_ROOT / "spot_hourly_ess"
HOURLY_DIR = SOURCE_ROOT / "spot_hourly"
FIFTEEN_MIN_DIR = SOURCE_ROOT / "spot_15min"
MONTHLY_AVG_DIR = SOURCE_ROOT / "monthly_hourly_avg"
PROJECT_SPOT_PRICE_DIR = DATA_DIR / "spot_price"

MIN_DAYS_PER_MONTH = 1
PRICE_MIN_YUAN_PER_MWH = -1000.0
PRICE_MAX_YUAN_PER_MWH = 3000.0

PROVINCE_CODES = {
    "anhui": "Anhui",
    "beijing": "Beijing",
    "chongqing": "Chongqing",
    "fujian": "Fujian",
    "gansu": "Gansu",
    "guangdong": "Guangdong",
    "guangxi": "Guangxi",
    "guizhou": "Guizhou",
    "hainan": "Hainan",
    "hebei": "Hebei_south",
    "hebei_south": "Hebei_south",
    "hebei_north": "Hebei_north",
    "jibei": "Hebei_north",
    "冀北": "Hebei_north",
    "heilongjiang": "Heilongjiang",
    "henan": "Henan",
    "hubei": "Hubei",
    "hunan": "Hunan",
    "inner_mongolia": "InnerMongolia",
    "innermongolia": "InnerMongolia",
    "jiangsu": "Jiangsu",
    "jiangxi": "Jiangxi",
    "jilin": "Jilin",
    "liaoning": "Liaoning",
    "ningxia": "Ningxia",
    "qinghai": "Qinghai",
    "shaanxi": "Shaanxi",
    "shandong": "Shandong",
    "shanghai": "Shanghai",
    "shanxi": "Shanxi",
    "sichuan": "Sichuan",
    "tianjin": "Tianjin",
    "xinjiang": "Xinjiang",
    "yunnan": "Yunnan",
    "zhejiang": "Zhejiang",
}

CN_PROVINCE_TO_CODE = {
    "安徽省": "Anhui",
    "北京市": "Beijing",
    "重庆市": "Chongqing",
    "福建省": "Fujian",
    "甘肃省": "Gansu",
    "广东省": "Guangdong",
    "广西壮族自治区": "Guangxi",
    "广西省": "Guangxi",
    "贵州省": "Guizhou",
    "海南省": "Hainan",
    "河北省": "Hebei_south",
    "冀北": "Hebei_north",
    "黑龙江省": "Heilongjiang",
    "河南省": "Henan",
    "湖北省": "Hubei",
    "湖南省": "Hunan",
    "内蒙古自治区": "InnerMongolia",
    "江苏省": "Jiangsu",
    "江西省": "Jiangxi",
    "吉林省": "Jilin",
    "辽宁省": "Liaoning",
    "宁夏回族自治区": "Ningxia",
    "青海省": "Qinghai",
    "陕西省": "Shaanxi",
    "山东省": "Shandong",
    "上海市": "Shanghai",
    "山西省": "Shanxi",
    "四川省": "Sichuan",
    "天津市": "Tianjin",
    "新疆维吾尔自治区": "Xinjiang",
    "云南省": "Yunnan",
    "浙江省": "Zhejiang",
}


@dataclass
class SourceStats:
    source_file: str
    source_kind: str
    province_code: str
    month: str
    input_rows: int
    valid_rows: int
    dropped_rows: int
    complete_days: int
    trust_level: str
    notes: str


def normalize_province_code(raw: str) -> str:
    key = str(raw).strip()
    if key in CN_PROVINCE_TO_CODE:
        return CN_PROVINCE_TO_CODE[key]
    lowered = key.lower().replace("-", "_")
    return PROVINCE_CODES.get(lowered, key)


def clean_price_frame(df: pd.DataFrame, source_file: Path, source_kind: str) -> tuple[pd.DataFrame, int]:
    required = ["date", "hour", "day_ahead", "real_time"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"{source_file} 缺少字段: {missing}")
    out = df[required].copy()
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out["hour"] = pd.to_numeric(out["hour"], errors="coerce")
    out["day_ahead"] = pd.to_numeric(out["day_ahead"], errors="coerce")
    out["real_time"] = pd.to_numeric(out["real_time"], errors="coerce")
    before = len(out)
    out = out.dropna(subset=["date", "hour", "day_ahead", "real_time"])
    out = out[(out["hour"] >= 0) & (out["hour"] <= 23)]
    out["hour"] = out["hour"].astype(int)
    for col in ["day_ahead", "real_time"]:
        out = out[(out[col] >= PRICE_MIN_YUAN_PER_MWH) & (out[col] <= PRICE_MAX_YUAN_PER_MWH)]
    out = out.drop_duplicates(subset=["date", "hour"], keep="first")
    if source_kind == "hourly_detail":
        counts = out.groupby("date")["hour"].nunique()
        complete_dates = counts[counts == 24].index
        out = out[out["date"].isin(complete_dates)]
    dropped = before - len(out)
    return out, dropped


def aggregate_hourly_detail(path: Path, province_code: str) -> tuple[pd.DataFrame | None, SourceStats]:
    raw = pd.read_csv(path, encoding="utf-8-sig")
    month = path.stem if len(path.stem) == 6 else ""
    try:
        clean, dropped = clean_price_frame(raw, path, "hourly_detail")
    except ValueError:
        return None, SourceStats(str(path), "hourly_detail", province_code, month, len(raw), 0, len(raw), 0, "reject", "字段不完整")
    if clean.empty:
        return None, SourceStats(str(path), "hourly_detail", province_code, month, len(raw), 0, dropped, 0, "reject", "无完整日前/实时成对小时数据")
    clean["month"] = clean["date"].dt.strftime("%Y-%m")
    month = clean["month"].mode().iloc[0]
    complete_days = int(clean["date"].nunique())
    if complete_days < MIN_DAYS_PER_MONTH:
        return None, SourceStats(str(path), "hourly_detail", province_code, month, len(raw), len(clean), dropped, complete_days, "reject", "完整日数量不足")
    grouped = (
        clean.groupby("hour", as_index=False)[["day_ahead", "real_time"]]
        .mean()
        .sort_values("hour")
    )
    if len(grouped) != 24:
        return None, SourceStats(str(path), "hourly_detail", province_code, month, len(raw), len(clean), dropped, complete_days, "reject", "聚合后不足 24 小时")
    stats = SourceStats(
        source_file=str(path),
        source_kind="hourly_detail",
        province_code=province_code,
        month=month,
        input_rows=len(raw),
        valid_rows=len(clean),
        dropped_rows=dropped,
        complete_days=complete_days,
        trust_level="high",
        notes="逐日逐小时明细平均",
    )
    return grouped, stats


def aggregate_spot_hourly(path: Path, province_code: str) -> tuple[pd.DataFrame | None, SourceStats]:
    raw = pd.read_csv(path, encoding="utf-8-sig")
    try:
        clean, dropped = clean_price_frame(raw, path, "spot_hourly")
    except ValueError:
        return None, SourceStats(str(path), "spot_hourly", province_code, "", len(raw), 0, len(raw), 0, "reject", "字段不完整")
    if clean.empty:
        return None, SourceStats(str(path), "spot_hourly", province_code, "", len(raw), 0, dropped, 0, "reject", "无完整日前/实时成对小时数据")
    clean["month"] = clean["date"].dt.strftime("%Y-%m")
    month = clean["month"].mode().iloc[0]
    complete_days = int(clean["date"].nunique())
    grouped = (
        clean.groupby("hour", as_index=False)[["day_ahead", "real_time"]]
        .mean()
        .sort_values("hour")
    )
    if len(grouped) != 24:
        return None, SourceStats(str(path), "spot_hourly", province_code, month, len(raw), len(clean), dropped, complete_days, "reject", "聚合后不足 24 小时")
    stats = SourceStats(
        source_file=str(path),
        source_kind="spot_hourly",
        province_code=province_code,
        month=month,
        input_rows=len(raw),
        valid_rows=len(clean),
        dropped_rows=dropped,
        complete_days=complete_days,
        trust_level="low",
        notes="电查查逐小时样例，完整成对时才纳入",
    )
    return grouped, stats


def aggregate_spot_15min(path: Path, province_code: str) -> tuple[pd.DataFrame | None, SourceStats]:
    raw = pd.read_csv(path, encoding="utf-8-sig")
    required = ["date", "time", "day_ahead_yuan_per_mwh", "real_time_yuan_per_mwh"]
    missing = [col for col in required if col not in raw.columns]
    if missing:
        return None, SourceStats(str(path), "spot_15min", province_code, "", len(raw), 0, len(raw), 0, "reject", f"缺少字段: {missing}")

    df = raw[required].copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["time"] = df["time"].astype(str)
    df["hour"] = pd.to_numeric(df["time"].str.slice(0, 2), errors="coerce")
    df["day_ahead"] = pd.to_numeric(df["day_ahead_yuan_per_mwh"], errors="coerce")
    df["real_time"] = pd.to_numeric(df["real_time_yuan_per_mwh"], errors="coerce")
    before = len(df)
    df = df.dropna(subset=["date", "hour", "day_ahead", "real_time"])
    df = df[(df["hour"] >= 0) & (df["hour"] <= 23)]
    df["hour"] = df["hour"].astype(int)
    for col in ["day_ahead", "real_time"]:
        df = df[(df[col] >= PRICE_MIN_YUAN_PER_MWH) & (df[col] <= PRICE_MAX_YUAN_PER_MWH)]
    # 15 分钟源必须每小时 4 个成对点才进入小时平均。
    counts = df.groupby(["date", "hour"]).size()
    complete_keys = counts[counts == 4].index
    if len(complete_keys) == 0:
        return None, SourceStats(str(path), "spot_15min", province_code, "", len(raw), 0, before, 0, "reject", "无完整 15 分钟成对小时数据")
    complete_df = df.set_index(["date", "hour"]).loc[complete_keys].reset_index()
    day_counts = complete_df.groupby("date")["hour"].nunique()
    complete_dates = day_counts[day_counts == 24].index
    complete_df = complete_df[complete_df["date"].isin(complete_dates)]
    dropped = before - len(complete_df)
    if complete_df.empty:
        return None, SourceStats(str(path), "spot_15min", province_code, "", len(raw), 0, dropped, 0, "reject", "无完整日前/实时成对日数据")
    complete_df["month"] = complete_df["date"].dt.strftime("%Y-%m")
    month = complete_df["month"].mode().iloc[0]
    complete_days = int(complete_df["date"].nunique())
    grouped = (
        complete_df.groupby("hour", as_index=False)[["day_ahead", "real_time"]]
        .mean()
        .sort_values("hour")
    )
    if len(grouped) != 24:
        return None, SourceStats(str(path), "spot_15min", province_code, month, len(raw), len(complete_df), dropped, complete_days, "reject", "聚合后不足 24 小时")
    stats = SourceStats(
        source_file=str(path),
        source_kind="spot_15min",
        province_code=province_code,
        month=month,
        input_rows=len(raw),
        valid_rows=len(complete_df),
        dropped_rows=dropped,
        complete_days=complete_days,
        trust_level="low",
        notes="15 分钟样例聚合为小时均价，完整成对时才纳入",
    )
    return grouped, stats


def aggregate_monthly_avg(path: Path, province_code: str) -> tuple[pd.DataFrame | None, SourceStats]:
    raw = pd.read_csv(path, encoding="utf-8-sig")
    month = path.stem
    required = ["hour", "day_ahead_avg_yuan_per_mwh", "real_time_avg_yuan_per_mwh"]
    missing = [col for col in required if col not in raw.columns]
    if missing:
        return None, SourceStats(str(path), "monthly_avg", province_code, month, len(raw), 0, len(raw), 0, "reject", f"缺少字段: {missing}")
    df = raw[required].copy()
    df["hour"] = pd.to_numeric(df["hour"], errors="coerce")
    df["day_ahead"] = pd.to_numeric(df["day_ahead_avg_yuan_per_mwh"], errors="coerce")
    df["real_time"] = pd.to_numeric(df["real_time_avg_yuan_per_mwh"], errors="coerce")
    before = len(df)
    df = df.dropna(subset=["hour", "day_ahead", "real_time"])
    df = df[(df["hour"] >= 0) & (df["hour"] <= 23)]
    df["hour"] = df["hour"].astype(int)
    for col in ["day_ahead", "real_time"]:
        df = df[(df[col] >= PRICE_MIN_YUAN_PER_MWH) & (df[col] <= PRICE_MAX_YUAN_PER_MWH)]
    df = df.drop_duplicates(subset=["hour"], keep="first").sort_values("hour")
    dropped = before - len(df)
    if len(df) != 24:
        return None, SourceStats(str(path), "monthly_avg", province_code, month, len(raw), len(df), dropped, 0, "reject", "月均曲线不足 24 小时或存在缺失")
    stats = SourceStats(
        source_file=str(path),
        source_kind="monthly_avg",
        province_code=province_code,
        month=month,
        input_rows=len(raw),
        valid_rows=len(df),
        dropped_rows=dropped,
        complete_days=0,
        trust_level="low",
        notes="已聚合月均样例，仅在无逐日明细时使用",
    )
    return df[["hour", "day_ahead", "real_time"]], stats


def write_curve(province_code: str, year: int, month: int, curve: pd.DataFrame) -> Path:
    file_name = f"{year:04d}_{month:02d}_spot_price.csv"
    rel_path = Path("data") / "spot_typical_prices" / province_code / file_name
    path = PROJECT_ROOT / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    out = pd.DataFrame(
        {
            "hour": curve["hour"].astype(int),
            "day_ahead_yuan_per_mwh": curve["day_ahead"].astype(float).round(6),
            "real_time_yuan_per_mwh": curve["real_time"].astype(float).round(6),
        }
    )
    out.to_csv(path, index=False, encoding="utf-8-sig")
    return rel_path


def collect_curves() -> tuple[list[dict], list[SourceStats]]:
    curves: dict[tuple[str, int, int], tuple[pd.DataFrame, SourceStats]] = {}
    audits: list[SourceStats] = []

    if HOURLY_ESS_DIR.exists():
        for province_dir in sorted(HOURLY_ESS_DIR.iterdir()):
            if not province_dir.is_dir():
                continue
            province_code = normalize_province_code(province_dir.name)
            for path in sorted(province_dir.glob("*.csv")):
                curve, stats = aggregate_hourly_detail(path, province_code)
                audits.append(stats)
                if curve is None or stats.trust_level == "reject":
                    continue
                year, month = [int(v) for v in stats.month.split("-")]
                curves[(province_code, year, month)] = (curve, stats)

    if HOURLY_DIR.exists():
        for province_dir in sorted(HOURLY_DIR.iterdir()):
            if not province_dir.is_dir():
                continue
            province_code = normalize_province_code(province_dir.name)
            for path in sorted(province_dir.glob("*.csv")):
                curve, stats = aggregate_spot_hourly(path, province_code)
                audits.append(stats)
                if curve is None or stats.trust_level == "reject":
                    continue
                year, month = [int(v) for v in stats.month.split("-")]
                curves.setdefault((province_code, year, month), (curve, stats))

    if FIFTEEN_MIN_DIR.exists():
        for province_dir in sorted(FIFTEEN_MIN_DIR.iterdir()):
            if not province_dir.is_dir():
                continue
            province_code = normalize_province_code(province_dir.name)
            for path in sorted(province_dir.glob("*.csv")):
                curve, stats = aggregate_spot_15min(path, province_code)
                audits.append(stats)
                if curve is None or stats.trust_level == "reject":
                    continue
                year, month = [int(v) for v in stats.month.split("-")]
                curves.setdefault((province_code, year, month), (curve, stats))

    if MONTHLY_AVG_DIR.exists():
        for province_dir in sorted(MONTHLY_AVG_DIR.iterdir()):
            if not province_dir.is_dir():
                continue
            province_code = normalize_province_code(province_dir.name)
            for path in sorted(province_dir.glob("*.csv")):
                curve, stats = aggregate_monthly_avg(path, province_code)
                audits.append(stats)
                if curve is None or stats.trust_level == "reject":
                    continue
                year, month = [int(v) for v in stats.month.split("-")]
                curves.setdefault((province_code, year, month), (curve, stats))

    if PROJECT_SPOT_PRICE_DIR.exists():
        for province_dir in sorted(PROJECT_SPOT_PRICE_DIR.iterdir()):
            if not province_dir.is_dir():
                continue
            province_code = normalize_province_code(province_dir.name)
            for path in sorted(province_dir.glob("*.csv")):
                curve, stats = aggregate_hourly_detail(path, province_code)
                stats.source_kind = "project_spot_price"
                stats.trust_level = "low" if stats.trust_level != "reject" else "reject"
                stats.notes = "项目现有现货样例数据"
                audits.append(stats)
                if curve is None or stats.trust_level == "reject":
                    continue
                year, month = [int(v) for v in stats.month.split("-")]
                curves.setdefault((province_code, year, month), (curve, stats))

    rows: list[dict] = []
    for (province_code, year, month), (curve, stats) in sorted(curves.items()):
        rel_path = write_curve(province_code, year, month, curve)
        rows.append(
            {
                "province_code": province_code,
                "year": year,
                "month": f"{month:02d}",
                "curve_id": f"{province_code}:{year:04d}-{month:02d}:spot_price",
                "file_path": rel_path.as_posix(),
                "unit": "yuan_per_mwh",
                "hours": 24,
                "has_day_ahead": True,
                "has_real_time": True,
                "source_kind": stats.source_kind,
                "source_file": stats.source_file,
                "complete_days": stats.complete_days,
                "valid_rows": stats.valid_rows,
                "dropped_rows": stats.dropped_rows,
                "trust_level": stats.trust_level,
                "notes": stats.notes,
                "day_ahead_avg": round(float(np.mean(curve["day_ahead"])), 6),
                "real_time_avg": round(float(np.mean(curve["real_time"])), 6),
                "day_ahead_min": round(float(np.min(curve["day_ahead"])), 6),
                "day_ahead_max": round(float(np.max(curve["day_ahead"])), 6),
                "real_time_min": round(float(np.min(curve["real_time"])), 6),
                "real_time_max": round(float(np.max(curve["real_time"])), 6),
            }
        )
    return rows, audits


def main() -> None:
    if not SOURCE_ROOT.exists():
        raise FileNotFoundError(f"未找到现货源目录: {SOURCE_ROOT}")
    if OUTPUT_DIR.exists():
        if OUTPUT_DIR.name != "spot_typical_prices":
            raise RuntimeError(f"拒绝清理非目标目录: {OUTPUT_DIR}")
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    catalog_rows, audits = collect_curves()
    catalog = pd.DataFrame(catalog_rows)
    audit = pd.DataFrame([s.__dict__ for s in audits])
    catalog.to_csv(OUTPUT_DIR / "catalog.csv", index=False, encoding="utf-8-sig")
    audit.to_csv(OUTPUT_DIR / "audit.csv", index=False, encoding="utf-8-sig")
    summary = {
        "source_root": str(SOURCE_ROOT),
        "curve_count": int(len(catalog)),
        "province_count": int(catalog["province_code"].nunique()) if not catalog.empty else 0,
        "unit": "yuan_per_mwh",
        "price_min_yuan_per_mwh": PRICE_MIN_YUAN_PER_MWH,
        "price_max_yuan_per_mwh": PRICE_MAX_YUAN_PER_MWH,
        "rejected_sources": int((audit["trust_level"] == "reject").sum()) if not audit.empty else 0,
        "high_trust_curves": int((catalog["trust_level"] == "high").sum()) if not catalog.empty else 0,
        "low_trust_curves": int((catalog["trust_level"] == "low").sum()) if not catalog.empty else 0,
    }
    (OUTPUT_DIR / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[OK] 生成现货典型曲线: {len(catalog)}")
    print(f"[OK] 输出目录: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
