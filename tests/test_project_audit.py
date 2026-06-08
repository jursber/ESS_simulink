"""面向项目目标的审计测试。

这些测试优先覆盖数据质量、计算守恒、API 契约和当前已知埋雷点。
"""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api.main import app
from src.core.calculator import calculate
from src.data.config import ConfigLoader
from src.data.loader import DataLoader
from src.data.scenario import ScenarioConfig
from src.models.dispatch import BusinessModel, PricingMode


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"


def _base_config(**overrides) -> ScenarioConfig:
    data = {
        "name": "audit",
        "region": "henan",
        "business_model": "B1",
        "pricing_mode": "M1",
        "selected_date": "2026-03-15",
    }
    data.update(overrides)
    return ScenarioConfig(**data)


def test_core_demo_day_data_is_complete_and_unit_scaled():
    """示范日核心数据必须能按 24 小时完整加载，现货电价单位为元/kWh。"""
    config = _base_config()
    p_da, p_rt = DataLoader.load_spot_prices(config.region, config.selected_date)
    ct = ConfigLoader.load_contract_position(config.region, config.selected_date)
    da = ConfigLoader.load_dayahead_position(config.region, config.selected_date)

    assert len(p_da) == len(p_rt) == 24
    assert ct["hour"].astype(int).tolist() == list(range(24))
    assert da["hour"].astype(int).tolist() == list(range(24))
    assert all(0 <= p <= 2 for p in p_da + p_rt)
    assert all(math.isfinite(p) for p in p_da + p_rt)


def test_all_administrative_tariff_files_cover_24_hours_and_have_price_column():
    """全国行政分时电价文件应覆盖 0~23 小时，至少一个电压等级价格列有有效值。"""
    tariff_root = DATA_DIR / "tariff" / "administrative_tariff"
    files = list(tariff_root.glob("*/*.csv"))
    assert files, "行政分时电价目录为空"

    bad_files: list[str] = []
    for path in files:
        df = pd.read_csv(path, comment="#", encoding="utf-8-sig")
        price_cols = [c for c in df.columns if c not in ("hour", "时段")]
        hours = sorted(int(h) for h in df["hour"].dropna().unique())
        has_price = bool(price_cols) and df[price_cols].notna().any(axis=None)
        if hours != list(range(24)) or not has_price:
            bad_files.append(path.relative_to(ROOT).as_posix())

    assert bad_files == []


def test_pv_curve_and_load_grid_identity_hold_when_pv_enabled():
    """光伏接入后，电网负荷应等于真实负荷 - 储能出力 - 光伏自用。"""
    result = calculate(_base_config())

    assert len(result.pv_generation) == 24
    assert len(result.pv_self_consumed) == 24
    assert len(result.pv_fed_in) == 24
    assert all(v >= -1e-9 for v in result.pv_generation)
    assert all(v >= -1e-9 for v in result.pv_self_consumed)
    assert all(v >= -1e-9 for v in result.pv_fed_in)
    assert 0 <= result.pv_self_rate <= 1

    p_da, p_rt = DataLoader.load_spot_prices("henan", "2026-03-15")
    ct = ConfigLoader.load_contract_position("henan", "2026-03-15")
    da = ConfigLoader.load_dayahead_position("henan", "2026-03-15")
    hourly = DataLoader.load_processed_load(
        "henan",
        "2026-03-15",
        p_da,
        p_rt,
        [float(ct[ct["hour"] == h]["q_contract_kwh"].iloc[0]) for h in range(24)],
        [float(ct[ct["hour"] == h]["p_contract_yuan_per_kwh"].iloc[0]) for h in range(24)],
        [float(da[da["hour"] == h]["q_dayahead_kwh"].iloc[0]) for h in range(24)],
    )

    for h in range(24):
        expected = hourly[h].load_real - result.load_ESS[h] - result.pv_self_consumed[h]
        assert result.load_grid[h] == pytest.approx(expected, abs=1e-6)
        assert result.pv_fed_in[h] == pytest.approx(
            result.pv_generation[h] - result.pv_self_consumed[h], abs=1e-6
        )


@pytest.mark.parametrize("bm", list(BusinessModel))
@pytest.mark.parametrize("pm", list(PricingMode))
def test_calculation_smoke_matrix_obeys_basic_physical_bounds(bm, pm):
    """5 种电价模式 × 7 种商业模式都应可计算，并遵守基础物理边界。"""
    result = calculate(_base_config(business_model=bm.value, pricing_mode=pm.value))
    ess = ConfigLoader.load_ess_defaults("henan")

    assert len(result.load_ESS) == 24
    assert len(result.SOC) == 24
    assert len(result.load_grid) == 24
    assert max(abs(v) for v in result.load_ESS) <= ess.max_power + 1e-6
    assert min(result.SOC) >= ess.soc_min - 1e-6
    assert max(result.SOC) <= ess.soc_max + 1e-6
    assert result.equivalent_cycles == pytest.approx(
        sum(max(0, v) for v in result.load_ESS) / ess.cap_rated, abs=1e-9
    )


