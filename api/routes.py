"""API 路由。"""
from __future__ import annotations

import pandas as pd
from pathlib import Path
from fastapi import APIRouter, HTTPException

from api.schemas import (
    CalculateRequest,
    CalculateResponse,
    InvestmentData,
    OptionItem,
    OptionsResponse,
    OverviewData,
    ScenarioBrief,
    TimeSeries,
    WelfareData,
    WholesaleOverrides,
)
from src.core.calculator import calculate, effective_wholesale_for_scenario
from src.data.config import ConfigLoader
from src.data.loader import DataLoader
from src.data.scenario import ScenarioConfig, ScenarioManager
from src.models.dispatch import BusinessModel, PricingMode
from src.models.wholesale import UI_OPTION_LISTS, WholesaleSettlementConfig

router = APIRouter()
ROOT = Path(__file__).resolve().parent.parent

PM_LABELS = {
    "M1": "行政分时", "M2": "江苏模式", "M3": "合同分时",
    "M4": "现货联动", "M5": "一口价",
}
BM_LABELS = {
    "B1": "用户+储能", "B2a": "售电公司最优", "B2b": "储能运营商最优",
    "B2c": "用户最优", "B3a": "储售一体最优", "B3b": "用户最优(储售一体)",
    "B4": "总社会福利最高",
}


def _day_production_load_mwh(region: str, date: str) -> float:
    path = ROOT / "data" / "processed" / "load" / f"load_{region}.csv"
    if not path.exists():
        return 0.0
    df = pd.read_csv(path, dtype={"date": str}, encoding="utf-8-sig")
    day = df[df["date"] == str(date)]
    if day.empty:
        return 0.0
    return float(day["Load_real"].sum()) / 1000.0


def _load_real_series(region: str, date: str) -> list[float]:
    path = ROOT / "data" / "processed" / "load" / f"load_{region}.csv"
    if not path.exists():
        return [0.0] * 24
    df = pd.read_csv(path, dtype={"date": str, "hour": int}, encoding="utf-8-sig")
    day = df[df["date"] == date].sort_values("hour")
    if len(day) != 24:
        return [0.0] * 24
    return [float(v) for v in day["Load_real"].tolist()]


def _build_response(
    result,
    config: ScenarioConfig,
    ess,
    prod_mwh: float,
    share_ratio: float,
) -> CalculateResponse:
    ess_mwh = ess.cap_rated / 1000.0
    initial_invest = ess.initial_investment
    initial_invest_wan = initial_invest / 10000

    roi_years = (
        initial_invest / (result.daily_arbitrage * 365)
        if result.daily_arbitrage > 0 else None
    )
    irr_val = result.irr if result.irr != float("inf") else None
    cum_cf = result.daily_arbitrage * 365 * ess.design_life / 10000

    total_charge = sum(min(0, v) for v in result.load_ESS) * -1
    total_discharge = sum(max(0, v) for v in result.load_ESS)

    user_bill_no = result.user_bill_no_ess / 10000
    user_bill_with = result.user_bill_with_ess / 10000
    user_savings = result.user_savings / 10000
    user_return = (result.user_savings - result.user_net) / 10000
    user_total = result.user_bill_with_ess / 10000

    cb_bill_no = user_bill_no
    cb_bill_with = user_bill_with
    cb_savings = user_savings
    cb_return = user_return
    cb_total = (result.user_bill_with_ess + (result.user_savings - result.user_net)) / 10000

    return CalculateResponse(
        time_series=TimeSeries(
            hours=list(range(24)),
            load_ess=list(result.load_ESS),
            soc=list(result.SOC),
            load_grid=list(result.load_grid),
            load_real=list(result.load_real) if hasattr(result, "load_real") else [0.0] * 24,
        ),
        overview=OverviewData(
            pricing_mode=config.pricing_mode,
            pricing_mode_label=PM_LABELS.get(config.pricing_mode, config.pricing_mode),
            business_model=config.business_model,
            business_model_label=BM_LABELS.get(config.business_model, config.business_model),
            ess_cap_mwh=ess_mwh,
            ess_power_kw=ess.max_power,
            prod_load_mwh=prod_mwh,
            initial_invest_wan=initial_invest_wan,
            eta_pct=ess.eta_roundtrip * 100,
            design_life=ess.design_life,
        ),
        welfare=WelfareData(
            user_bill_no_ess_wan=user_bill_no,
            user_bill_with_ess_wan=user_bill_with,
            user_savings_wan=user_savings,
            user_return_wan=user_return,
            user_total_wan=user_total,
            combined_bill_no_ess_wan=cb_bill_no,
            combined_bill_with_ess_wan=cb_bill_with,
            combined_savings_wan=cb_savings,
            combined_return_wan=cb_return,
            combined_total_wan=cb_total,
            total_welfare_wan=result.total_welfare / 10000,
        ),
        investment=InvestmentData(
            ess_cap_mwh=ess_mwh,
            unit_cost=ess.unit_cost,
            initial_invest_wan=initial_invest_wan,
            om_pct=ess.r_om * 100,
            eta_pct=ess.eta_roundtrip * 100,
            design_life=ess.design_life,
            roi_years=roi_years,
            irr_pct=irr_val * 100 if irr_val is not None else None,
            cum_cf_wan=cum_cf,
            daily_arbitrage_yuan=result.daily_arbitrage,
            annual_arbitrage_wan=result.daily_arbitrage * 365 / 10000,
            total_charge_kwh=total_charge,
            annual_charge_mwh=total_charge * 365 / 1000,
            total_discharge_kwh=total_discharge,
            annual_discharge_mwh=total_discharge * 365 / 1000,
            equivalent_cycles=result.equivalent_cycles,
            annual_cycles=result.equivalent_cycles * 365,
        ),
    )


