"""批发购电结算引擎单元测试。"""
import pytest

from src.models.dispatch import HourlyData
from src.models.wholesale import (
    DaQuantityDefinition,
    MarketRegionCode,
    SettlementMode,
    TimeGranularity,
    WholesaleSettlementConfig,
)
from src.core.wholesale_settlement import compute_wholesale_purchase_cost


def _make_hour(
    hour: int,
    q_act: float,
    q_lt: float,
    p_lt: float,
    p_ref: float,
    q_da: float,
    q_clr: float | None,
    p_da: float,
    p_rt: float,
) -> HourlyData:
    return HourlyData(
        hour=hour,
        load_real=q_act,
        P_user=0.0,
        P_da=p_da,
        P_rt=p_rt,
        Q_contract=q_lt,
        P_contract=p_lt,
        Q_dayahead=q_da,
        P_ref=p_ref,
        q_dayahead_cleared=q_clr,
    )


def test_guangdong_style_matches_three_part_sum():
    """广东型：与 Q_LT·P_LT + 日前偏差 + 实时偏差 一致。"""
    hourly = [
        _make_hour(h, 100, 50, 0.3, 0, 60, None, 0.4, 0.5)
        for h in range(24)
    ]
    load = [100.0] * 24
    p_da = [0.4] * 24
    p_rt = [0.5] * 24
    cfg = WholesaleSettlementConfig()
    bd = compute_wholesale_purchase_cost(hourly, load, p_da, p_rt, cfg)
    per = 50 * 0.3 + (60 - 50) * 0.4 + (100 - 60) * 0.5
    assert bd.C_mlt == pytest.approx(24 * (50 * 0.3), rel=0, abs=1e-6)
    assert bd.C_da == pytest.approx(24 * (60 - 50) * 0.4, rel=0, abs=1e-6)
    assert bd.C_rt == pytest.approx(24 * (100 - 60) * 0.5, rel=0, abs=1e-6)
    assert bd.purchase_cost == pytest.approx(24 * per, rel=0, abs=1e-3)


def test_guangxi_style_includes_smooth_and_long_term_diff():
    """广西型：中长期项含 (P_LT + P_DA - P_ref)，并叠加月度调平常数。"""
    hourly = [
        _make_hour(h, 100, 50, 0.3, 0.28, 60, None, 0.4, 0.45)
        for h in range(24)
    ]
    load = [100.0] * 24
    p_da = [0.4] * 24
    p_rt = [0.45] * 24
    cfg = WholesaleSettlementConfig(
        market_region_code=MarketRegionCode.CN,
        settlement_mode=SettlementMode.GUANGXI_STYLE,
        time_granularity=TimeGranularity.H1,
        da_quantity_definition=DaQuantityDefinition.DECLARATION,
        contract_curve_profile="mock_henan",
        dayahead_curve_profile="mock_henan",
        purchase_monthly_constant_yuan=0.0,
        guangxi_month_smooth_yuan=100.0,
        shanxi_wholesale_addon_yuan=0.0,
    )
    bd = compute_wholesale_purchase_cost(hourly, load, p_da, p_rt, cfg)
    c_lt_e = 50 * (0.3 + 0.4 - 0.28)
    c_da = (60 - 50) * 0.4
    c_rt = (100 - 60) * 0.45
    per = c_lt_e + c_da + c_rt
    assert bd.C_mlt == pytest.approx(24 * c_lt_e, rel=0, abs=1e-6)
    assert bd.C_month_smooth == 100.0
    assert bd.purchase_cost == pytest.approx(24 * per + 100.0, rel=0, abs=1e-3)


def test_cleared_quantity_used_when_configured():
    """cleared 口径：日前偏差使用出清电量列。"""
    hourly = [
        _make_hour(h, 80, 40, 0.3, 0, 50, 70.0, 0.4, 0.5)
        for h in range(24)
    ]
    load = [80.0] * 24
    p_da = [0.4] * 24
    p_rt = [0.5] * 24
    cfg = WholesaleSettlementConfig(
        da_quantity_definition=DaQuantityDefinition.CLEARED,
    )
    bd = compute_wholesale_purchase_cost(hourly, load, p_da, p_rt, cfg)
    assert bd.C_da == pytest.approx(24 * (70 - 40) * 0.4, rel=0, abs=1e-6)
    assert bd.C_rt == pytest.approx(24 * (80 - 70) * 0.5, rel=0, abs=1e-6)
