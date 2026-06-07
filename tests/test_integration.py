"""端到端集成测试：模拟完整的用户操作流程。"""
import pytest
import os
import json
import tempfile
import shutil

from src.data.scenario import ScenarioManager, ScenarioConfig
from src.data.config import ConfigLoader
from src.data.loader import DataLoader
from src.core.calculator import calculate
from src.core.pricing import compute_user_price
from src.models.dispatch import BusinessModel, PricingMode


class TestFullUserFlow:
    """模拟用户完整操作：创建方案 → 计算 → 查看结果 → 对比 → 参数调整。"""

    def setup_method(self):
        self.mgr = ScenarioManager()
        # Clean up test scenarios
        for item in self.mgr.list_all():
            if item['name'].startswith('e2e-'):
                self.mgr.delete(item['id'])

    def teardown_method(self):
        for item in self.mgr.list_all():
            if item['name'].startswith('e2e-'):
                self.mgr.delete(item['id'])

    def test_create_calculate_compare_flow(self):
        """完整流程：创建 2 个方案 → 计算 → 查看指标。"""
        # 1. 创建方案 A: B1 + M1
        cfg_a = ScenarioConfig(
            name="e2e-方案A",
            region="henan",
            business_model="B1",
            pricing_mode="M1",
            selected_date="2026-03-15",
        )
        sid_a = self.mgr.save(cfg_a)

        # 2. 创建方案 B: B2a + M4
        cfg_b = ScenarioConfig(
            name="e2e-方案B",
            region="henan",
            business_model="B2a",
            pricing_mode="M4",
            selected_date="2026-03-15",
        )
        sid_b = self.mgr.save(cfg_b)

        # 3. 加载并计算
        loaded_a = self.mgr.load(sid_a)
        result_a = calculate(loaded_a)

        loaded_b = self.mgr.load(sid_b)
        result_b = calculate(loaded_b)

        # 4. 验证方案列表
        items = self.mgr.list_all()
        ids = [it['id'] for it in items]
        assert sid_a in ids
        assert sid_b in ids

        # 5. 验证关键指标存在且合理
        assert result_a.irr != float("inf")
        assert result_a.npv != 0
        assert result_a.payback_years > 0
        assert 0 <= result_a.equivalent_cycles <= 24

        assert result_b.irr != float("inf")
        assert result_b.npv != 0

        # 6. 多方案对比验证
        # 不同模型应产生不同结果
        assert result_a.ess_revenue != result_b.ess_revenue or \
               result_a.daily_arbitrage != result_b.daily_arbitrage or \
               result_a.user_savings != result_b.user_savings, \
               "不同方案应产生不同结果"

    def test_params_persistence(self):
        """测试参数保存和加载的持久性。"""
        # 保存到临时文件，避免污染全局参数库。
        from src.models.dispatch import ESSParams
        import pandas as pd
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            ess_path = Path(tmpdir) / "ess_defaults.csv"
            fin_path = Path(tmpdir) / "financial_defaults.csv"
            ess = ESSParams(cap_rated=6000, power_rated=0.6)
            ConfigLoader.save_ess_defaults(ess, ess_path)
            ConfigLoader.save_financial_defaults({
                "r_discount": 0.08, "r_user_b1": 0.35, "r_user_b2": 0.55,
            }, fin_path)

            ess_df = pd.read_csv(ess_path)
            fin_df = pd.read_csv(fin_path)
            ess_values = {r["param"]: r["value"] for _, r in ess_df.iterrows()}
            fin_values = {r["param"]: r["value"] for _, r in fin_df.iterrows()}

            assert float(ess_values["cap_rated"]) == 6000
            assert float(ess_values["power_rated"]) == 0.6
            assert float(fin_values["r_discount"]) == 0.08
            assert float(fin_values["r_user_b1"]) == 0.35

    def test_scenario_resolve_params(self):
        """测试方案的参数覆盖优先级。"""
        cfg = ScenarioConfig(
            name="e2e-参数测试",
            region="henan",
            business_model="B1",
            pricing_mode="M1",
            selected_date="2026-03-15",
            ess_params={"cap_rated": 9999},
            private_overrides={"ess_params.power_rated": 0.99},
        )

        global_ess = {"cap_rated": 5000, "power_rated": 0.5}
        global_fin = {"r_discount": 0.06}

        ess, fin = cfg.resolve_params(global_ess, global_fin)

        assert ess["cap_rated"] == 9999  # 方案私有覆盖全局
        assert ess["power_rated"] == 0.99     # private_overrides 最高优先级

    def test_scenario_edit_flow(self):
        """测试编辑方案流程。"""
        cfg = ScenarioConfig(
            name="e2e-编辑测试",
            region="henan",
            business_model="B1",
            pricing_mode="M1",
            selected_date="2026-03-15",
        )
        sid = self.mgr.save(cfg)

        # 修改
        loaded = self.mgr.load(sid)
        loaded.business_model = "B3a"
        loaded.pricing_mode = "M3"
        self.mgr.save(loaded)

        # 验证
        reloaded = self.mgr.load(sid)
        assert reloaded.business_model == "B3a"
        assert reloaded.pricing_mode == "M3"