# ---------- 端点 ----------

@router.get("/scenarios", response_model=list[ScenarioBrief])
def list_scenarios():
    mgr = ScenarioManager()
    return [ScenarioBrief(id=it["id"], name=it["name"]) for it in mgr.list_all()]


@router.get("/scenarios/{scenario_id}")
def get_scenario(scenario_id: str):
    try:
        mgr = ScenarioManager()
        cfg = mgr.load(scenario_id)
    except FileNotFoundError:
        raise HTTPException(404, f"方案 {scenario_id} 不存在")
    return cfg.to_dict()


@router.get("/options", response_model=OptionsResponse)
def get_options():
    return OptionsResponse(
        pricing_modes=[OptionItem(value=k, label=v) for k, v in PM_LABELS.items()],
        business_models=[OptionItem(value=k, label=v) for k, v in BM_LABELS.items()],
        settlement_modes=[
            OptionItem(value=v, label=l) for v, l in UI_OPTION_LISTS["settlement_mode"]
        ],
        contract_profiles=[
            OptionItem(value=v, label=l) for v, l in UI_OPTION_LISTS["contract_curve_profile"]
        ],
        dayahead_profiles=[
            OptionItem(value=v, label=l) for v, l in UI_OPTION_LISTS["dayahead_curve_profile"]
        ],
    )


@router.post("/calculate", response_model=CalculateResponse)
def run_calculation(req: CalculateRequest):
    try:
        mgr = ScenarioManager()
        config = mgr.load(req.scenario_id)
    except FileNotFoundError:
        raise HTTPException(404, f"方案 {req.scenario_id} 不存在")

    config.pricing_mode = req.pricing_mode
    config.business_model = req.business_model

    wholesale_cfg = effective_wholesale_for_scenario(config)
    if req.wholesale_overrides:
        flat = wholesale_cfg.to_flat_dict()
        ov = req.wholesale_overrides
        if ov.settlement_mode is not None:
            flat["settlement_mode"] = ov.settlement_mode
        if ov.contract_curve_profile is not None:
            flat["contract_curve_profile"] = ov.contract_curve_profile
        if ov.dayahead_curve_profile is not None:
            flat["dayahead_curve_profile"] = ov.dayahead_curve_profile
        wholesale_cfg = WholesaleSettlementConfig.from_flat_dict(flat)

    try:
        result = calculate(config, wholesale_cfg=wholesale_cfg)
    except Exception as e:
        raise HTTPException(422, f"计算失败: {e}")

    ess = ConfigLoader.load_ess_defaults(config.region)
    prod_mwh = _day_production_load_mwh(config.region, config.selected_date)

    # 获取 load_real 用于前端图表
    load_real = _load_real_series(config.region, config.selected_date)

    resp = _build_response(result, config, ess, prod_mwh, 20.0)
    resp.time_series.load_real = load_real
    return resp
