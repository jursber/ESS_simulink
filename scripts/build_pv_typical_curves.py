"""生成光伏典型日单位出力曲线。

源数据来自桌面清洗后的泛能光伏 15 分钟站点数据。输出到
data/pv_typical_curves/，每条曲线表示 1MW 光伏装机的分钟级发电量。
"""
from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = DATA_DIR / "pv_typical_curves"

SOURCE_DIR = Path(r"C:\Users\Administrator\Desktop\ess数据\fanneng_pv_data_fixed")
MANIFEST_PATH = Path(
    r"C:\Users\Administrator\Documents\Codex\2026-06-08"
    r"\ess-simulink-c-users-administrator-desktop\outputs\fanneng_pv_fixed_manifest.csv"
)

MIN_TYPICAL_SAMPLES = 3
MIN_WEATHER_SAMPLES = 3

PROVINCE_CODES = {
    "北京": "Beijing",
    "天津": "Tianjin",
    "安徽": "Anhui",
    "山东": "Shandong",
    "广东": "Guangdong",
    "广西": "Guangxi",
    "江苏": "Jiangsu",
    "河北": "Hebei_south",
    "冀北": "Hebei_north",
    "河南": "Henan",
    "浙江": "Zhejiang",
    "湖北": "Hubei",
    "湖南": "Hunan",
    "福建": "Fujian",
    "辽宁": "Liaoning",
    "黑龙江": "Heilongjiang",
}

CITY_CODES = {
    "全省": "province_total",
    "未识别": "unknown_city",
    "北京": "beijing",
    "天津": "tianjin",
    "六安": "luan",
    "池州": "chizhou",
    "滁州": "chuzhou",
    "芜湖": "wuhu",
    "东营": "dongying",
    "临沂": "linyi",
    "烟台": "yantai",
    "青岛": "qingdao",
    "东莞": "dongguan",
    "广州": "guangzhou",
    "梅州": "meizhou",
    "江门": "jiangmen",
    "河源": "heyuan",
    "清远": "qingyuan",
    "湛江": "zhanjiang",
    "珠海": "zhuhai",
    "柳州": "liuzhou",
    "贵港": "guigang",
    "钦州": "qinzhou",
    "南通": "nantong",
    "宿迁": "suqian",
    "徐州": "xuzhou",
    "扬州": "yangzhou",
    "淮安": "huaian",
    "盐城": "yancheng",
    "连云港": "lianyungang",
    "唐山": "tangshan",
    "廊坊": "langfang",
    "沧州": "cangzhou",
    "石家庄": "shijiazhuang",
    "信阳": "xinyang",
    "南阳": "nanyang",
    "周口": "zhoukou",
    "商丘": "shangqiu",
    "开封": "kaifeng",
    "新乡": "xinxiang",
    "洛阳": "luoyang",
    "郑州": "zhengzhou",
    "台州": "taizhou",
    "宁波": "ningbo",
    "杭州": "hangzhou",
    "舟山": "zhoushan",
    "衢州": "quzhou",
    "金华": "jinhua",
    "武汉": "wuhan",
    "黄冈": "huanggang",
    "长沙": "changsha",
    "三明": "sanming",
    "宁德": "ningde",
    "泉州": "quanzhou",
    "龙岩": "longyan",
    "大连": "dalian",
    "沈阳": "shenyang",
    "大庆": "daqing",
}

SEASON_LABELS = {
    "annual": "全年",
    "spring": "春季",
    "summer": "夏季",
    "autumn": "秋季",
    "winter": "冬季",
}

WEATHER_LABELS = {
    "typical": "典型日",
    "sunny": "晴天",
    "cloudy": "多云",
    "overcast": "阴天",
    "rainy": "雨天",
}


@dataclass
class DayCurve:
    province: str
    province_code: str
    city: str
    city_code: str
    station_name: str
    system_code: str
    capacity_kw: float
    date: str
    season: str
    cf_15min: np.ndarray
    daily_kwh_per_mw: float
    irradiance_kwh_m2: float
    peak_cf: float
    volatility: float


def slugify_unknown(value: str, prefix: str) -> str:
    cleaned = re.sub(r"[^0-9A-Za-z]+", "_", value).strip("_").lower()
    return cleaned or prefix


def season_of_month(month: int) -> str:
    if month in (3, 4, 5):
        return "spring"
    if month in (6, 7, 8):
        return "summer"
    if month in (9, 10, 11):
        return "autumn"
    return "winter"


def read_manifest() -> pd.DataFrame:
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(f"未找到光伏清单文件: {MANIFEST_PATH}")
    manifest = pd.read_csv(MANIFEST_PATH, encoding="utf-8-sig")
    required = ["省份", "城市_从项目名推断", "项目名称", "系统编码", "容量kW", "修复后文件路径"]
    missing = [col for col in required if col not in manifest.columns]
    if missing:
        raise ValueError(f"光伏清单缺少字段: {missing}")
    return manifest


