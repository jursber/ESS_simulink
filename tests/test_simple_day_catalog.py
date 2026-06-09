"""Tests for the simple-day typical curve catalog."""

import shutil
from pathlib import Path

import pandas as pd
import pytest

from src.data.simple_day_catalog import SimpleDayCatalog


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")


def _test_data_dir(name: str) -> Path:
    path = Path(".test_simple_day_catalog") / name
    shutil.rmtree(path, ignore_errors=True)
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_catalog_returns_empty_groups_when_optional_assets_are_missing():
    tmp_path = _test_data_dir("missing")
    try:
        catalog = SimpleDayCatalog(tmp_path)

        data = catalog.list_catalog()

        assert set(data) == {"load", "pv", "spot", "retail", "wholesale"}
        assert data["load"] == []
        assert data["pv"] == []
        assert data["spot"] == []
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_catalog_lists_load_pv_spot_and_reads_24_hour_curves():
    tmp_path = _test_data_dir("normal")
    try:
        _write_csv(
            tmp_path / "load" / "steady.csv",
            [{"minute": i, "load_MW": 2.0} for i in range(1440)],
        )
        _write_csv(
            tmp_path / "pv_typical_curves" / "catalog.csv",
            [{
                "province": "测试省",
                "province_code": "Test",
                "city": "测试市",
                "city_code": "test_city",
                "season": "annual",
                "season_label": "全年",
                "weather_type": "sunny",
                "weather_label": "晴天",
                "curve_id": "Test:test_city:annual:sunny",
                "file_path": "data/pv_typical_curves/Test/test_city/pv.csv",
                "unit": "kWh_per_1MW_per_minute",
            }],
        )
        _write_csv(
            tmp_path / "pv_typical_curves" / "Test" / "test_city" / "pv.csv",
            [{"minute": i, "output_kwh_per_mw": 1.0} for i in range(1440)],
        )
        _write_csv(
            tmp_path / "spot_typical_prices" / "catalog.csv",
            [{
                "province_code": "Test",
                "year": "2026",
                "month": "06",
                "curve_id": "Test:2026-06:spot_price",
                "file_path": "data/spot_typical_prices/Test/spot.csv",
                "unit": "yuan_per_mwh",
                "source_kind": "hourly_detail",
                "trust_level": "high",
            }],
        )
        _write_csv(
            tmp_path / "spot_typical_prices" / "Test" / "spot.csv",
            [
                {
                    "hour": h,
                    "day_ahead_yuan_per_mwh": 100 + h,
                    "real_time_yuan_per_mwh": 200 + h,
                }
                for h in range(24)
            ],
        )

        catalog = SimpleDayCatalog(tmp_path)
        groups = catalog.list_catalog()

        assert groups["load"][0]["id"] == "steady"
        assert groups["pv"][0]["id"] == "Test:test_city:annual:sunny"
        assert groups["spot"][0]["id"] == "Test:2026-06:spot_price"

        load = catalog.load_load_curve("steady")
        pv = catalog.load_pv_curve("Test:test_city:annual:sunny")
        p_da, p_rt = catalog.load_spot_curve("Test:2026-06:spot_price")

        assert load == pytest.approx([2000.0] * 24)
        assert pv == pytest.approx([0.06] * 24)
        assert p_da[0] == pytest.approx(0.1)
        assert p_rt[-1] == pytest.approx(0.223)
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)
