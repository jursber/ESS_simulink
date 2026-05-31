"""API 路由。"""
from __future__ import annotations

import pandas as pd
from pathlib import Path
from fastapi import APIRouter, HTTPException

from api.schemas import (
    CalculateRequest,
    CalculateResponse,
    GlobalParamsResponse,
    GlobalParamsUpdate,
    InvestmentData,
    OptionItem,
    OptionsResponse,
    OverviewData,
    ScenarioBrief,
    TariffRow,
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

    # 获取电价曲线
    try:
        price_da, price_rt = DataLoader.load_spot_prices(config.region, config.selected_date)
    except Exception:
        price_da, price_rt = [], []

    resp = _build_response(result, config, ess, prod_mwh, 20.0)
    resp.time_series.load_real = load_real
    resp.time_series.price_da = price_da
    resp.time_series.price_rt = price_rt
    resp.time_series.price_user = list(result.P_user_curve) if hasattr(result, 'P_user_curve') else []
    return resp


# ---------- 全局参数 ----------

def _tariff_to_rows(df: pd.DataFrame) -> list[TariffRow]:
    rows = []
    for _, r in df.iterrows():
        rows.append(TariffRow(
            period=str(r.get("period", "")),
            start=int(r.get("start_hour", r.get("start", 0))),
            end=int(r.get("end_hour", r.get("end", 0))),
            price=float(r.get("price_yuan_per_kwh", r.get("price", 0))),
        ))
    return rows


@router.get("/global-params", response_model=GlobalParamsResponse)
def get_global_params():
    ess = ConfigLoader.load_ess_defaults("henan")
    fin = ConfigLoader.load_financial_defaults("henan")
    wcfg = ConfigLoader.load_wholesale_settlement()
    tariff_admin = ConfigLoader.load_tariff("henan", "admin")
    tariff_contract = ConfigLoader.load_tariff("henan", "contract")
    tariff_jiangsu = ConfigLoader.load_tariff("henan", "jiangsu")
    return GlobalParamsResponse(
        ess={
            "cap_rated": ess.cap_rated,
            "c_rate": ess.c_rate,
            "eta_roundtrip": ess.eta_roundtrip,
            "soc_min": ess.soc_min,
            "soc_max": ess.soc_max,
            "unit_cost": ess.unit_cost,
            "r_om": ess.r_om,
            "design_life": ess.design_life,
            "r_degrade": ess.r_degrade,
        },
        financial={k: float(v) for k, v in fin.items()},
        wholesale=wcfg.to_flat_dict(),
        tariff_admin=_tariff_to_rows(tariff_admin),
        tariff_contract=_tariff_to_rows(tariff_contract),
        tariff_jiangsu=tariff_jiangsu,
        flat_price=0.55,
    )


@router.put("/global-params")
def update_global_params(req: GlobalParamsUpdate):
    from src.models.dispatch import ESSParams
    from src.models.wholesale import (
        MarketRegionCode, SettlementMode, TimeGranularity,
        DaQuantityDefinition, PriceNode,
    )
    # 保存 ESS
    ess = ESSParams(
        cap_rated=req.ess.get("cap_rated", 5000),
        c_rate=req.ess.get("c_rate", 0.5),
        eta_roundtrip=req.ess.get("eta_roundtrip", 0.85),
        soc_min=req.ess.get("soc_min", 0.10),
        soc_max=req.ess.get("soc_max", 0.90),
        unit_cost=req.ess.get("unit_cost", 0.9),
        r_om=req.ess.get("r_om", 0.01),
        design_life=int(req.ess.get("design_life", 10)),
        r_degrade=req.ess.get("r_degrade", 0.025),
    )
    ConfigLoader.save_ess_defaults(ess)
    # 保存财务
    ConfigLoader.save_financial_defaults(req.financial)
    # 保存批发结算
    wflat = req.wholesale
    wcfg = WholesaleSettlementConfig(
        market_region_code=MarketRegionCode(wflat.get("market_region_code", "CN")),
        settlement_mode=SettlementMode(wflat.get("settlement_mode", "GUANGDONG_STYLE")),
        time_granularity=TimeGranularity(wflat.get("time_granularity", "1h")),
        da_quantity_definition=DaQuantityDefinition(wflat.get("da_quantity_definition", "declaration")),
        price_node=PriceNode(wflat.get("price_node", "unified")),
        contract_curve_profile=wflat.get("contract_curve_profile", "mock_henan"),
        dayahead_curve_profile=wflat.get("dayahead_curve_profile", "mock_henan"),
        purchase_monthly_constant_yuan=float(wflat.get("purchase_monthly_constant_yuan", 0)),
        guangxi_month_smooth_yuan=float(wflat.get("guangxi_month_smooth_yuan", 0)),
        shanxi_wholesale_addon_yuan=float(wflat.get("shanxi_wholesale_addon_yuan", 0)),
    )
    ConfigLoader.save_wholesale_settlement(wcfg)
    return {"status": "ok"}


@router.get("/params/contract-position")
def get_contract_position():
    df = ConfigLoader.load_contract_position("henan", None, profile="mock_henan")
    return df.to_dict(orient="records")


@router.get("/params/dayahead-position")
def get_dayahead_position():
    df = ConfigLoader.load_dayahead_position("henan", None, profile="mock_henan")
    return df.to_dict(orient="records")