def load_station_days(row: pd.Series) -> list[DayCurve]:
    province = str(row["省份"]).strip()
    city = str(row.get("城市_从项目名推断", "")).strip()
    if city == "" or city.lower() == "nan":
        city = "未识别"
    province_code = PROVINCE_CODES.get(province, slugify_unknown(province, "province"))
    city_code = CITY_CODES.get(city, slugify_unknown(city, "city"))
    station_name = str(row["项目名称"]).strip()
    system_code = str(row["系统编码"]).strip()
    capacity_kw = float(row["容量kW"])
    path = Path(str(row["修复后文件路径"]).strip())
    if not path.exists() or capacity_kw <= 0:
        return []

    df = pd.read_csv(path, encoding="utf-8-sig")
    required = ["日期", "时间", "15分钟平均功率(kW)", "瞬时辐照度(W/m²)"]
    if any(col not in df.columns for col in required):
        return []
    df = df[required].copy()
    df["日期"] = df["日期"].astype(str)
    df["时间"] = df["时间"].astype(str)
    df["timestamp"] = pd.to_datetime(df["日期"] + " " + df["时间"], errors="coerce")
    df["power_kw"] = pd.to_numeric(df["15分钟平均功率(kW)"], errors="coerce")
    df["irradiance"] = pd.to_numeric(df["瞬时辐照度(W/m²)"], errors="coerce")
    df = df.dropna(subset=["timestamp", "power_kw", "irradiance"])
    df = df.sort_values("timestamp")

    days: list[DayCurve] = []
    for date, day in df.groupby(df["timestamp"].dt.date):
        day = day.sort_values("timestamp")
        if len(day) != 96:
            continue
        power = day["power_kw"].to_numpy(dtype=float)
        irradiance = day["irradiance"].to_numpy(dtype=float)
        if np.isnan(power).any() or np.isnan(irradiance).any():
            continue
        cf = np.clip(power / capacity_kw, 0.0, 1.2)
        daily_kwh_per_mw = float(np.sum(cf) * 250.0)
        peak_cf = float(np.max(cf))
        if daily_kwh_per_mw < 50.0 or peak_cf < 0.02:
            continue
        diff = np.diff(cf)
        volatility = float(np.mean(np.abs(diff)))
        irradiance_kwh_m2 = float(np.sum(np.clip(irradiance, 0.0, None)) * 0.25 / 1000.0)
        date_str = pd.Timestamp(date).strftime("%Y-%m-%d")
        season = season_of_month(pd.Timestamp(date).month)
        days.append(
            DayCurve(
                province=province,
                province_code=province_code,
                city=city,
                city_code=city_code,
                station_name=station_name,
                system_code=system_code,
                capacity_kw=capacity_kw,
                date=date_str,
                season=season,
                cf_15min=cf,
                daily_kwh_per_mw=daily_kwh_per_mw,
                irradiance_kwh_m2=irradiance_kwh_m2,
                peak_cf=peak_cf,
                volatility=volatility,
            )
        )
    return days


def weather_labels_for_group(days: list[DayCurve]) -> dict[int, str]:
    yields = np.array([d.daily_kwh_per_mw for d in days], dtype=float)
    irradiance = np.array([d.irradiance_kwh_m2 for d in days], dtype=float)
    peaks = np.array([d.peak_cf for d in days], dtype=float)
    q75 = float(np.quantile(yields, 0.75))
    q60 = float(np.quantile(yields, 0.60))
    labels: dict[int, str] = {}
    for idx, day in enumerate(days):
        if day.irradiance_kwh_m2 <= 1.5 or day.daily_kwh_per_mw <= 800:
            labels[idx] = "rainy"
        elif day.irradiance_kwh_m2 <= 2.5 or day.daily_kwh_per_mw <= 1600:
            labels[idx] = "overcast"
        elif (
            (day.daily_kwh_per_mw >= max(q75, 3000.0) or day.irradiance_kwh_m2 >= 3.5)
            and day.peak_cf >= 0.50
        ):
            labels[idx] = "sunny"
        elif day.daily_kwh_per_mw >= q60 and peaks[idx] >= 0.35:
            labels[idx] = "cloudy"
        else:
            labels[idx] = "cloudy"
    return labels


def median_representative(days: list[DayCurve]) -> tuple[np.ndarray, DayCurve]:
    curves = np.vstack([d.cf_15min for d in days])
    median_cf = np.median(curves, axis=0)
    distances = np.linalg.norm(curves - median_cf, axis=1)
    representative = days[int(np.argmin(distances))]
    return median_cf, representative


