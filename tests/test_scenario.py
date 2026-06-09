"""scenario 模块测试。"""
import sys
sys.path.insert(0, '.')

import shutil
import uuid
from pathlib import Path

import pytest

from src.data.scenario import ScenarioManager, ScenarioConfig


@pytest.fixture
def manager():
    tmp = Path(".test_scenarios") / uuid.uuid4().hex
    tmp.mkdir(parents=True, exist_ok=True)
    try:
        mgr = ScenarioManager(storage_dir=tmp)
        yield mgr
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def sample_config():
    return ScenarioConfig(
        name="测试方案",
        region="henan",
        pricing_mode="M1",
        business_model="B1",
        ess_params={"cap_rated": 5000, "power_rated": 0.5, "eta_roundtrip": 0.85,
                     "soc_min": 0.10, "soc_max": 0.90, "unit_cost": 0.9,
                     "r_om": 0.01, "design_life": 10, "r_degrade": 0.025},
        financial_params={"r_discount": 0.06, "r_user": 0.30},
        selected_date="2026-03-15",
        private_overrides={},
        wholesale_overrides={
            "settlement_mode": "GUANGDONG_STYLE",
            "contract_curve_profile": "mock_henan",
            "dayahead_curve_profile": "mock_henan",
        },
    )


class TestScenarioConfig:
    def test_default_id_is_none(self):
        cfg = ScenarioConfig(name="test", region="henan")
        assert cfg.id is None

    def test_created_at_is_set_on_init(self):
        cfg = ScenarioConfig(name="test", region="henan")
        assert cfg.created_at is not None
        assert "T" in cfg.created_at

    def test_to_dict_roundtrip(self, sample_config):
        d = sample_config.to_dict()
        cfg2 = ScenarioConfig.from_dict(d)
        assert cfg2.name == sample_config.name
        assert cfg2.region == sample_config.region
        assert cfg2.pricing_mode == sample_config.pricing_mode
        assert cfg2.business_model == sample_config.business_model
        assert cfg2.ess_params == sample_config.ess_params
        assert cfg2.financial_params == sample_config.financial_params
        assert cfg2.wholesale_overrides == sample_config.wholesale_overrides

    def test_variants_default_to_a(self):
        cfg = ScenarioConfig(name="test", region="henan")
        assert set(cfg.variants) == {"A"}
        assert cfg.variants["A"]["system"]["net_load"] is True
        assert cfg.variants["A"]["system"]["ess"] is True
        assert cfg.variants["A"]["system"]["pv"] is False

    def test_variant_config_applies_saved_variant_and_request_overrides(self):
        cfg = ScenarioConfig(
            name="test",
            region="henan",
            variants={
                "A": {"pricing_mode": "M1", "system": {"net_load": True, "ess": True, "pv": False}},
                "B": {
                    "pricing_mode": "M3",
                    "business_model": "B1",
                    "system": {"net_load": True, "ess": False, "pv": True},
                    "pv_params": {"cap_rated": 500},
                    "run_curves": {"load_profile": "steady_24h"},
                    "wholesale_overrides": {
                        "settlement_mode": "GUANGDONG_STYLE",
                        "contract_curve_profile": "mock_henan",
                        "dayahead_curve_profile": "mock_henan",
                    },
                },
            },
        )

        variant = cfg.variant_config("B", {"system": {"net_load": True, "ess": False, "pv": False}})

        assert variant.pricing_mode == "M3"
        assert variant.system == {"net_load": True, "ess": False, "pv": False}
        assert variant.pv_params == {"cap_rated": 500}
        assert variant.run_curves["load_profile"] == "steady_24h"
        assert variant.wholesale_overrides["contract_curve_profile"] == "mock_henan"


