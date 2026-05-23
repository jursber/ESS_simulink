"""pricing 模块测试。"""
import sys
sys.path.insert(0, '.')

import pandas as pd
import pytest
from src.models.dispatch import PricingMode
from src.core.pricing import compute_user_price, lookup_tou


# ---- fixtures ----

@pytest.fixture
def admin_tariff():
    return pd.DataFrame({
        'period': ['valley', 'flat', 'peak', 'flat', 'peak'],
        'start_hour': [0, 12, 8, 21, 17],
        'end_hour': [8, 17, 12, 24, 21],
        'price_yuan_per_kwh': [0.28, 0.58, 0.95, 0.58, 0.95],
        'label': ['谷段', '平段', '峰段', '平段', '峰段'],
    })


@pytest.fixture
def contract_tariff():
    return pd.DataFrame({
        'period': ['valley', 'flat', 'peak', 'flat', 'peak', 'flat'],
        'start_hour': [0, 7, 9, 11, 17, 21],
        'end_hour': [7, 9, 11, 17, 21, 24],
        'price_yuan_per_kwh': [0.30, 0.60, 1.00, 0.60, 1.00, 0.60],
        'label': ['谷段', '平段', '峰段', '平段', '峰段', '平段'],
    })


@pytest.fixture
def jiangsu_config():
    return {
        'p_base': 0.50,
        'coefficient_peak': 1.6,
        'coefficient_flat': 1.0,
        'coefficient_valley': 0.4,
    }


@pytest.fixture
def tariffs(admin_tariff, contract_tariff, jiangsu_config):
    return {
        'admin': admin_tariff,
        'contract': contract_tariff,
        'jiangsu': jiangsu_config,
        'flat_price': 0.55,
    }


@pytest.fixture
def P_da_month():
    """全月 744 小时日前电价 (元/kWh). 模拟第 0..23 小时各有不同均价."""
    import numpy as np
    np.random.seed(42)
    # 每个小时有 31 天的值
    by_hour = {}
    for h in range(24):
        base = 0.32 + 0.02 * ((h + 8) % 24)  # 简单周期
        values = base + 0.02 * np.random.randn(31)
        by_hour[h] = values.tolist()
    # 扁平化为 744 元素列表 (31 天 × 24 小时)
    flat = []
    for d in range(31):
        for h in range(24):
            flat.append(by_hour[h][d])
    return flat


# ---- lookup_tou ----

class TestLookupTOU:
    def test_valley_hour_returns_valley_price(self, admin_tariff):
        assert lookup_tou(admin_tariff, 3) == pytest.approx(0.28)

    def test_peak_hour_returns_peak_price(self, admin_tariff):
        assert lookup_tou(admin_tariff, 10) == pytest.approx(0.95)

    def test_flat_hour_returns_flat_price(self, admin_tariff):
        assert lookup_tou(admin_tariff, 15) == pytest.approx(0.58)

    def test_boundary_hour_0(self, admin_tariff):
        assert lookup_tou(admin_tariff, 0) == pytest.approx(0.28)

    def test_boundary_hour_23(self, admin_tariff):
        assert lookup_tou(admin_tariff, 23) == pytest.approx(0.58)

    def test_contract_tariff(self, contract_tariff):
        assert lookup_tou(contract_tariff, 3) == pytest.approx(0.30)
        assert lookup_tou(contract_tariff, 10) == pytest.approx(1.00)

    def test_missing_hour_raises(self, admin_tariff):
        # 删除部分行制造缺口
        half = admin_tariff.iloc[:2]
        with pytest.raises(ValueError, match="未找到"):
            lookup_tou(half, 23)


# ---- compute_user_price ----

class TestM1AdminTOU:
    def test_returns_24_values(self, tariffs):
        result = compute_user_price(PricingMode.M1_ADMIN_TOU, tariffs, None)
        assert len(result) == 24

    def test_valley_hours(self, tariffs):
        result = compute_user_price(PricingMode.M1_ADMIN_TOU, tariffs, None)
        for h in [0, 1, 7]:
            assert result[h] == pytest.approx(0.28)

    def test_peak_hours(self, tariffs):
        result = compute_user_price(PricingMode.M1_ADMIN_TOU, tariffs, None)
        for h in [8, 10, 18, 20]:
            assert result[h] == pytest.approx(0.95)

    def test_flat_hours(self, tariffs):
        result = compute_user_price(PricingMode.M1_ADMIN_TOU, tariffs, None)
        for h in [12, 15, 22]:
            assert result[h] == pytest.approx(0.58)


class TestM2Jiangsu:
    def test_returns_24_values(self, tariffs):
        result = compute_user_price(PricingMode.M2_JIANGSU, tariffs, None)
        assert len(result) == 24

    def test_valley_coefficient(self, tariffs):
        result = compute_user_price(PricingMode.M2_JIANGSU, tariffs, None)
        # valley: P_base(0.50) × 0.4 = 0.20
        for h in [0, 3, 7]:
            assert result[h] == pytest.approx(0.20)

    def test_peak_coefficient(self, tariffs):
        result = compute_user_price(PricingMode.M2_JIANGSU, tariffs, None)
        # peak: 0.50 × 1.6 = 0.80
        for h in [9, 18]:
            assert result[h] == pytest.approx(0.80)

    def test_flat_coefficient(self, tariffs):
        result = compute_user_price(PricingMode.M2_JIANGSU, tariffs, None)
        # flat: 0.50 × 1.0 = 0.50
        for h in [13, 22]:
            assert result[h] == pytest.approx(0.50)


class TestM3ContractTOU:
    def test_returns_24_values(self, tariffs):
        result = compute_user_price(PricingMode.M3_CONTRACT_TOU, tariffs, None)
        assert len(result) == 24

    def test_valley_price(self, tariffs):
        result = compute_user_price(PricingMode.M3_CONTRACT_TOU, tariffs, None)
        for h in [0, 3, 6]:
            assert result[h] == pytest.approx(0.30)

    def test_peak_price(self, tariffs):
        result = compute_user_price(PricingMode.M3_CONTRACT_TOU, tariffs, None)
        for h in [9, 10, 18]:
            assert result[h] == pytest.approx(1.00)


class TestM4SpotLinked:
    def test_returns_24_values(self, tariffs, P_da_month):
        result = compute_user_price(PricingMode.M4_SPOT_LINKED, tariffs, P_da_month)
        assert len(result) == 24

    def test_each_hour_is_monthly_avg(self, tariffs, P_da_month):
        import numpy as np
        result = compute_user_price(PricingMode.M4_SPOT_LINKED, tariffs, P_da_month)
        # 验证每个 h 的值 = 该小时 31 天的均值
        for h in range(24):
            vals = [P_da_month[d * 24 + h] for d in range(31)]
            assert result[h] == pytest.approx(float(np.mean(vals)))

    def test_no_pda_raises(self, tariffs):
        with pytest.raises(ValueError, match="P_da"):
            compute_user_price(PricingMode.M4_SPOT_LINKED, tariffs, None)


class TestM5Flat:
    def test_returns_24_values(self, tariffs):
        result = compute_user_price(PricingMode.M5_FLAT, tariffs, None)
        assert len(result) == 24

    def test_all_same_price(self, tariffs):
        result = compute_user_price(PricingMode.M5_FLAT, tariffs, None)
        assert all(v == pytest.approx(0.55) for v in result)

    def test_no_flat_price_raises(self):
        with pytest.raises(ValueError, match="flat_price"):
            compute_user_price(PricingMode.M5_FLAT, {}, None)