def test_api_options_and_calculate_response_contract():
    """API 必须返回前端依赖的稳定字段和 24 点时序。"""
    client = TestClient(app)
    scenarios = client.get("/api/scenarios")
    assert scenarios.status_code == 200
    scenario_items = scenarios.json()
    assert scenario_items, "至少需要一个示范方案用于 API smoke test"

    options = client.get("/api/options")
    assert options.status_code == 200
    option_data = options.json()
    assert len(option_data["pricing_modes"]) == 5
    assert len(option_data["business_models"]) == 7

    resp = client.post(
        "/api/calculate",
        json={
            "scenario_id": scenario_items[0]["id"],
            "pricing_mode": "M1",
            "business_model": "B1",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    ts = data["time_series"]
    for key in ["hours", "load_ess", "soc", "load_grid", "load_real", "price_user", "pv_power"]:
        assert len(ts[key]) == 24
    assert data["overview"]["ess_cap_mwh"] > 0
    assert data["investment"]["initial_invest_wan"] > 0
    assert isinstance(data["econ_ratings"], list)


def test_workspace_api_contracts_for_new_pages():
    """多方案、方案管理、模型管理、数据资产和文档页依赖的 API 应保持可用。"""
    client = TestClient(app)
    scenarios = client.get("/api/scenarios").json()
    assert len(scenarios) >= 1

    compare_items = [
        {"scenario_id": s["id"], "pricing_mode": "M1", "business_model": "B1"}
        for s in scenarios[:4]
    ]
    compare = client.post("/api/compare", json={"items": compare_items})
    assert compare.status_code == 200, compare.text
    compare_data = compare.json()
    assert len(compare_data["items"]) == len(compare_items)
    assert any(m["key"] == "total_welfare_wan" for m in compare_data["metrics"])

    overflow = client.post("/api/compare", json={"items": compare_items + [compare_items[0]]})
    assert overflow.status_code == 400

    models = client.get("/api/models")
    assert models.status_code == 200
    model_data = models.json()
    assert {c["key"] for c in model_data["categories"]} >= {"dispatch", "pricing", "business"}

    save_model = client.put("/api/models/greedy_window/params", json={"window_hours": 12})
    assert save_model.status_code == 200
    rejected_model = client.put("/api/models/bad.name/params", json={"window_hours": 12})
    assert rejected_model.status_code == 400
    models_after_save = client.get("/api/models").json()
    dispatch_models = next(c for c in models_after_save["categories"] if c["key"] == "dispatch")["models"]
    greedy = next(m for m in dispatch_models if m["id"] == "greedy_window")
    assert greedy["draft_saved"] is True
    assert next(p for p in greedy["params"] if p["key"] == "window_hours")["value"] == 12

    assets = client.get("/api/data-assets")
    assert assets.status_code == 200
    asset_data = assets.json()
    assert {g["key"] for g in asset_data["groups"]} >= {"params", "spot_price", "load", "pv_curves"}
    assert isinstance(asset_data["trust"], list)

    docs = client.get("/api/docs")
    assert docs.status_code == 200
    doc_list = docs.json()["docs"]
    assert doc_list
    detail = client.get(f"/api/docs/{doc_list[0]['id']}")
    assert detail.status_code == 200
    assert "content" in detail.json()


def test_scenario_crud_api_roundtrip():
    """方案管理页的新增、改名、复制、删除流程应闭环。"""
    client = TestClient(app)
    created = client.post("/api/scenarios", json={"name": "audit-api-crud", "pricing_mode": "M3"})
    assert created.status_code == 200, created.text
    sid = created.json()["id"]
    try:
        renamed = client.put(f"/api/scenarios/{sid}", json={"name": "audit-api-crud-renamed"})
        assert renamed.status_code == 200
        detail = client.get(f"/api/scenarios/{sid}")
        assert detail.json()["name"] == "audit-api-crud-renamed"

        copied = client.post(f"/api/scenarios/{sid}/duplicate", json={"name": "audit-api-crud-copy"})
        assert copied.status_code == 200
        copy_id = copied.json()["id"]
        delete_copy = client.delete(f"/api/scenarios/{copy_id}")
        assert delete_copy.status_code == 200
    finally:
        client.delete(f"/api/scenarios/{sid}")


def test_admin_tariff_loader_should_use_requested_region():
    """请求河南行政分时电价时，应返回河南文件中的价格，而不是北京价格。"""
    tariff = ConfigLoader.load_tariff("henan", "admin")
    henan_raw = pd.read_csv(
        DATA_DIR / "tariff" / "administrative_tariff" / "Henan" / "202603_commercial.csv",
        comment="#",
        encoding="utf-8-sig",
    )
    expected_h0 = float(henan_raw.loc[henan_raw["hour"] == 0, "1-10(20)千伏(元/kWh)"].iloc[0])
    actual_h0 = float(tariff.loc[tariff["start_hour"] <= 0, "price_yuan_per_kwh"].iloc[0])
    assert actual_h0 == pytest.approx(expected_h0, abs=1e-9)


def test_scenario_ess_private_override_should_affect_dispatch_power_limit():
    """方案私有储能功率应影响调度上限。"""
    cfg = _base_config(ess_params={"power_rated": 0.1, "cap_rated": 200})
    result = calculate(cfg)
    assert max(abs(v) for v in result.load_ESS) <= 100 + 1e-6


def test_available_dates_should_not_reuse_demo_data_for_unknown_region():
    """未知地区不应返回河南示范日期。"""
    assert DataLoader.get_available_dates("unknown-region") == []


def test_calculate_cache_key_should_include_all_result_affecting_inputs():
    """缓存 key 应包含会影响结果的全部输入维度。"""
    from api.routes import _cache_key, _scenario_fingerprint

    cfg_a = _base_config(ess_params={"power_rated": 0.1})
    cfg_b = _base_config(ess_params={"power_rated": 0.2})
    fp_a = _scenario_fingerprint(cfg_a)
    fp_b = _scenario_fingerprint(cfg_b)
    key_a = _cache_key("s1", "M1", "B1", "GUANGDONG_STYLE", "mock_henan", "mock_henan", fp_a)
    key_b = _cache_key("s1", "M1", "B1", "GUANGDONG_STYLE", "mock_henan", "mock_henan", fp_b)
    assert key_a != key_b
