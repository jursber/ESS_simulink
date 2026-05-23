"""config 模块测试。"""
import sys
sys.path.insert(0, '.')

import tempfile
from pathlib import Path

import pytest

from src.data.config import ConfigLoader
from src.models.dispatch import ESSParams


class TestLoadESSDefaults:
    def test_returns_essparams(self):
        params = ConfigLoader.load_ess_defaults("henan")
        assert isinstance(params, ESSParams)

    def test_default_values(self):
        params = ConfigLoader.load_ess_defaults("henan")
        assert params.cap_rated == 5000
        assert params.c_rate == 0.5
        assert params.eta_roundtrip == 0.85
        assert params.soc_min == 0.10
        assert params.soc_max == 0.90
        assert params.unit_cost == 0.9
        assert params.r_om == 0.01
        assert params.design_life == 10
        assert params.r_degrade == 0.025

    def test_computed_properties(self):
        params = ConfigLoader.load_ess_defaults("henan")
        assert params.max_power == 2500.0
        assert abs(params.eta_single - 0.922) < 0.01
        assert params.initial_investment == 4_500_000  # 5000*0.9*1000


class TestLoadTariff:
    def test_admin_returns_dataframe(self):
        df = ConfigLoader.load_tariff("henan", "admin")
        assert hasattr(df, 'columns')
        assert 'price_yuan_per_kwh' in df.columns

    def test_contract_returns_dataframe(self):
        df = ConfigLoader.load_tariff("henan", "contract")
        assert 'price_yuan_per_kwh' in df.columns

    def test_jiangsu_returns_dict(self):
        cfg = ConfigLoader.load_tariff("henan", "jiangsu")
        assert isinstance(cfg, dict)
        assert 'p_base' in cfg
        assert float(cfg['p_base']) == 0.50


class TestLoadContractPosition:
    def test_returns_24_rows_for_scenario_date(self):
        df = ConfigLoader.load_contract_position("henan", "2026-03-15")
        assert len(df) == 24

    def test_has_required_columns(self):
        df = ConfigLoader.load_contract_position("henan", "2026-03-15")
        assert 'q_contract_kwh' in df.columns
        assert 'p_contract_yuan_per_kwh' in df.columns

    def test_unknown_date_raises(self):
        with pytest.raises(ValueError, match="未找到日期"):
            ConfigLoader.load_contract_position("henan", "2099-01-01")


class TestLoadDayaheadPosition:
    def test_returns_24_rows_for_scenario_date(self):
        df = ConfigLoader.load_dayahead_position("henan", "2026-03-15")
        assert len(df) == 24

    def test_has_required_columns(self):
        df = ConfigLoader.load_dayahead_position("henan", "2026-03-15")
        assert 'q_dayahead_kwh' in df.columns

    def test_unknown_date_raises(self):
        with pytest.raises(ValueError, match="未找到日期"):
            ConfigLoader.load_dayahead_position("henan", "2099-01-01")


class TestLoadFinancialDefaults:
    def test_returns_dict(self):
        fin = ConfigLoader.load_financial_defaults("henan")
        assert 'r_discount' in fin
        assert 'r_user_b1' in fin
        assert 'r_user_b2' in fin
        assert 'r_user_b3' in fin

    def test_r_discount_value(self):
        fin = ConfigLoader.load_financial_defaults("henan")
        assert float(fin['r_discount']) == 0.06


class TestSaveESSDefaults:
    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # 加载默认值
            params = ConfigLoader.load_ess_defaults("henan")
            # 修改
            params.cap_rated = 8000
            # 保存到临时目录
            ConfigLoader.save_ess_defaults(params, Path(tmpdir) / "ess_defaults.csv")
            # 重新加载（通过指定路径的方式需要临时支持）
            import pandas as pd
            df = pd.read_csv(Path(tmpdir) / "ess_defaults.csv")
            cap_row = df[df['param'] == 'cap_rated']
            assert float(cap_row['value'].iloc[0]) == 8000