def write_curve(path: Path, cf_15min: np.ndarray) -> float:
    cf_minute = np.repeat(cf_15min, 15)
    output_kwh_per_mw = cf_minute * 1000.0 / 60.0
    power_kw_per_mw = cf_minute * 1000.0
    out = pd.DataFrame(
        {
            "minute": np.arange(1440, dtype=int),
            "output_kwh_per_mw": output_kwh_per_mw,
            "capacity_factor": cf_minute,
            "power_kw_per_mw": power_kw_per_mw,
        }
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(path, index=False, encoding="utf-8-sig")
    return float(output_kwh_per_mw.sum())


def iter_scope_groups(days: list[DayCurve]) -> Iterable[tuple[str, str, str, str, list[DayCurve]]]:
    by_city: dict[tuple[str, str, str, str], list[DayCurve]] = {}
    by_province: dict[tuple[str, str], list[DayCurve]] = {}
    for day in days:
        by_city.setdefault((day.province, day.province_code, day.city, day.city_code), []).append(day)
        by_province.setdefault((day.province, day.province_code), []).append(day)

    for (province, province_code, city, city_code), group in by_city.items():
        yield province, province_code, city, city_code, group
    for (province, province_code), group in by_province.items():
        yield province, province_code, "全省", "province_total", group


def build_catalog(days: list[DayCurve]) -> pd.DataFrame:
    rows: list[dict] = []
    for province, province_code, city, city_code, scope_days in iter_scope_groups(days):
        for season in ["annual", "spring", "summer", "autumn", "winter"]:
            season_days = scope_days if season == "annual" else [d for d in scope_days if d.season == season]
            if len(season_days) < MIN_TYPICAL_SAMPLES:
                continue

            labels = weather_labels_for_group(season_days)
            groups: dict[str, list[DayCurve]] = {"typical": season_days}
            for idx, label in labels.items():
                groups.setdefault(label, []).append(season_days[idx])

            for weather_type, group in sorted(groups.items()):
                min_samples = MIN_TYPICAL_SAMPLES if weather_type == "typical" else MIN_WEATHER_SAMPLES
                if len(group) < min_samples:
                    continue
                median_cf, representative = median_representative(group)
                file_name = f"{city_code}_{season}_{weather_type}.csv"
                rel_path = Path("data") / "pv_typical_curves" / province_code / city_code / file_name
                abs_path = PROJECT_ROOT / rel_path
                daily_kwh_per_mw = write_curve(abs_path, median_cf)
                rows.append(
                    {
                        "province": province,
                        "province_code": province_code,
                        "city": city,
                        "city_code": city_code,
                        "season": season,
                        "season_label": SEASON_LABELS[season],
                        "weather_type": weather_type,
                        "weather_label": WEATHER_LABELS[weather_type],
                        "curve_id": f"{province_code}:{city_code}:{season}:{weather_type}",
                        "file_path": rel_path.as_posix(),
                        "unit": "kWh_per_1MW_per_minute",
                        "daily_kwh_per_mw": round(daily_kwh_per_mw, 6),
                        "sample_records": len(group),
                        "sample_days": len({d.date for d in group}),
                        "source_sites": len({d.system_code for d in group}),
                        "representative_date": representative.date,
                        "representative_station": representative.system_code,
                        "classification_method": "pv_irradiance_proxy_median_curve",
                    }
                )
    return pd.DataFrame(rows)


def main() -> None:
    if not SOURCE_DIR.exists():
        raise FileNotFoundError(f"未找到清洗后的光伏源目录: {SOURCE_DIR}")
    manifest = read_manifest()
    all_days: list[DayCurve] = []
    for _, row in manifest.iterrows():
        all_days.extend(load_station_days(row))
    if not all_days:
        raise RuntimeError("没有可用于生成典型曲线的有效光伏日数据")

    if OUTPUT_DIR.exists():
        if OUTPUT_DIR.name != "pv_typical_curves":
            raise RuntimeError(f"拒绝清理非目标目录: {OUTPUT_DIR}")
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    catalog = build_catalog(all_days)
    catalog_path = OUTPUT_DIR / "catalog.csv"
    catalog.to_csv(catalog_path, index=False, encoding="utf-8-sig")
    summary = {
        "source_dir": str(SOURCE_DIR),
        "manifest_path": str(MANIFEST_PATH),
        "valid_station_days": len(all_days),
        "curve_count": int(len(catalog)),
        "province_count": int(catalog["province_code"].nunique()) if not catalog.empty else 0,
        "city_count": int(catalog[["province_code", "city_code"]].drop_duplicates().shape[0])
        if not catalog.empty
        else 0,
        "unit": "output_kwh_per_mw is per-minute generation for a 1MW PV system",
        "min_typical_samples": MIN_TYPICAL_SAMPLES,
        "min_weather_samples": MIN_WEATHER_SAMPLES,
    }
    (OUTPUT_DIR / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[OK] 有效站点日: {len(all_days)}")
    print(f"[OK] 生成曲线: {len(catalog)}")
    print(f"[OK] 输出目录: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
