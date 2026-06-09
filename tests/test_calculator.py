"""测试共享计算器模块。"""
import pytest
import os
import json

from src.data.scenario import ScenarioConfig, ScenarioManager
from src.data.config import ConfigLoader
from src.core.calculator import calculate
from src.models.dispatch import DispatchResult, ESSParams


class TestCalculator:
    """测试 calculator.calculate() 正常返回。"""

    @pytest.mark.parametrize("bm", ["B1", "B2a", "B2b", "B2c", "B3a", "B3b", "B4"])
    @pytest.mark.parametrize("pm", ["M1", "M2", "M3", "M4", "M4-contract", "M5"])
    def test_calculate_returns_dispatch_result(self, bm, pm):
        config = ScenarioConfig(
            name=f"test-{bm}-{pm}",
            region="henan",
            business_model=bm,
            pricing_mode=pm,
            selected_date="2026-03-15",
        )
        result = calculate(config)
        assert isinstance(result, DispatchResult)
        assert len(result.load_ESS) == 24
        assert len(result.SOC) == 24
        assert len(result.load_grid) == 24

    def test_calculate_honors_disabled_ess(self):
        config = ScenarioConfig(
            name="no-ess",
            region="henan",
            business_model="B1",
            pricing_mode="M1",
            selected_date="2026-03-15",
            system={"net_load": True, "ess": False, "pv": False},
        )
        result = calculate(config)
        assert sum(abs(v) for v in result.load_ESS) == 0
        assert result.equivalent_cycles == 0
        assert result.irr == 0

    def test_calculate_honors_enabled_pv_and_load_profile(self):
        config = ScenarioConfig(
            name="pv-load-profile",
            region="henan",
            business_model="B1",
            pricing_mode="M1",
            selected_date="2026-03-15",
            system={"net_load": True, "ess": True, "pv": True},
            pv_params={"cap_rated": 500},
            run_curves={"load_profile": "steady_24h", "pv_region": "henan", "pv_curve_type": "sunny"},
        )
        result = calculate(config)
        assert result.pv_cap_kw == 500
        assert sum(result.pv_generation) > 0
        assert len(result.load_real) == 24

    def test_calculate_honors_spot_curve_id(self, monkeypatch):
        from src.data.simple_day_catalog import SimpleDayCatalog

        def fake_spot_curve(self, curve_id):
            assert curve_id == "Test:spot"
            return [0.10 + h * 0.001 for h in range(24)], [0.20 + h * 0.001 for h in range(24)]

        monkeypatch.setattr(SimpleDayCatalog, "load_spot_curve", fake_spot_curve)
        config = ScenarioConfig(
            name="spot-curve-id",
            region="henan",
            business_model="B1",
            pricing_mode="M4",
            selected_date="2026-03-15",
            run_curves={"spot_curve_id": "Test:spot"},
        )

        result = calculate(config)

        assert result.P_da_curve[0] == pytest.approx(0.10)
        assert result.P_rt_curve[-1] == pytest.approx(0.223)
        assert result.P_user_curve == pytest.approx(result.P_da_curve)
        assert result.simulation_meta["spot_curve_id"] == "Test:spot"

    def test_calculate_honors_pv_curve_id(self, monkeypatch):
        from src.data.simple_day_catalog import SimpleDayCatalog

        def fake_pv_curve(self, curve_id):
            assert curve_id == "Test:pv"
            return [0.5] * 24

        monkeypatch.setattr(SimpleDayCatalog, "load_pv_curve", fake_pv_curve)
        config = ScenarioConfig(
            name="pv-curve-id",
            region="henan",
            business_model="B1",
            pricing_mode="M1",
            selected_date="2026-03-15",
            system={"net_load": True, "ess": True, "pv": True},
            pv_params={"cap_rated": 100},
            run_curves={"pv_curve_id": "Test:pv"},
        )

        result = calculate(config)

        assert result.pv_cap_kw == 100
        assert result.pv_generation == pytest.approx([50.0] * 24)
        assert result.pv_total_gen_daily == pytest.approx(1200.0)
        assert result.simulation_meta["pv_curve_id"] == "Test:pv"

    def test_calculate_b1_m1_reasonable(self):
        config = ScenarioConfig(
            name="test",
            region="henan",
            business_model="B1",
            pricing_mode="M1",
            selected_date="2026-03-15",
        )
        result = calculate(config)
        assert result.user_savings >= 0
        assert 0 < result.equivalent_cycles < 24
        assert result.irr != 0

    def test_all_results_obey_physical_constraints(self):
        params = ConfigLoader.load_ess_defaults("henan")
        for bm in ["B1", "B2a", "B2b", "B2c", "B3a", "B3b", "B4"]:
            config = ScenarioConfig(
                name=f"phys-{bm}",
                region="henan",
                business_model=bm,
                pricing_mode="M1",
                selected_date="2026-03-15",
            )
            result = calculate(config)
            for h in range(24):
                assert abs(result.load_ESS[h]) <= params.max_power + 1e-6, \
                    f"{bm} h={h}: power exceeds max"
                assert result.SOC[h] >= params.soc_min - 1e-6, \
                    f"{bm} h={h}: SOC below min"
                assert result.SOC[h] <= params.soc_max + 1e-6, \
                    f"{bm} h={h}: SOC above max"


class TestFinancialDefaultsSavedAndLoaded:
    """测试财务参数 CSV 的读写。"""

    def setup_method(self):
        self.backup_path = "data/config/financial_defaults_bak.csv"
        self.orig_path = "data/config/financial_defaults.csv"
        if os.path.exists(self.backup_path):
            os.remove(self.backup_path)

    def teardown_method(self):
        if os.path.exists(self.backup_path):
            if os.path.exists(self.orig_path):
                os.remove(self.orig_path)
            os.rename(self.backup_path, self.orig_path)

    def test_load_financial_has_all_keys(self):
        fin = ConfigLoader.load_financial_defaults("henan")
        assert "r_discount" in fin
        assert "r_user_b1" in fin
        assert "r_user_b2" in fin

    def test_load_financial_values_are_numeric(self):
        fin = ConfigLoader.load_financial_defaults("henan")
        for k in ["r_discount", "r_user_b1", "r_user_b2"]:
            float(fin[k])

    def test_save_and_reload_roundtrip(self):
        import shutil
        import uuid
        import pandas as pd
        from pathlib import Path

        new_data = {"r_discount": 0.10, "r_user_b1": 0.25, "r_user_b2": 0.55}
        tmpdir = Path(".test_financial") / uuid.uuid4().hex
        tmpdir.mkdir(parents=True, exist_ok=True)
        try:
            path = tmpdir / "financial_defaults.csv"
            ConfigLoader.save_financial_defaults(new_data, path)
            df = pd.read_csv(path)
            reloaded = {r["param"]: r["value"] for _, r in df.iterrows()}
            assert float(reloaded["r_discount"]) == 0.10
            assert float(reloaded["r_user_b1"]) == 0.25
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
