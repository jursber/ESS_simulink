import pytest

from src.core.dispatch import optimize_peak_valley_arbitrage, run_dispatch
from src.models.dispatch import (
    BusinessModel,
    ESSParams,
    FinancialParams,
    HourlyData,
    PVParams,
    PricingMode,
)


def _params(**overrides):
    values = {
        "cap_rated": 100.0,
        "power_rated": 0.05,
        "eta_roundtrip": 1.0,
        "soc_min": 0.10,
        "soc_max": 0.90,
    }
    values.update(overrides)
    return ESSParams(**values)


def test_peak_valley_charges_low_and_discharges_high():
    price = [0.2] * 8 + [0.5] * 8 + [1.0] * 8
    load, soc, profit = optimize_peak_valley_arbitrage(
        price,
        _params(),
        load_absorption_limit=[40.0] * 24,
        soc_initial=0.10,
    )

    assert min(load[:8]) < 0
    assert max(load[16:]) > 0
    assert profit > 0
    assert all(-50.0 - 1e-6 <= v <= 40.0 + 1e-6 for v in load)
    assert min(soc) >= 0.10 - 1e-6
    assert max(soc) <= 0.90 + 1e-6


def test_without_pv_storage_never_exports_to_grid():
    price = [0.1] * 12 + [2.0] * 12
    user_load = [15.0] * 24
    load, _, _ = optimize_peak_valley_arbitrage(
        price,
        _params(),
        load_absorption_limit=user_load,
        soc_initial=0.10,
    )

    for h, ess_discharge in enumerate(load):
        assert ess_discharge - user_load[h] <= 1e-6


def test_flat_positive_price_does_not_cycle():
    load, _, profit = optimize_peak_valley_arbitrage(
        [0.5] * 24,
        _params(),
        load_absorption_limit=[100.0] * 24,
        soc_initial=0.10,
    )

    assert sum(abs(v) for v in load) == pytest.approx(0.0, abs=1e-6)
    assert profit == pytest.approx(0.0, abs=1e-6)


def test_small_spread_below_efficiency_loss_does_not_cycle():
    price = [0.50] * 12 + [0.51] * 12
    load, _, profit = optimize_peak_valley_arbitrage(
        price,
        _params(eta_roundtrip=0.64),
        load_absorption_limit=[100.0] * 24,
        soc_initial=0.10,
    )

    assert sum(abs(v) for v in load) == pytest.approx(0.0, abs=1e-6)
    assert profit == pytest.approx(0.0, abs=1e-6)


def test_invalid_or_zero_storage_params_return_empty_dispatch():
    load, soc, profit = optimize_peak_valley_arbitrage(
        [float("nan")] * 24,
        _params(cap_rated=0.0),
        load_absorption_limit=[100.0] * 24,
        soc_initial=0.10,
    )

    assert load == [0.0] * 24
    assert soc == [0.10] * 24
    assert profit == 0.0


def test_with_pv_export_is_allowed_at_feed_in_value():
    price = [-0.1] * 4 + [0.3] * 20
    load, _, profit = optimize_peak_valley_arbitrage(
        price,
        _params(),
        load_absorption_limit=[0.0] * 24,
        export_price=[0.4] * 24,
        soc_initial=0.10,
    )

    assert min(load[:4]) < 0
    assert max(load[4:]) > 0
    assert profit > 0


def _hourly(price):
    return [
        HourlyData(
            hour=h,
            load_real=20.0,
            P_user=price[h],
            P_da=price[h],
            P_rt=price[h],
            Q_contract=20.0,
            P_contract=price[h],
            Q_dayahead=20.0,
        )
        for h in range(24)
    ]


def test_run_dispatch_without_pv_keeps_grid_import_non_negative():
    price = [0.1] * 12 + [2.0] * 12
    result = run_dispatch(
        _hourly(price),
        BusinessModel.B1_USER_ESS,
        PricingMode.M1_ADMIN_TOU,
        _params(),
        FinancialParams(r_user=0.0),
    )

    assert min(result.load_grid) >= -1e-6


def test_run_dispatch_with_pv_values_export_at_feed_in_tariff():
    price = [-0.1] * 4 + [0.3] * 20
    result = run_dispatch(
        _hourly(price),
        BusinessModel.B1_USER_ESS,
        PricingMode.M1_ADMIN_TOU,
        _params(),
        FinancialParams(r_user=0.0),
        pv_params=PVParams(cap_rated=1.0, feed_in_tariff=0.4),
        pv_curve=[0.0] * 24,
    )

    assert min(result.load_grid) < 0
    assert result.user_bill_with_ess < result.user_bill_no_ess
