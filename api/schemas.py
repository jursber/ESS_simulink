"""请求/响应 Pydantic 模型。"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


# ---------- 请求 ----------

class WholesaleOverrides(BaseModel):
    settlement_mode: Optional[str] = None
    contract_curve_profile: Optional[str] = None
    dayahead_curve_profile: Optional[str] = None


class CalculateRequest(BaseModel):
    scenario_id: str
    variant_key: str = "A"
    pricing_mode: str = "M1"
    business_model: str = "B1"
    system: Optional[dict[str, Any]] = None
    ess_params: Optional[dict[str, Any]] = None
    pv_params: Optional[dict[str, Any]] = None
    run_curves: Optional[dict[str, Any]] = None
    private_overrides: Optional[dict[str, Any]] = None
    wholesale_overrides: Optional[WholesaleOverrides] = None


# ---------- 响应 ----------

class OptionItem(BaseModel):
    value: str
    label: str


class ScenarioBrief(BaseModel):
    id: str
    name: str


class TimeSeries(BaseModel):
    hours: list[int]
    load_ess: list[float]
    soc: list[float]
    load_grid: list[float]
    load_real: list[float]
    price_da: list[float] = []
    price_rt: list[float] = []
    price_user: list[float] = []
    cost_grid: list[float] = []
    cost_ess: list[float] = []
    energy_grid: list[float] = []
    energy_ess: list[float] = []
    energy_load: list[float] = []
    net_load: list[float] = []
    tou_summary: dict = {}
    pv_power: list[float] = []


class OverviewData(BaseModel):
    pricing_mode: str
    pricing_mode_label: str
    business_model: str
    business_model_label: str
    ess_cap_mwh: float
    ess_power_kw: float
    prod_load_mwh: float
    initial_invest_wan: float
    eta_pct: float
    design_life: int
    pv_cap_kw: float = 0
    flex_load_kw: float = 0


class WelfareData(BaseModel):
    user_bill_no_ess_wan: float
    user_bill_with_ess_wan: float
    user_savings_wan: float
    user_return_wan: float
    user_total_wan: float
    combined_bill_no_ess_wan: float
    combined_bill_with_ess_wan: float
    combined_savings_wan: float
    combined_return_wan: float
    combined_total_wan: float
    total_welfare_wan: float


class InvestmentData(BaseModel):
    ess_cap_mwh: float
    unit_cost: float
    initial_invest_wan: float
    om_pct: float
    eta_pct: float
    design_life: int
    roi_years: Optional[float] = None
    irr_pct: Optional[float] = None
    cum_cf_wan: float
    daily_arbitrage_yuan: float
    annual_arbitrage_wan: float
    total_charge_kwh: float
    annual_charge_mwh: float
    total_discharge_kwh: float
    annual_discharge_mwh: float
    equivalent_cycles: float
    annual_cycles: float
    retail_profit_wan: Optional[float] = None


class EconRating(BaseModel):
    subject: str
    metric_label: str
    value: Optional[float] = None
    rating: str = "--"


class PVInvestmentData(BaseModel):
    initial_invest_wan: float
    irr_pct: Optional[float] = None
    payback_years: Optional[float] = None
    cum_cf_wan: float
    daily_gen_kwh: float
    annual_gen_mwh: float
    daily_self_yuan: float
    annual_self_wan: float
    daily_feed_in_yuan: float
    annual_feed_in_wan: float
    self_rate: float


class CalculateResponse(BaseModel):
    time_series: TimeSeries
    overview: OverviewData
    welfare: WelfareData
    investment: InvestmentData
    pv_investment: Optional[PVInvestmentData] = None
    econ_ratings: list[EconRating] = []
    load_cv: Optional[float] = None


class OptionsResponse(BaseModel):
    pricing_modes: list[OptionItem]
    business_models: list[OptionItem]
    settlement_modes: list[OptionItem]
    contract_profiles: list[OptionItem]
    dayahead_profiles: list[OptionItem]


# ---------- 全局参数 ----------

class TariffRow(BaseModel):
    period: str
    start: int
    end: int
    price: float


class GlobalParamsResponse(BaseModel):
    ess: dict[str, Any]
    pv: dict[str, Any] = {}
    financial: dict[str, Any]
    wholesale: dict[str, Any]
    tariff_admin: list[TariffRow]
    tariff_contract: list[TariffRow]
    tariff_jiangsu: dict[str, Any]
    flat_price: float


class GlobalParamsUpdate(BaseModel):
    ess: dict[str, Any]
    financial: dict[str, Any]
    wholesale: dict[str, Any]
    flat_price: float = 0.5
