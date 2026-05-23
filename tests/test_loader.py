"""loader 模块测试。"""
import sys
sys.path.insert(0, '.')

import pytest
from src.data.loader import DataLoader


class TestGetAvailableDates:
    def test_returns_list_of_strings(self):
        dates = DataLoader.get_available_dates('henan')
        assert isinstance(dates, list)
        assert len(dates) > 0
        assert all(isinstance(d, str) for d in dates)

    def test_includes_known_date(self):
        dates = DataLoader.get_available_dates('henan')
        assert '2026-03-15' in dates

    def test_returns_empty_for_unknown_region(self):
        dates = DataLoader.get_available_dates('nonexistent')
        assert dates == []


class TestLoadSpotPrices:
    def test_returns_two_lists_of_24(self):
        P_da, P_rt = DataLoader.load_spot_prices('henan', '2026-03-15')
        assert len(P_da) == 24
        assert len(P_rt) == 24

    def test_values_are_in_yuan_per_kwh(self):
        P_da, P_rt = DataLoader.load_spot_prices('henan', '2026-03-15')
        # 源数据 ~0-580 元/MWh, 除1000后应在 0~0.6 元/kWh 范围
        for v in P_da:
            assert 0.0 <= v <= 1.0, f"P_da={v} 超出预期范围"
        for v in P_rt:
            assert 0.0 <= v <= 1.0, f"P_rt={v} 超出预期范围"

    def test_invalid_date_raises(self):
        with pytest.raises(ValueError, match="未找到"):
            DataLoader.load_spot_prices('henan', '2099-01-01')


class TestLoadProcessedLoad:
    def test_returns_list_of_hourlydata(self):
        from src.models.dispatch import HourlyData
        result = DataLoader.load_processed_load(
            'henan', '2026-03-15',
            P_da=[0.3]*24, P_rt=[0.35]*24,
            Q_contract=[200]*24, P_contract=[0.35]*24,
            Q_dayahead=[400]*24,
        )
        assert len(result) == 24
        assert all(isinstance(h, HourlyData) for h in result)

    def test_hours_are_0_to_23(self):
        from src.models.dispatch import HourlyData
        result = DataLoader.load_processed_load(
            'henan', '2026-03-15',
            P_da=[0.3]*24, P_rt=[0.35]*24,
            Q_contract=[200]*24, P_contract=[0.35]*24,
            Q_dayahead=[400]*24,
        )
        hours = [h.hour for h in result]
        assert hours == list(range(24))

    def test_load_real_is_positive(self):
        from src.models.dispatch import HourlyData
        result = DataLoader.load_processed_load(
            'henan', '2026-03-15',
            P_da=[0.3]*24, P_rt=[0.35]*24,
            Q_contract=[200]*24, P_contract=[0.35]*24,
            Q_dayahead=[400]*24,
        )
        for h in result:
            assert h.load_real > 0, f"hour {h.hour}: load_real 应 > 0"

    def test_invalid_date_raises(self):
        with pytest.raises(ValueError, match="未找到"):
            DataLoader.load_processed_load(
                'henan', '2099-01-01',
                P_da=[0.3]*24, P_rt=[0.35]*24,
                Q_contract=[200]*24, P_contract=[0.35]*24,
                Q_dayahead=[400]*24,
            )


class TestLoadProcessedLoadRaisesOnMismatchedArrays:
    def test_short_pda_raises(self):
        with pytest.raises(ValueError, match="24"):
            DataLoader.load_processed_load(
                'henan', '2026-03-15',
                P_da=[0.3]*10, P_rt=[0.35]*24,
                Q_contract=[200]*24, P_contract=[0.35]*24,
                Q_dayahead=[400]*24,
            )
