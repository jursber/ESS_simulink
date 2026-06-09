"""共享计算器 — 统一的调度计算入口，避免页面间代码重复。"""

from dataclasses import asdict
from typing import Optional

from src.data.scenario import ScenarioConfig
from src.data.loader import DataLoader
from src.data.config import ConfigLoader
from src.core.pricing import compute_user_price
from src.core.dispatch import run_dispatch
from src.models.dispatch import BusinessModel, PricingMode, ESSParams, FinancialParams, PVParams, DispatchResult
from src.models.wholesale import WholesaleSettlementConfig


def _runtime_pricing_mode(value: str) -> PricingMode:
    """Map UI-only pricing options to the closest implemented pricing engine."""
    if value == "M4-contract":
        return PricingMode.M4_SPOT_LINKED
    return PricingMode(value)


def _coerce_ess_params(values: dict) -> dict:
    """Convert scenario/global ESS values into ESSParams constructor types."""
    out = {}
    int_keys = {"design_life", "cycle_life"}
    bool_keys = {"degrade_enabled", "cycle_enabled"}
    valid_keys = set(ESSParams.__dataclass_fields__)
    for key, value in values.items():
        if key not in valid_keys:
            continue
        if key in bool_keys:
            if isinstance(value, str):
                out[key] = value.strip().lower() in {"1", "true", "yes", "y"}
            else:
                out[key] = bool(value)
        elif key in int_keys:
            out[key] = int(float(value))
        else:
            out[key] = float(value)
    return out


def _coerce_pv_params(values: dict) -> dict:
    out = {}
    int_keys = {"design_life"}
    valid_keys = set(PVParams.__dataclass_fields__)
    for key, value in values.items():
        if key not in valid_keys:
            continue
        if key in int_keys:
            out[key] = int(float(value))
        else:
            out[key] = float(value)
    return out


def resolve_runtime_params(config: ScenarioConfig) -> tuple[ESSParams, dict]:
    """Resolve scenario private params against global defaults for runtime use."""
    ess_defaults = asdict(ConfigLoader.load_ess_defaults(config.region))
    fin_defaults = ConfigLoader.load_financial_defaults(config.region)
    ess_values, fin_values = config.resolve_params(ess_defaults, fin_defaults)
    if not (config.system or {}).get("ess", True):
        ess_values["cap_rated"] = 0
        ess_values["power_rated"] = 0
    return ESSParams(**_coerce_ess_params(ess_values)), fin_values


def effective_wholesale_for_scenario(config: ScenarioConfig) -> WholesaleSettlementConfig:
    """合并全局 wholesale CSV、方案快照字段和 `wholesale.*` 私有覆盖。"""
    base = ConfigLoader.load_wholesale_settlement()
    flat = base.to_flat_dict()
    flat.update(config.wholesale_overrides or {})
    ov = config.private_overrides or {}
    numeric = {
        "purchase_monthly_constant_yuan",
        "guangxi_month_smooth_yuan",
        "shanxi_wholesale_addon_yuan",
    }
    for k in flat:
        path = f"wholesale.{k}"
        if path in ov:
            val = ov[path]
            flat[k] = float(val) if k in numeric else val
    return WholesaleSettlementConfig.from_flat_dict(flat)


def calculate(
    config: ScenarioConfig,
    wholesale_cfg: Optional[WholesaleSettlementConfig] = None,
) -> DispatchResult:
    """执行完整调度计算并返回 DispatchResult。

    Args:
        config: 方案配置（电价模式、地区、日期等）。
        wholesale_cfg: 若给定则直接使用；否则按全局 CSV + 方案 `wholesale.*` 覆盖合并。
    """
    region = config.region
    date = config.selected_date

    wholesale_cfg = wholesale_cfg or effective_wholesale_for_scenario(config)

    P_da, P_rt = DataLoader.load_spot_prices(region, date)
    ct = ConfigLoader.load_contract_position(
        region, date, profile=wholesale_cfg.contract_curve_profile
    )
    da = ConfigLoader.load_dayahead_position(
        region, date, profile=wholesale_cfg.dayahead_curve_profile
    )
    Q_contract = [float(ct[ct["hour"] == h]["q_contract_kwh"].iloc[0]) for h in range(24)]
    P_contract = [float(ct[ct["hour"] == h]["p_contract_yuan_per_kwh"].iloc[0]) for h in range(24)]
    P_ref = [float(ct[ct["hour"] == h]["p_ref_yuan_per_kwh"].iloc[0]) for h in range(24)]
    Q_dayahead = [float(da[da["hour"] == h]["q_dayahead_kwh"].iloc[0]) for h in range(24)]
    q_cleared = [float(da[da["hour"] == h]["q_dayahead_cleared_kwh"].iloc[0]) for h in range(24)]

    tariffs = {
        "admin": ConfigLoader.load_tariff(region, "admin"),
        "contract": ConfigLoader.load_tariff(region, "contract"),
        "flat_price": 0.55,
    }
    pricing_mode = _runtime_pricing_mode(config.pricing_mode)
    P_user = compute_user_price(pricing_mode, tariffs,
                                 DataLoader.get_monthly_pda(region))

    hourly = DataLoader.load_processed_load(
        region, date, P_da, P_rt,
        Q_contract, P_contract, Q_dayahead,
        P_ref=P_ref,
        q_dayahead_cleared=q_cleared,
    )
    run_curves = config.run_curves or {}
    profile_name = run_curves.get("load_profile")
    if profile_name and profile_name != "daily_default":
        load_override = DataLoader.load_profile_hourly(
            str(profile_name),
            avg_load_mw=run_curves.get("avg_load"),
            max_load_mw=run_curves.get("max_load"),
        )
        for h, load_value in enumerate(load_override):
            hourly[h].load_real = float(load_value)
    for i, h in enumerate(hourly):
        h.P_user = P_user[i]

    ess_params, fin_defaults = resolve_runtime_params(config)
    r_user_map = {"B1": float(fin_defaults["r_user_b1"]),
                  "B2": float(fin_defaults["r_user_b2"]),
                  "B3": float(fin_defaults.get("r_user_b2", 0.5))}
    bm_code = config.business_model
    bm_prefix = "B1" if bm_code == "B1" else ("B2" if bm_code.startswith("B2") else ("B3" if bm_code.startswith("B3") else "B2"))

    # 光伏参数
    pv_dict = ConfigLoader.load_pv_defaults(region)
    pv_dict.update(config.pv_params or {})
    if not (config.system or {}).get("pv", False):
        pv_dict["cap_rated"] = 0
    pv_params = PVParams(**_coerce_pv_params(pv_dict))
    pv_region = str((config.run_curves or {}).get("pv_region") or pv_dict.get("region", region))
    pv_curve_type = str((config.run_curves or {}).get("pv_curve_type") or pv_dict.get("curve_type", "annual_avg"))
    pv_curve = ConfigLoader.load_pv_curve(
        pv_region,
        pv_curve_type,
    )

    return run_dispatch(
        hourly,
        BusinessModel(bm_code),
        pricing_mode,
        ess_params,
        FinancialParams(
            r_discount=float(fin_defaults.get("r_discount", 0.06)),
            r_user=float(fin_defaults.get("r_user", r_user_map.get(bm_prefix, 0.30))),
        ),
        wholesale_cfg=wholesale_cfg,
        pv_params=pv_params if pv_params.cap_rated > 0 else None,
        pv_curve=pv_curve,
    )
