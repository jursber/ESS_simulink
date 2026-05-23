"""售电公司购电成本与 PRD §5.3 公式一致性。"""
import pytest

from src.data.scenario import ScenarioConfig
from src.data.config import ConfigLoader
from src.data.loader import DataLoader
from src.core.calculator import calculate


def test_b2a_purchase_components_sum_to_total():
    config = ScenarioConfig(
        name="pc-sum",
        region="henan",
        business_model="B2a",
        pricing_mode="M1",
        selected_date="2026-03-15",
    )
    result = calculate(config)
    assert result.purchase_cost == pytest.approx(
        result.C_mlt + result.C_da + result.C_rt, rel=0, abs=1e-6
    )


def test_b2a_purchase_matches_prd_manual_sum():
    """C_中长期、C_日前、C_实时 与 §5.3 分项公式手工重算一致。"""
    config = ScenarioConfig(
        name="pc-manual",
        region="henan",
        business_model="B2a",
        pricing_mode="M1",
        selected_date="2026-03-15",
    )
    result = calculate(config)
    P_da, P_rt = DataLoader.load_spot_prices(config.region, config.selected_date)
    ct = ConfigLoader.load_contract_position(config.region, config.selected_date)
    da = ConfigLoader.load_dayahead_position(config.region, config.selected_date)
    Qc = [float(ct[ct["hour"] == h]["q_contract_kwh"].iloc[0]) for h in range(24)]
    Pc = [float(ct[ct["hour"] == h]["p_contract_yuan_per_kwh"].iloc[0]) for h in range(24)]
    Qda = [float(da[da["hour"] == h]["q_dayahead_kwh"].iloc[0]) for h in range(24)]
    C_mlt = sum(Qc[h] * Pc[h] for h in range(24))
    C_da = sum((Qda[h] - Qc[h]) * P_da[h] for h in range(24))
    C_rt = sum((result.load_grid[h] - Qda[h]) * P_rt[h] for h in range(24))
    assert result.C_mlt == pytest.approx(C_mlt, rel=0, abs=1e-6)
    assert result.C_da == pytest.approx(C_da, rel=0, abs=1e-6)
    assert result.C_rt == pytest.approx(C_rt, rel=0, abs=1e-6)


def test_b1_no_wholesale_purchase_lines():
    config = ScenarioConfig(
        name="pc-b1",
        region="henan",
        business_model="B1",
        pricing_mode="M1",
        selected_date="2026-03-15",
    )
    result = calculate(config)
    assert result.purchase_cost == 0.0
    assert result.C_mlt == 0.0
    assert result.C_da == 0.0
    assert result.C_rt == 0.0