class TestAllPricingModesComputeCorrectly:
    """验证 5 种电价模式都能正确计算。"""

    def test_m1_m3_m5_no_da_needed(self):
        """M1/M3/M5 不需要日前价格数据。"""
        tariffs = {
            "admin": ConfigLoader.load_tariff("henan", "admin"),
            "contract": ConfigLoader.load_tariff("henan", "contract"),
        }
        # M1
        p1 = compute_user_price(PricingMode.M1_ADMIN_TOU, {"admin": tariffs["admin"], "flat_price": 0.55})
        assert len(p1) == 24
        # M3
        p3 = compute_user_price(PricingMode.M3_CONTRACT_TOU, {"contract": tariffs["contract"], "flat_price": 0.55})
        assert len(p3) == 24
        # M5
        p5 = compute_user_price(PricingMode.M5_FLAT, {"flat_price": 0.55})
        assert len(p5) == 24
        assert p5[0] == 0.55

    @pytest.mark.xfail(reason="ConfigLoader 尚未提供 jiangsu 配置加载；当前 M2 仅在 pricing.py 中降级处理", strict=True)
    def test_m2_jiangsu_has_peak_valley_ratio(self):
        tariffs = {
            "admin": ConfigLoader.load_tariff("henan", "admin"),
            "jiangsu": ConfigLoader.load_tariff("henan", "jiangsu"),
        }
        p2 = compute_user_price(PricingMode.M2_JIANGSU, tariffs)
        # 峰时段价格应高于谷时段
        valley_h = [h for h in range(24) if 0 <= h < 8]
        peak_h = [h for h in range(24) if 8 <= h < 12 or 17 <= h < 21]
        avg_valley = sum(p2[h] for h in valley_h) / len(valley_h)
        avg_peak = sum(p2[h] for h in peak_h) / len(peak_h)
        assert avg_peak > avg_valley

    def test_m4_uses_monthly_avg(self):
        """M4 月度均价应等于全月日前均价。"""
        all_pda = DataLoader.get_monthly_pda("henan")
        p4 = compute_user_price(PricingMode.M4_SPOT_LINKED, {}, all_pda)
        assert len(p4) == 24
        # 验证月度均价一致性
        n_days = len(all_pda) // 24
        import numpy as np
        expected = np.array(all_pda).reshape(n_days, 24).mean(axis=0)
        for h in range(24):
            assert abs(p4[h] - expected[h]) < 1e-6


class TestDispatchResultConsistency:
    """验证 DispatchResult 内部一致性。"""

    @pytest.mark.parametrize("bm", ["B1", "B2a", "B2b", "B2c", "B3a", "B3b", "B4"])
    def test_load_grid_equals_load_real_minus_load_ess(self, bm):
        config = ScenarioConfig(
            name=f"cons-{bm}",
            region="henan",
            business_model=bm,
            pricing_mode="M1",
            selected_date="2026-03-15",
        )
        result = calculate(config)

        P_da, P_rt = DataLoader.load_spot_prices(config.region, config.selected_date)
        ct = ConfigLoader.load_contract_position(config.region, config.selected_date)
        da = ConfigLoader.load_dayahead_position(config.region, config.selected_date)
        Q_contract = [float(ct[ct["hour"] == h]["q_contract_kwh"].iloc[0]) for h in range(24)]
        P_contract = [float(ct[ct["hour"] == h]["p_contract_yuan_per_kwh"].iloc[0]) for h in range(24)]
        Q_dayahead = [float(da[da["hour"] == h]["q_dayahead_kwh"].iloc[0]) for h in range(24)]

        hourly = DataLoader.load_processed_load(
            config.region, config.selected_date,
            P_da, P_rt, Q_contract, P_contract, Q_dayahead,
        )

        for h in range(24):
            pv_self = result.pv_self_consumed[h] if result.pv_generation else 0.0
            expected_load_grid = hourly[h].load_real - result.load_ESS[h] - pv_self
            assert abs(result.load_grid[h] - expected_load_grid) < 1e-6

    @pytest.mark.parametrize("bm", ["B1", "B2b", "B2c", "B3b"])
    def test_user_side_models_positive_savings(self, bm):
        """用户拥有储能的模式（B1/B2b/B2c/B3b），用户节省应为非负。"""
        config = ScenarioConfig(
            name=f"sav-{bm}",
            region="henan",
            business_model=bm,
            pricing_mode="M1",
            selected_date="2026-03-15",
        )
        result = calculate(config)
        assert result.user_savings >= -1e-9, f"{bm}: user_savings={result.user_savings}"
