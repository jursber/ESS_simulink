"""Catalog for simple-day typical curves.

The catalog is a read-only view over local data assets. It keeps UI/API code
away from filesystem details and returns hourly curves in the units expected by
the existing calculation engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from src.data.loader import aggregate_minute_to_hour


DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


@dataclass(frozen=True)
class CurveOption:
    """A selectable simple-day curve option."""

    id: str
    label: str
    category: str
    meta: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "category": self.category,
            "meta": dict(self.meta),
        }


class SimpleDayCatalog:
    """Read-only catalog for simple-day typical curves."""

    def __init__(self, data_dir: Path | None = None) -> None:
        self.data_dir = Path(data_dir) if data_dir else DATA_DIR

    def list_catalog(self) -> dict[str, list[dict[str, Any]]]:
        """Return selectable curve options grouped by product category."""
        return {
            "load": [item.to_dict() for item in self.list_load_profiles()],
            "pv": [item.to_dict() for item in self.list_pv_curves()],
            "spot": [item.to_dict() for item in self.list_spot_curves()],
            "retail": [item.to_dict() for item in self.list_retail_curves()],
            "wholesale": [item.to_dict() for item in self.list_wholesale_profiles()],
        }

    def list_load_profiles(self) -> list[CurveOption]:
        load_dir = self.data_dir / "load"
        if not load_dir.exists():
            return []

        options: list[CurveOption] = []
        for path in sorted(load_dir.glob("*.csv")):
            if path.parent.name == "custom":
                continue
            try:
                columns = pd.read_csv(path, nrows=0, comment="#").columns
            except Exception:
                continue
            if "load_MW" in columns or {"date", "hour", "Load_real"}.issubset(set(columns)):
                meta = {"file": self._rel(path), "source": "load"}
                if "load_MW" in columns:
                    meta["granularity"] = "minute"
                else:
                    meta["granularity"] = "hourly"
                options.append(CurveOption(path.stem, _LOAD_LABELS.get(path.stem, path.stem), "load", meta))
        return options

    def list_pv_curves(self) -> list[CurveOption]:
        catalog_path = self.data_dir / "pv_typical_curves" / "catalog.csv"
        if not catalog_path.exists():
            return []
        try:
            df = pd.read_csv(catalog_path, comment="#", encoding="utf-8-sig")
        except Exception:
            return []

        options: list[CurveOption] = []
        for _, row in df.iterrows():
            curve_id = str(row.get("curve_id") or "").strip()
            file_path = str(row.get("file_path") or "").strip()
            if not curve_id or not file_path:
                continue
            label = _join_label(
                row.get("province"),
                row.get("city"),
                row.get("season_label") or row.get("season"),
                row.get("weather_label") or row.get("weather_type"),
            )
            meta = {
                "province_code": _none_to_empty(row.get("province_code")),
                "city_code": _none_to_empty(row.get("city_code")),
                "season": _none_to_empty(row.get("season")),
                "weather_type": _none_to_empty(row.get("weather_type")),
                "unit": _none_to_empty(row.get("unit")),
                "file": file_path,
            }
            options.append(CurveOption(curve_id, label or curve_id, "pv", meta))
        return options

    def list_spot_curves(self) -> list[CurveOption]:
        catalog_path = self.data_dir / "spot_typical_prices" / "catalog.csv"
        if not catalog_path.exists():
            return []
        try:
            df = pd.read_csv(catalog_path, comment="#", encoding="utf-8-sig")
        except Exception:
            return []

        options: list[CurveOption] = []
        for _, row in df.iterrows():
            curve_id = str(row.get("curve_id") or "").strip()
            file_path = str(row.get("file_path") or "").strip()
            if not curve_id or not file_path:
                continue
            ym = f"{row.get('year', '')}-{str(row.get('month', '')).zfill(2)}"
            label = _join_label(row.get("province_code"), ym, row.get("source_kind"))
            meta = {
                "province_code": _none_to_empty(row.get("province_code")),
                "year": _none_to_empty(row.get("year")),
                "month": str(row.get("month", "")).zfill(2),
                "unit": _none_to_empty(row.get("unit")),
                "trust_level": _none_to_empty(row.get("trust_level")),
                "file": file_path,
            }
            options.append(CurveOption(curve_id, label or curve_id, "spot", meta))
        return options

    def list_retail_curves(self) -> list[CurveOption]:
        tariff_dir = self.data_dir / "tariff"
        if not tariff_dir.exists():
            return []
        return [
            CurveOption("admin", "administrative tariff", "retail", {"mode": "admin"}),
            CurveOption("contract", "contract tariff", "retail", {"mode": "contract"}),
            CurveOption("flat", "flat tariff", "retail", {"mode": "flat"}),
        ]

    def list_wholesale_profiles(self) -> list[CurveOption]:
        base = self.data_dir / "trading_strategy" / "contract_position"
        if not base.exists():
            return []
        options = []
        for path in sorted(base.iterdir()):
            if path.is_dir():
                options.append(CurveOption(path.name, path.name, "wholesale", {"profile": path.name}))
        return options

    def load_load_curve(self, profile_id: str, date: str | None = None) -> list[float]:
        """Return a 24-hour load curve in kWh."""
        path = self.data_dir / "load" / f"{profile_id}.csv"
        if not path.exists():
            raise FileNotFoundError(f"load profile not found: {profile_id}")
        df = pd.read_csv(path, comment="#")
        if "load_MW" in df.columns:
            values = [float(v) for v in df["load_MW"].tolist()]
            if len(values) != 1440:
                raise ValueError(f"load profile {profile_id} must contain 1440 minute points")
            return [v * 1000.0 for v in aggregate_minute_to_hour(values)]
        if {"date", "hour", "Load_real"}.issubset(df.columns):
            day = df.copy()
            if date and "date" in day.columns:
                day = day[day["date"].astype(str) == str(date)]
            day = day.sort_values("hour")
            if len(day) != 24:
                raise ValueError(f"load profile {profile_id} must contain 24 hourly rows")
            return [float(v) for v in day["Load_real"].tolist()]
        raise ValueError(f"load profile {profile_id} has unsupported columns")

    def load_pv_curve(self, curve_id: str) -> list[float]:
        """Return a 24-hour PV curve in kWh/kWp."""
        option = self._find_option(self.list_pv_curves(), curve_id)
        path = self._data_path(str(option.meta.get("file") or ""))
        if not path.exists():
            raise FileNotFoundError(f"pv curve file not found: {curve_id}")
        df = pd.read_csv(path, comment="#")
        if "output_kwh_per_mw" in df.columns:
            values = [float(v) for v in df["output_kwh_per_mw"].tolist()]
            if len(values) != 1440:
                raise ValueError(f"pv curve {curve_id} must contain 1440 minute points")
            return [sum(values[h * 60:(h + 1) * 60]) / 1000.0 for h in range(24)]
        if "capacity_factor" in df.columns:
            values = [float(v) for v in df["capacity_factor"].tolist()]
            if len(values) != 1440:
                raise ValueError(f"pv curve {curve_id} must contain 1440 minute points")
            return aggregate_minute_to_hour(values)
        if "output" in df.columns:
            values = [float(v) for v in df["output"].tolist()]
            if len(values) == 1440:
                return aggregate_minute_to_hour(values)
            if len(values) == 24:
                return values
        if "hour" in df.columns:
            value_col = _first_existing_column(df, ["pv_kwh_per_kw", "capacity_factor", "output"])
            if value_col:
                day = df.sort_values("hour")
                if len(day) == 24:
                    return [float(v) for v in day[value_col].tolist()]
        raise ValueError(f"pv curve {curve_id} has unsupported columns")

    def load_spot_curve(self, curve_id: str) -> tuple[list[float], list[float]]:
        """Return day-ahead and real-time spot price curves in yuan/kWh."""
        option = self._find_option(self.list_spot_curves(), curve_id)
        path = self._data_path(str(option.meta.get("file") or ""))
        if not path.exists():
            raise FileNotFoundError(f"spot curve file not found: {curve_id}")
        df = pd.read_csv(path, comment="#")
        if "hour" in df.columns:
            df = df.sort_values("hour")
        if len(df) != 24:
            raise ValueError(f"spot curve {curve_id} must contain 24 hourly rows")
        da_col = _first_existing_column(df, ["day_ahead_yuan_per_mwh", "day_ahead", "P_da"])
        rt_col = _first_existing_column(df, ["real_time_yuan_per_mwh", "real_time", "P_rt"])
        if not da_col or not rt_col:
            raise ValueError(f"spot curve {curve_id} is missing price columns")
        return (_to_yuan_per_kwh(df[da_col].tolist()), _to_yuan_per_kwh(df[rt_col].tolist()))

    def _find_option(self, options: list[CurveOption], curve_id: str) -> CurveOption:
        for option in options:
            if option.id == curve_id:
                return option
        raise KeyError(f"curve id not found: {curve_id}")

    def _data_path(self, value: str) -> Path:
        path = Path(value)
        if path.is_absolute():
            return path
        if path.parts and path.parts[0] == "data":
            return self.data_dir.joinpath(*path.parts[1:])
        return self.data_dir.parent / path

    def _rel(self, path: Path) -> str:
        try:
            return path.relative_to(self.data_dir.parent).as_posix()
        except ValueError:
            return path.as_posix()


def _first_existing_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for name in candidates:
        if name in df.columns:
            return name
    return None


def _join_label(*parts: Any) -> str:
    return " / ".join(str(p) for p in parts if p is not None and str(p).strip() and str(p) != "nan")


def _none_to_empty(value: Any) -> str:
    if value is None or str(value) == "nan":
        return ""
    return str(value)


def _to_yuan_per_kwh(values: list[Any]) -> list[float]:
    out = [float(v) for v in values]
    if out and max(abs(v) for v in out) > 10:
        return [v / 1000.0 for v in out]
    return out


_LOAD_LABELS = {
    "daily_default": "default day load",
    "steady_24h": "steady 24h load",
    "all_day_production": "all-day production",
    "daytime_single_shift": "daytime single shift",
    "daytime_single_shift_v2": "daytime single shift v2",
    "daytime_multi_peak": "daytime multi-peak",
    "night_single_shift": "night single shift",
    "night_rising": "night rising",
    "continuous_24h": "continuous 24h",
}