class TestScenarioManagerSaveLoad:
    def test_save_assigns_id(self, manager, sample_config):
        manager.save(sample_config)
        assert sample_config.id is not None
        assert len(sample_config.id) > 10

    def test_save_load_roundtrip(self, manager, sample_config):
        manager.save(sample_config)
        loaded = manager.load(sample_config.id)
        assert loaded.name == sample_config.name
        assert loaded.region == sample_config.region
        assert loaded.business_model == sample_config.business_model
        assert loaded.ess_params == sample_config.ess_params
        assert loaded.financial_params == sample_config.financial_params

    def test_list_all_returns_saved(self, manager, sample_config):
        manager.save(sample_config)
        items = manager.list_all()
        assert len(items) == 1
        assert items[0]['id'] == sample_config.id
        assert items[0]['name'] == sample_config.name

    def test_list_all_returns_multiple(self, manager, sample_config):
        cfg2 = ScenarioConfig(name="方案二", region="henan")
        manager.save(sample_config)
        manager.save(cfg2)
        items = manager.list_all()
        assert len(items) == 2

    def test_load_nonexistent_raises(self, manager):
        with pytest.raises(FileNotFoundError):
            manager.load("nonexistent-id")

    def test_delete_removes_file(self, manager, sample_config):
        manager.save(sample_config)
        manager.delete(sample_config.id)
        items = manager.list_all()
        assert len(items) == 0

    def test_delete_nonexistent_raises(self, manager):
        with pytest.raises(FileNotFoundError):
            manager.delete("nonexistent-id")


class TestCopyParams:
    def test_copy_overrides_target(self, manager, sample_config):
        src = ScenarioConfig(
            name="源方案", region="henan",
            private_overrides={"ess_params.cap_rated": 8000, "ess_params.power_rated": 1.0},
        )
        tgt = ScenarioConfig(
            name="目标方案", region="henan",
            private_overrides={"ess_params.cap_rated": 6000},
        )
        manager.save(src)
        manager.save(tgt)
        manager.copy_params(src.id, tgt.id, ["ess_params.cap_rated"])
        reloaded = manager.load(tgt.id)
        assert reloaded.private_overrides["ess_params.cap_rated"] == 8000
        # 未复制的参数应保持不变
        assert "ess_params.power_rated" not in reloaded.private_overrides

    def test_copy_all_params(self, manager, sample_config):
        src = ScenarioConfig(
            name="源方案", region="henan",
            private_overrides={"a": 1, "b": 2},
        )
        tgt = ScenarioConfig(name="目标方案", region="henan")
        manager.save(src)
        manager.save(tgt)
        manager.copy_params(src.id, tgt.id, None)  # None = 全部
        reloaded = manager.load(tgt.id)
        assert reloaded.private_overrides == {"a": 1, "b": 2}


class TestResolveParams:
    def test_no_overrides_uses_global(self):
        global_ess = {"cap_rated": 5000}
        global_fin = {"r_discount": 0.06, "r_user": 0.30}
        sc = ScenarioConfig(name="test", region="henan",
                            ess_params=None, financial_params=None,
                            private_overrides={})
        ess, fin = sc.resolve_params(global_ess, global_fin)
        assert ess["cap_rated"] == 5000
        assert fin["r_discount"] == 0.06

    def test_override_replaces_value(self):
        global_ess = {"cap_rated": 5000}
        global_fin = {"r_discount": 0.06, "r_user": 0.30}
        sc = ScenarioConfig(name="test", region="henan",
                            ess_params=None, financial_params=None,
                            private_overrides={"ess_params.cap_rated": 8000})
        ess, fin = sc.resolve_params(global_ess, global_fin)
        assert ess["cap_rated"] == 8000

    def test_scenario_private_params_take_priority(self):
        """方案私有参数覆盖全局默认。"""
        global_ess = {"cap_rated": 5000}
        global_fin = {"r_discount": 0.06, "r_user": 0.30}
        sc = ScenarioConfig(name="test", region="henan",
                            ess_params={"cap_rated": 3000, "unit_cost": 1.0},
                            financial_params={"r_user": 0.50},
                            private_overrides={"ess_params.cap_rated": 8000})
        ess, fin = sc.resolve_params(global_ess, global_fin)
        # private_overrides 最高优先级
        assert ess["cap_rated"] == 8000
        # scenario 私有参数覆盖全局
        assert ess["unit_cost"] == 1.0
        assert fin["r_user"] == 0.50
        # 未覆盖的沿用全局
        assert fin["r_discount"] == 0.06
