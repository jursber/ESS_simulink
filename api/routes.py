"""API 路由。"""
from __future__ import annotations

import hashlib
import json
import pandas as pd
import re
from pathlib import Path
from fastapi import APIRouter, HTTPException

from api.schemas import (
    CalculateRequest,
    CalculateResponse,
    EconRating,
    GlobalParamsResponse,
    GlobalParamsUpdate,
    InvestmentData,
    OptionItem,
    OptionsResponse,
    OverviewData,
    PVInvestmentData,
    ScenarioBrief,
    TariffRow,
    TimeSeries,
    WelfareData,
    WholesaleOverrides,
)
from src.core.calculator import calculate, effective_wholesale_for_scenario, resolve_runtime_params
from src.data.config import ConfigLoader
from src.data.loader import DataLoader
from src.data.scenario import ScenarioConfig, ScenarioManager
from src.models.dispatch import BusinessModel, PricingMode
from src.models.wholesale import UI_OPTION_LISTS, WholesaleSettlementConfig

router = APIRouter()
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DOCS_DIR = ROOT / "docs"
PRD_DIR = ROOT / "PRD"

# 计算结果缓存（内存级，重启清空）
_result_cache: dict[str, CalculateResponse] = {}
CACHE_MAX_SIZE = 100

def _params_version() -> list[tuple[str, int, int]]:
    """Return a compact version signature for global parameter files."""
    version = []
    for path in sorted((DATA_DIR / "params").glob("*.csv")):
        stat = path.stat()
        version.append((path.name, stat.st_mtime_ns, stat.st_size))
    return version


def _scenario_fingerprint(config: ScenarioConfig) -> str:
    payload = {
        "scenario": config.to_dict(),
        "params": _params_version(),
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _cache_key(
    scenario_id: str,
    pricing_mode: str,
    business_model: str,
    settlement: str,
    contract: str,
    dayahead: str,
    fingerprint: str,
) -> str:
    return f"{scenario_id}|{pricing_mode}|{business_model}|{settlement}|{contract}|{dayahead}|{fingerprint}"

PM_LABELS = {
    "M1": "行政分时", "M2": "江苏模式", "M3": "合同分时",
    "M4": "现货联动", "M4-contract": "中长期联动", "M5": "一口价",
}
BM_LABELS = {
    "B1": "用户+储能", "B2a": "售电公司最优", "B2b": "储能运营商最优",
    "B2c": "用户最优", "B3a": "储售一体最优", "B3b": "用户最优(储售一体)",
    "B4": "总社会福利最高",
}


def _find_monthly_file(directory: Path, date: str) -> Path:
    """在目录中查找匹配月份的 CSV 文件，找不到则用最近的。"""
    ym = date[:4] + date[5:7]
    path = directory / f"{ym}.csv"
    if path.exists():
        return path
    default = directory / "daily_default.csv"
    if default.exists():
        return default
    for f in sorted(directory.glob("*.csv")):
        try:
            cols = pd.read_csv(f, nrows=0, comment='#').columns.tolist()
            if "date" in cols:
                return f
        except Exception:
            pass
    raise FileNotFoundError(f"未找到数据文件: {directory}")


def _day_production_load_mwh(region: str, date: str) -> float:
    try:
        path = _find_monthly_file(DATA_DIR / "load", date)
    except FileNotFoundError:
        return 0.0
    df = pd.read_csv(path, dtype={"date": str}, comment='#')
    day = df[df["date"] == str(date)]
    if day.empty:
        return 0.0
    return float(day["Load_real"].sum()) / 1000.0


def _load_real_series(region: str, date: str) -> list[float]:
    try:
        path = _find_monthly_file(DATA_DIR / "load", date)
    except FileNotFoundError:
        return [0.0] * 24
    df = pd.read_csv(path, dtype={"date": str, "hour": int}, comment='#')
    day = df[df["date"] == date].sort_values("hour")
    if len(day) != 24:
        return [0.0] * 24
    return [float(v) for v in day["Load_real"].tolist()]


_PERIOD_CN = {
    "valley": "谷",
    "flat": "平",
    "peak": "峰",
    "super_peak": "尖峰",
    "deep_valley": "深谷",
}


def _compute_tou_summary(config: ScenarioConfig, load_real: list[float]) -> dict:
    """按峰谷平时段汇总全天用电量（kWh）。"""
    mode = config.pricing_mode
    # M5 一口价无 period 划分
    if mode == "M5":
        return {}
    # 确定 tariff 加载模式
    mode_map = {"M1": "admin", "M2": "admin", "M3": "contract", "M4": "admin"}
    tariff_key = mode_map.get(mode, "admin")
    try:
        tariff_df = ConfigLoader.load_tariff(config.region, tariff_key)
    except Exception:
        return {}
    summary: dict[str, float] = {}
    for _, row in tariff_df.iterrows():
        period = str(row.get("period", ""))
        start = int(row.get("start_hour", 0))
        end = int(row.get("end_hour", 0))
        cn = _PERIOD_CN.get(period, period)
        for h in range(start, end):
            if 0 <= h < 24:
                summary[cn] = summary.get(cn, 0.0) + load_real[h]
    summary["_total"] = round(sum(load_real), 1)
    return {k: round(v, 1) for k, v in summary.items()}


def _build_response(
    result,
    config: ScenarioConfig,
    ess,
    prod_mwh: float,
    share_ratio: float,
    load_real: list[float] | None = None,
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

    # 逐小时数据
    _load_real = load_real if load_real else [0.0] * 24
    _load_grid = list(result.load_grid)
    _load_ess = list(result.load_ESS)
    _P_user = list(result.P_user_curve) if hasattr(result, 'P_user_curve') else [0.0] * 24

    # 成本（元）
    cost_grid = [_load_grid[h] * _P_user[h] for h in range(24)]
    cost_ess = [_load_ess[h] * _P_user[h] for h in range(24)]

    # 峰谷平汇总
    tou_summary = _compute_tou_summary(config, _load_real)

    # 光伏投资数据
    pv_invest = None
    pv_cap = getattr(result, 'pv_cap_kw', 0.0)
    if pv_cap > 0:
        pv_irr_val = result.pv_irr if result.pv_irr != float("inf") else None
        pv_payback = result.pv_payback_years if result.pv_payback_years != float("inf") else None
        pv_annual_revenue = (result.pv_self_daily + result.pv_feed_in_daily) * 365
        pv_om_annual = pv_cap * 3.5 * 1000 * 0.015  # cap × unit_cost × 1000 × r_om
        pv_cum_cf = (pv_annual_revenue - pv_om_annual) * 25 / 10000
        pv_invest = PVInvestmentData(
            initial_invest_wan=pv_cap * 3.5 / 10,  # kWp × 元/Wp / 10000 = 万元
            irr_pct=pv_irr_val * 100 if pv_irr_val is not None else None,
            payback_years=pv_payback,
            cum_cf_wan=pv_cum_cf,
            daily_gen_kwh=result.pv_total_gen_daily,
            annual_gen_mwh=result.pv_total_gen_daily * 365 / 1000,
            daily_self_yuan=result.pv_self_daily,
            annual_self_wan=result.pv_self_daily * 365 / 10000,
            daily_feed_in_yuan=result.pv_feed_in_daily,
            annual_feed_in_wan=result.pv_feed_in_daily * 365 / 10000,
            self_rate=result.pv_self_rate,
        )

    return CalculateResponse(
        time_series=TimeSeries(
            hours=list(range(24)),
            load_ess=_load_ess,
            soc=list(result.SOC),
            load_grid=_load_grid,
            load_real=_load_real,
            price_da=list(result.P_da_curve) if hasattr(result, 'P_da_curve') else [],
            price_rt=list(result.P_rt_curve) if hasattr(result, 'P_rt_curve') else [],
            price_user=_P_user,
            cost_grid=cost_grid,
            cost_ess=cost_ess,
            energy_grid=_load_grid,
            energy_ess=_load_ess,
            energy_load=_load_real,
            net_load=_load_grid,
            tou_summary=tou_summary,
            pv_power=list(getattr(result, 'pv_generation', [])),
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
            pv_cap_kw=pv_cap,
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
            retail_profit_wan=result.retail_profit / 10000 if result.retail_profit else 0,
        ),
        pv_investment=pv_invest,
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


@router.post("/scenarios")
def create_scenario(req: dict):
    """创建方案。用于方案管理页的轻量 CRUD。"""
    name = str(req.get("name") or "未命名方案")
    cfg = ScenarioConfig(
        name=name,
        region=str(req.get("region") or "henan"),
        pricing_mode=str(req.get("pricing_mode") or "M1"),
        business_model=str(req.get("business_model") or "B1"),
        selected_date=str(req.get("selected_date") or "2026-03-15"),
        ess_params=req.get("ess_params") or {},
        pv_params=req.get("pv_params") or {},
        financial_params=req.get("financial_params") or {},
        private_overrides=req.get("private_overrides") or {},
        wholesale_overrides=req.get("wholesale_overrides") or {},
        system=req.get("system") or None,
        run_curves=req.get("run_curves") or None,
        variants=req.get("variants") or None,
    )
    sid = ScenarioManager().save(cfg)
    return {"status": "ok", "id": sid, "scenario": cfg.to_dict()}


@router.put("/scenarios/{scenario_id}")
def update_scenario(scenario_id: str, req: dict):
    mgr = ScenarioManager()
    try:
        cfg = mgr.load(scenario_id)
    except FileNotFoundError:
        raise HTTPException(404, f"方案 {scenario_id} 不存在")

    for key in ("name", "region", "pricing_mode", "business_model", "selected_date"):
        if key in req:
            setattr(cfg, key, req[key])
    if "ess_params" in req:
        cfg.ess_params = req["ess_params"] or {}
    if "pv_params" in req:
        cfg.pv_params = req["pv_params"] or {}
    if "financial_params" in req:
        cfg.financial_params = req["financial_params"] or {}
    if "private_overrides" in req:
        cfg.private_overrides = req["private_overrides"] or {}
    if "wholesale_overrides" in req:
        cfg.wholesale_overrides = req["wholesale_overrides"] or {}
    if "system" in req:
        cfg.system = req["system"] or {"net_load": True, "ess": True, "pv": False}
    if "run_curves" in req:
        cfg.run_curves = req["run_curves"] or {}
    if "variants" in req:
        cfg.variants = cfg._normalize_variants(req["variants"] or {})
    mgr.save(cfg)
    _result_cache.clear()
    return {"status": "ok", "scenario": cfg.to_dict()}


@router.post("/scenarios/{scenario_id}/duplicate")
def duplicate_scenario(scenario_id: str, req: dict | None = None):
    mgr = ScenarioManager()
    try:
        cfg = mgr.load(scenario_id)
    except FileNotFoundError:
        raise HTTPException(404, f"方案 {scenario_id} 不存在")
    cfg.id = None
    cfg.name = (req or {}).get("name") or f"{cfg.name}-副本"
    sid = mgr.save(cfg)
    return {"status": "ok", "id": sid, "scenario": cfg.to_dict()}


@router.delete("/scenarios/{scenario_id}")
def delete_scenario(scenario_id: str):
    mgr = ScenarioManager()
    try:
        mgr.delete(scenario_id)
    except FileNotFoundError:
        raise HTTPException(404, f"方案 {scenario_id} 不存在")
    _result_cache.clear()
    return {"status": "ok"}


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
        parent = mgr.load(req.scenario_id)
    except FileNotFoundError:
        raise HTTPException(404, f"方案 {req.scenario_id} 不存在")

    variant_overrides = {
        "pricing_mode": req.pricing_mode,
        "business_model": req.business_model,
    }
    if req.system is not None:
        variant_overrides["system"] = req.system
    if req.ess_params is not None:
        variant_overrides["ess_params"] = req.ess_params
    if req.pv_params is not None:
        variant_overrides["pv_params"] = req.pv_params
    if req.run_curves is not None:
        variant_overrides["run_curves"] = req.run_curves
    if req.private_overrides is not None:
        variant_overrides["private_overrides"] = req.private_overrides

    config = parent.variant_config(req.variant_key, variant_overrides)
    if req.wholesale_overrides is not None:
        merged_wholesale = dict(config.wholesale_overrides or {})
        ov_data = req.wholesale_overrides.model_dump(exclude_none=True)
        merged_wholesale.update(ov_data)
        config.wholesale_overrides = merged_wholesale

    # 缓存 key 必须包含方案内容和全局参数版本，否则参数编辑后可能返回旧结果。
    wholesale_cfg = effective_wholesale_for_scenario(config)
    key = _cache_key(
        f"{req.scenario_id}:{req.variant_key}", req.pricing_mode, req.business_model,
        wholesale_cfg.settlement_mode.value,
        wholesale_cfg.contract_curve_profile,
        wholesale_cfg.dayahead_curve_profile,
        _scenario_fingerprint(config),
    )
    if key in _result_cache:
        return _result_cache[key]

    try:
        result = calculate(config, wholesale_cfg=wholesale_cfg)
    except Exception as e:
        raise HTTPException(422, f"计算失败: {e}")

    ess, _ = resolve_runtime_params(config)

    # 获取 load_real 用于前端图表；若方案选择了运行曲线，使用算法实际输入。
    load_real = list(getattr(result, "load_real", None) or _load_real_series(config.region, config.selected_date))
    prod_mwh = sum(load_real) / 1000.0

    # 获取电价曲线
    try:
        price_da, price_rt = DataLoader.load_spot_prices(config.region, config.selected_date)
    except Exception:
        price_da, price_rt = [], []

    resp = _build_response(result, config, ess, prod_mwh, 20.0, load_real=load_real)

    # 负荷变异系数
    import numpy as np
    load_arr = np.array(load_real)
    resp.load_cv = float(np.std(load_arr) / np.mean(load_arr)) if np.mean(load_arr) > 0 else 0

    # 经济性评级
    resp.econ_ratings = _compute_econ_ratings(resp, result)

    # 缓存结果
    if len(_result_cache) >= CACHE_MAX_SIZE:
        _result_cache.pop(next(iter(_result_cache)))
    _result_cache[key] = resp

    return resp


def _scenario_compare_metrics(
    scenario_id: str,
    pricing_mode: str | None = None,
    business_model: str | None = None,
    variant_key: str = "A",
    variant_payload: dict | None = None,
    alias: str | None = None,
) -> dict:
    mgr = ScenarioManager()
    parent = mgr.load(scenario_id)
    cfg = parent.variant_config(variant_key, variant_payload or {})
    if pricing_mode:
        cfg.pricing_mode = pricing_mode
    if business_model:
        cfg.business_model = business_model
    wholesale_cfg = effective_wholesale_for_scenario(cfg)
    result = calculate(cfg, wholesale_cfg=wholesale_cfg)
    load_real = list(getattr(result, "load_real", None) or _load_real_series(cfg.region, cfg.selected_date))
    ess, _ = resolve_runtime_params(cfg)
    prod_mwh = sum(load_real) / 1000.0
    resp = _build_response(result, cfg, ess, prod_mwh, 20.0, load_real=load_real)
    import numpy as np
    load_arr = np.array(load_real)
    resp.load_cv = float(np.std(load_arr) / np.mean(load_arr)) if np.mean(load_arr) > 0 else 0
    resp.econ_ratings = _compute_econ_ratings(resp, result)
    return {
        "id": scenario_id,
        "name": alias or cfg.name,
        "variant_key": variant_key,
        "region": cfg.region,
        "date": cfg.selected_date,
        "pricing_mode": cfg.pricing_mode,
        "pricing_mode_label": PM_LABELS.get(cfg.pricing_mode, cfg.pricing_mode),
        "business_model": cfg.business_model,
        "business_model_label": BM_LABELS.get(cfg.business_model, cfg.business_model),
        "metrics": {
            "total_welfare_wan": resp.welfare.total_welfare_wan,
            "user_savings_wan": resp.welfare.user_savings_wan,
            "user_total_wan": resp.welfare.user_total_wan,
            "ess_irr_pct": resp.investment.irr_pct,
            "ess_payback_years": resp.investment.roi_years,
            "ess_annual_arbitrage_wan": resp.investment.annual_arbitrage_wan,
            "ess_cycles_day": resp.investment.equivalent_cycles,
            "retail_profit_wan": resp.investment.retail_profit_wan or 0,
            "pv_irr_pct": resp.pv_investment.irr_pct if resp.pv_investment else None,
            "pv_annual_gen_mwh": resp.pv_investment.annual_gen_mwh if resp.pv_investment else 0,
            "pv_self_rate": resp.pv_investment.self_rate if resp.pv_investment else None,
            "load_cv": resp.load_cv,
        },
        "ratings": [r.model_dump() for r in resp.econ_ratings],
    }


@router.post("/compare")
def compare_scenarios(req: dict):
    """多方案对比。最多 4 个方案，返回横向指标矩阵。"""
    items = req.get("items") or []
    if not items:
        raise HTTPException(400, "至少选择一个方案")
    if len(items) > 4:
        raise HTTPException(400, "最多支持 4 个方案")

    rows = []
    for item in items:
        try:
            rows.append(_scenario_compare_metrics(
                str(item["scenario_id"]),
                item.get("pricing_mode"),
                item.get("business_model"),
                item.get("variant_key") or "A",
                item.get("variant"),
                item.get("alias"),
            ))
        except FileNotFoundError:
            raise HTTPException(404, f"方案 {item.get('scenario_id')} 不存在")
    metric_defs = [
        {"key": "total_welfare_wan", "label": "总社会福利提升", "unit": "万元", "direction": "max"},
        {"key": "user_savings_wan", "label": "终端用户节费", "unit": "万元", "direction": "max"},
        {"key": "user_total_wan", "label": "用户实际用电成本", "unit": "万元", "direction": "min"},
        {"key": "ess_irr_pct", "label": "储能 IRR", "unit": "%", "direction": "max"},
        {"key": "ess_payback_years", "label": "储能静态回收期", "unit": "年", "direction": "min"},
        {"key": "ess_annual_arbitrage_wan", "label": "储能年套利创值", "unit": "万元", "direction": "max"},
        {"key": "ess_cycles_day", "label": "日等效循环次数", "unit": "次/日", "direction": "balanced"},
        {"key": "retail_profit_wan", "label": "售电公司利润", "unit": "万元", "direction": "max"},
        {"key": "pv_irr_pct", "label": "光伏 IRR", "unit": "%", "direction": "max"},
        {"key": "pv_annual_gen_mwh", "label": "光伏年发电量", "unit": "MWh", "direction": "max"},
        {"key": "pv_self_rate", "label": "光伏本地消纳率", "unit": "%", "direction": "max"},
        {"key": "load_cv", "label": "用户负荷变异系数", "unit": "-", "direction": "context"},
    ]
    return {"items": rows, "metrics": metric_defs}


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
    pv = ConfigLoader.load_pv_defaults("henan")
    fin = ConfigLoader.load_financial_defaults("henan")
    wcfg = ConfigLoader.load_wholesale_settlement()
    tariff_admin = ConfigLoader.load_tariff("henan", "admin")
    tariff_contract = ConfigLoader.load_tariff("henan", "contract")
    return GlobalParamsResponse(
        ess={
            "cap_rated": ess.cap_rated,
            "power_rated": ess.power_rated,
            "eta_roundtrip": ess.eta_roundtrip,
            "eta_charge": ess.eta_charge,
            "soc_min": ess.soc_min,
            "soc_max": ess.soc_max,
            "unit_cost": ess.unit_cost,
            "r_om": ess.r_om,
            "design_life": ess.design_life,
            "r_degrade": ess.r_degrade,
            "degrade_enabled": ess.degrade_enabled,
            "cycle_life": ess.cycle_life,
            "cycle_enabled": ess.cycle_enabled,
            "r_ess_share": ess.r_ess_share,
        },
        pv=pv,
        financial={k: float(v) for k, v in fin.items()},
        wholesale=wcfg.to_flat_dict(),
        tariff_admin=_tariff_to_rows(tariff_admin),
        tariff_contract=_tariff_to_rows(tariff_contract),
        tariff_jiangsu={},
        flat_price=0.5,
    )


@router.put("/global-params")
def update_global_params(req: GlobalParamsUpdate):
    from src.models.dispatch import ESSParams
    from src.models.wholesale import (
        MarketRegionCode, SettlementMode, TimeGranularity,
        DaQuantityDefinition,
    )
    # 保存 ESS
    ess = ESSParams(
        cap_rated=req.ess.get("cap_rated", 1000),
        power_rated=req.ess.get("power_rated", 0.5),
        eta_roundtrip=req.ess.get("eta_roundtrip", 0.87),
        eta_charge=req.ess.get("eta_charge", 0.92),
        soc_min=req.ess.get("soc_min", 0.10),
        soc_max=req.ess.get("soc_max", 0.90),
        design_life=int(req.ess.get("design_life", 10)),
        r_degrade=req.ess.get("r_degrade", 0.025),
        degrade_enabled=req.ess.get("degrade_enabled", False),
        cycle_life=int(req.ess.get("cycle_life", 5000)),
        cycle_enabled=req.ess.get("cycle_enabled", False),
        unit_cost=req.ess.get("unit_cost", 0.9),
        r_om=req.ess.get("r_om", 0.01),
        r_ess_share=req.ess.get("r_ess_share", 0.20),
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
        contract_curve_profile=wflat.get("contract_curve_profile", "mock_henan"),
        dayahead_curve_profile=wflat.get("dayahead_curve_profile", "mock_henan"),
        purchase_monthly_constant_yuan=float(wflat.get("purchase_monthly_constant_yuan", 0)),
        guangxi_month_smooth_yuan=float(wflat.get("guangxi_month_smooth_yuan", 0)),
        shanxi_wholesale_addon_yuan=float(wflat.get("shanxi_wholesale_addon_yuan", 0)),
    )
    ConfigLoader.save_wholesale_settlement(wcfg)
    return {"status": "ok"}


def _rate_irr(irr_pct: float) -> str:
    if irr_pct is None:
        return "--"
    if irr_pct <= 0:
        return "极差"
    if irr_pct <= 2:
        return "较差"
    if irr_pct <= 4:
        return "差"
    if irr_pct <= 8:
        return "达标"
    if irr_pct <= 12:
        return "优秀"
    return "无敌"


def _rate_retail(yuan_per_mwh: float) -> str:
    if yuan_per_mwh < 0:
        return "极差"
    if yuan_per_mwh < 1:
        return "较差"
    if yuan_per_mwh < 3:
        return "差"
    if yuan_per_mwh < 5:
        return "达标"
    if yuan_per_mwh < 8:
        return "优秀"
    return "无敌"


def _rate_user(wan_per_mwh: float) -> str:
    if wan_per_mwh < 0:
        return "极差"
    if wan_per_mwh < 2:
        return "较差"
    if wan_per_mwh < 4:
        return "差"
    if wan_per_mwh < 7:
        return "达标"
    if wan_per_mwh < 10:
        return "优秀"
    return "无敌"


def _compute_econ_ratings(resp: CalculateResponse, result) -> list[EconRating]:
    ratings = []

    # 终端用户：万元/MWh储能 = user_savings_wan / ess_cap_mwh
    ess_mwh = resp.overview.ess_cap_mwh
    user_wan_per_mwh = resp.welfare.user_savings_wan / ess_mwh if ess_mwh > 0 else 0
    ratings.append(EconRating(
        subject="终端用户",
        metric_label="储能节费(万元/MWh)",
        value=round(user_wan_per_mwh, 2),
        rating=_rate_user(user_wan_per_mwh),
    ))

    # 光伏投资 IRR
    pv_irr = getattr(result, 'pv_irr', 0.0)
    pv_irr_pct = pv_irr * 100 if pv_irr and pv_irr != float("inf") else None
    ratings.append(EconRating(
        subject="光伏投资",
        metric_label="IRR%",
        value=round(pv_irr_pct, 2) if pv_irr_pct is not None else None,
        rating=_rate_irr(pv_irr_pct),
    ))

    # 储能投资 IRR
    irr_pct = resp.investment.irr_pct
    ratings.append(EconRating(
        subject="储能投资",
        metric_label="IRR%",
        value=round(irr_pct, 2) if irr_pct is not None else None,
        rating=_rate_irr(irr_pct),
    ))

    # 售电公司：度电收益(元/MWh) = retail_profit / total_discharge_mwh
    discharge_mwh = resp.investment.annual_discharge_mwh
    retail_profit_wan = resp.investment.retail_profit_wan or 0
    retail_per_mwh = (retail_profit_wan * 10000) / (discharge_mwh * 365) if discharge_mwh > 0 else 0
    ratings.append(EconRating(
        subject="售电公司",
        metric_label="度电收益(元/MWh)",
        value=round(retail_per_mwh, 2),
        rating=_rate_retail(retail_per_mwh),
    ))

    return ratings


@router.get("/params/contract-position")
def get_contract_position():
    df = ConfigLoader.load_contract_position("henan", None, profile="mock_henan")
    return df.to_dict(orient="records")


@router.get("/params/dayahead-position")
def get_dayahead_position():
    df = ConfigLoader.load_dayahead_position("henan", None, profile="mock_henan")
    return df.to_dict(orient="records")


# ---------- 负荷曲线 ----------

_LABELS = {
    "steady_24h": "全天平稳生产",
    "daytime_single_shift": "白天生产,一班制",
    "daytime_single_shift_v2": "白天生产,一班制(变体)",
    "night_winter": "夜间生产-冬季",
    "night_summer": "夜间生产-夏季",
    "night_single_shift": "夜间生产,一班制",
    "night_uneven": "夜间非均匀生产",
    "night_rising": "夜间增长型生产",
    "all_day_production": "全天候生产",
    "all_day_two_shifts": "全天候生产,两班制",
    "all_day_daytime_high": "全天候生产,白天偏高",
    "continuous_24h": "全天24小时生产",
    "first_half_night": "前半夜生产",
    "second_half_night": "后半夜生产",
    "noon_evening_peak": "午间晚间高峰生产",
    "daytime_multi_peak": "白天生产,多峰制",
}


def _calc_max_demand(minute_data: list[float]) -> tuple[float, str]:
    """15 分钟滑动平均最大值，返回 (值, 时间段)。前 14 分钟与第 15 分钟保持一致。"""
    padded = [minute_data[0]] * 14 + list(minute_data)
    rolling = []
    for i in range(14, len(padded)):
        window = padded[i - 14:i + 1]
        rolling.append(sum(window) / 15.0)
    max_val = max(rolling)
    max_idx = rolling.index(max_val)
    start_h, start_m = divmod(max_idx, 60)
    end_m = max_idx + 15
    end_h, end_m = divmod(end_m, 60)
    if end_h >= 24:
        end_h = 23
        end_m = 59
    return max_val, f"{start_h:02d}:{start_m:02d}-{end_h:02d}:{end_m:02d}"


def _scale_curve(minute_data: list[float], avg_load: float = None, max_load: float = None) -> list[float]:
    """按平均负荷或最大负荷缩放曲线形状。"""
    if avg_load is not None:
        cur_avg = sum(minute_data) / len(minute_data)
        if cur_avg > 0:
            ratio = avg_load / cur_avg
            return [v * ratio for v in minute_data]
    elif max_load is not None:
        cur_max = max(minute_data)
        if cur_max > 0:
            ratio = max_load / cur_max
            return [v * ratio for v in minute_data]
    return minute_data


@router.get("/params/load-profiles")
def get_load_profiles():
    """返回 16 个负荷曲线的摘要数据。"""
    from src.data.loader import aggregate_minute_to_hour
    load_dir = DATA_DIR / "load"
    profiles = []
    for f in sorted(load_dir.glob("*.csv")):
        if f.parent.name == "custom":
            continue
        df = pd.read_csv(f, comment='#')
        if "load_MW" not in df.columns:
            continue
        minute_data = df["load_MW"].tolist()
        if len(minute_data) != 1440:
            continue
        hour_data = aggregate_minute_to_hour(minute_data)
        max_demand, period = _calc_max_demand(minute_data)
        profiles.append({
            "name": f.stem,
            "label": _LABELS.get(f.stem, f.stem),
            "minute_data": [round(v, 6) for v in minute_data],
            "hour_data": [round(v, 6) for v in hour_data],
            "avg_load_mw": round(sum(minute_data) / len(minute_data), 6),
            "max_load_mw": round(max(minute_data), 6),
            "max_demand_mw": round(max_demand, 6),
            "max_demand_period": period,
        })
    return {"profiles": profiles}


@router.post("/params/load-profile/preview")
def preview_load_profile(req: dict):
    """返回缩放后的负荷曲线数据。"""
    from src.data.loader import aggregate_minute_to_hour
    profile_name = req.get("profile_name", "steady_24h")
    avg_load = req.get("avg_load")
    max_load = req.get("max_load")

    path = DATA_DIR / "load" / f"{profile_name}.csv"
    if not path.exists():
        raise HTTPException(404, f"曲线 {profile_name} 不存在")

    df = pd.read_csv(path, comment='#')
    minute_data = df["load_MW"].tolist()

    scaled = _scale_curve(minute_data, avg_load=avg_load, max_load=max_load)
    hour_data = aggregate_minute_to_hour(scaled)
    max_demand, period = _calc_max_demand(scaled)

    return {
        "hour_data": [round(v, 6) for v in hour_data],
        "avg_load_mw": round(sum(scaled) / len(scaled), 6),
        "max_load_mw": round(max(scaled), 6),
        "max_demand_mw": round(max_demand, 6),
        "max_demand_period": period,
    }


@router.get("/params/pv")
def get_pv_params():
    params = ConfigLoader.load_pv_defaults("henan")
    # 返回 {region: [curve_types]} 格式
    pv_dir = DATA_DIR / "pv_curves"
    curves = {}
    if pv_dir.exists():
        for region_dir in sorted(pv_dir.iterdir()):
            if region_dir.is_dir() and region_dir.name != "custom":
                curves[region_dir.name] = [f.stem for f in sorted(region_dir.glob("*.csv"))]
    curve_data = ConfigLoader.load_pv_curve(
        params.get("region", "henan"),
        params.get("curve_type", "annual_avg"),
    )
    return {"params": params, "curves": curves, "curve_data": curve_data}


@router.put("/params/pv")
def update_pv_params(req: dict):
    ConfigLoader.save_pv_defaults(req)
    return {"status": "ok"}


@router.get("/params/spot-prices")
def get_spot_prices():
    """返回现货电价数据（日前/实时/价差）。"""
    spot_dir = DATA_DIR / "spot_price" / "henan"
    files = sorted(spot_dir.glob("*.csv"))
    if not files:
        return {"day_ahead": [0.0]*24, "real_time": [0.0]*24}
    # 读取最新月份文件
    df = pd.read_csv(files[-1], dtype={"date": str}, comment='#')
    latest_date = df["date"].max()
    day = df[df["date"] == latest_date].sort_values("hour")
    if len(day) != 24:
        return {"day_ahead": [0.0]*24, "real_time": [0.0]*24}
    da = [round(float(v)/1000, 4) for v in day["day_ahead"].tolist()]
    rt = [round(float(v)/1000, 4) for v in day["real_time"].tolist()]
    return {"day_ahead": da, "real_time": rt, "date": str(latest_date)}


@router.get("/params/pv-curve/{region}/{curve_type}")
def get_pv_curve(region: str, curve_type: str):
    data = ConfigLoader.load_pv_curve(region, curve_type)
    return {"region": region, "curve_type": curve_type, "data": data}


@router.get("/algorithms")
def list_algorithms():
    from src.core.registry import list_algorithms as _list
    return _list()


def _safe_csv_summary(path: Path) -> dict:
    try:
        df = pd.read_csv(path, comment="#", nrows=50, encoding="utf-8-sig")
        cols = list(df.columns)
        row_count = sum(1 for _ in open(path, "r", encoding="utf-8", errors="ignore")) - 1
    except Exception:
        cols = []
        row_count = 0
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "name": path.name,
        "columns": cols,
        "rows": max(row_count, 0),
        "size_kb": round(path.stat().st_size / 1024, 1),
    }


def _safe_model_param_path(model_id: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", model_id):
        raise HTTPException(400, "非法模型 ID")
    return DATA_DIR / "model_params" / f"{model_id}.json"


def _model_param_draft(model_id: str) -> dict:
    path = _safe_model_param_path(model_id)
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else {}


def _apply_model_draft(model: dict) -> dict:
    draft = _model_param_draft(str(model.get("id", "")))
    for param in model.get("params", []):
        if param.get("key") in draft:
            param["value"] = draft[param["key"]]
    model["draft_saved"] = bool(draft)
    return model


@router.get("/data-assets")
def list_data_assets():
    """按业务口径列出 data 目录中的核心数据资产。"""
    groups = [
        ("params", "全局参数", DATA_DIR / "params"),
        ("tariff", "分时电价", DATA_DIR / "tariff"),
        ("spot_price", "现货价格", DATA_DIR / "spot_price"),
        ("dispatch_load", "统调负荷", DATA_DIR / "dispatch_load"),
        ("load", "用户典型负荷", DATA_DIR / "load"),
        ("pv_curves", "光伏出力", DATA_DIR / "pv_curves"),
        ("trading_strategy", "交易策略持仓", DATA_DIR / "trading_strategy"),
        ("demand_capacity", "需量/容量单价", DATA_DIR / "demand_capacity"),
        ("catalog", "数据可信度", DATA_DIR / "catalog"),
    ]
    trust = []
    trust_path = DATA_DIR / "catalog" / "data_trust.csv"
    if trust_path.exists():
        trust = pd.read_csv(trust_path, comment="#").to_dict(orient="records")

    assets = []
    for key, label, root in groups:
        files = []
        if root.exists():
            files = [_safe_csv_summary(p) for p in sorted(root.rglob("*.csv"))[:80]]
        assets.append({
            "key": key,
            "label": label,
            "count": len(files),
            "files": files,
        })
    return {"groups": assets, "trust": trust}


@router.get("/models")
def list_models():
    """模型管理页数据：列出当前已实现/可配置/待接入模型。"""
    from src.core.registry import list_algorithms as _list_algorithms

    algorithms = _list_algorithms()
    if not algorithms:
        algorithms = [{
            "id": "optimize_arbitrage",
            "desc": "滑窗穷举套利调度（默认）：按有效价差寻找充放电窗口",
        }]

    data = {
        "categories": [
            {
                "key": "dispatch",
                "label": "调度模型",
                "models": [
                    {
                        "id": a["id"],
                        "name": a["id"],
                        "description": a.get("desc", ""),
                        "status": "已接入",
                        "params": [
                            {"key": "window_hours", "label": "搜索窗口", "value": 24, "unit": "h", "editable": True},
                            {"key": "min_spread", "label": "最小套利价差", "value": 0.0, "unit": "元/kWh", "editable": True},
                            {"key": "cycle_penalty", "label": "循环惩罚系数", "value": 0.0, "unit": "-", "editable": True},
                        ],
                    }
                    for a in algorithms
                ],
            },
            {
                "key": "pricing",
                "label": "零售电价模型",
                "models": [
                    {"id": k, "name": v, "description": "用户侧电价曲线生成模型", "status": "已接入", "params": []}
                    for k, v in PM_LABELS.items()
                ],
            },
            {
                "key": "business",
                "label": "商业模式/优化目标",
                "models": [
                    {"id": k, "name": v, "description": "决定储能调度目标与收益归属", "status": "已接入", "params": []}
                    for k, v in BM_LABELS.items()
                ],
            },
            {
                "key": "wholesale",
                "label": "批发侧结算模型",
                "models": [
                    {
                        "id": value,
                        "name": label,
                        "description": "中长期、日前、实时组合购电结算抽象",
                        "status": "简化接入",
                        "params": [
                            {"key": "time_granularity", "label": "时间粒度", "value": "1h", "unit": "", "editable": False},
                            {"key": "da_quantity_definition", "label": "日前电量口径", "value": "declaration", "unit": "", "editable": True},
                        ],
                    }
                    for value, label in UI_OPTION_LISTS["settlement_mode"]
                ],
            },
            {
                "key": "financial",
                "label": "投资评价模型",
                "models": [
                    {
                        "id": "irr_npv_payback",
                        "name": "IRR / NPV / 静态回收期",
                        "description": "储能与光伏投资收益评价，当前不考虑融资结构",
                        "status": "已接入",
                        "params": [
                            {"key": "r_discount", "label": "折现率", "value": ConfigLoader.load_financial_defaults("henan").get("r_discount", 0.06), "unit": "-", "editable": True}
                        ],
                    }
                ],
            },
        ]
    }
    for category in data["categories"]:
        category["models"] = [_apply_model_draft(model) for model in category["models"]]
    return data


@router.put("/models/{model_id}/params")
def update_model_params(model_id: str, req: dict):
    """保存模型超参草稿。当前先作为 mock 配置落盘，后续再接入算法。"""
    path = _safe_model_param_path(model_id)
    model_dir = path.parent
    model_dir.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(req, f, ensure_ascii=False, indent=2)
    return {"status": "ok", "model_id": model_id}


_HELP_DOCS = [
    {
        "id": "overview",
        "title": "系统总览",
        "category": "使用指南",
        "content": """# 系统总览

本系统用于模拟源网荷储售一体化场景下，不同电价模式、交易策略、储能/光伏参数和商业模式对收益的影响。

当前建议先使用“单方案分析”完成一个可信闭环，再进入“多方案对比”横向比较方案差异。""",
    },
    {
        "id": "single-scenario",
        "title": "单方案分析",
        "category": "使用指南",
        "content": """# 单方案分析

单方案分析页关注一个方案在典型日边界条件下的调度、收益和经济性。

关键区域包括：系统构成、商业模式、电价模式、运行参数、方案概览、多方收益、光储投资分析和典型日能量分析。""",
    },
    {
        "id": "compare",
        "title": "多方案对比",
        "category": "使用指南",
        "content": """# 多方案对比

多方案对比最多支持 4 个方案。横向卡片对应不同方案，纵向指标对应收益、成本、IRR、回收期、循环次数、光伏消纳率等关键指标。

指标中的高亮值代表在当前对比组内更优。""",
    },
    {
        "id": "data-trust",
        "title": "数据可信度",
        "category": "数据说明",
        "content": """# 数据可信度

数据可信度登记在 `data/catalog/data_trust.csv` 中。该文件只记录可信等级、是否 mock、适用范围和内部备注，不记录敏感来源细节。""",
    },
]


@router.get("/docs")
def list_docs():
    docs = [{"id": d["id"], "title": d["title"], "category": d["category"]} for d in _HELP_DOCS]
    for root, category in ((DOCS_DIR, "工程文档"), (PRD_DIR, "需求文档")):
        if root.exists():
            for path in sorted(root.glob("*.md"))[:40]:
                docs.append({
                    "id": f"file:{path.relative_to(ROOT).as_posix()}",
                    "title": path.stem,
                    "category": category,
                })
    return {"docs": docs}


@router.get("/docs/{doc_id:path}")
def get_doc(doc_id: str):
    for doc in _HELP_DOCS:
        if doc["id"] == doc_id:
            return doc
    if doc_id.startswith("file:"):
        rel = doc_id[5:]
        path = (ROOT / rel).resolve()
        if ROOT not in path.parents:
            raise HTTPException(400, "非法文档路径")
        if not path.exists() or path.suffix.lower() != ".md":
            raise HTTPException(404, "文档不存在")
        return {
            "id": doc_id,
            "title": path.stem,
            "category": "工程文档",
            "content": path.read_text(encoding="utf-8", errors="ignore"),
        }
    raise HTTPException(404, "文档不存在")


# ---------- 中长期量价曲线 ----------

# 分时电价时段定义（从 tariff_admin_henan.csv 提取）
_TOU_PERIODS = [
    {"period": "valley", "start": 0, "end": 8, "price": 0.28},
    {"period": "peak",   "start": 8, "end": 12, "price": 0.95},
    {"period": "flat",   "start": 12, "end": 17, "price": 0.58},
    {"period": "peak",   "start": 17, "end": 21, "price": 0.95},
    {"period": "flat",   "start": 21, "end": 24, "price": 0.58},
]

# 预设电价曲线
_TARIFF_CURVES = {
    "typical": [
        {"period": "valley", "start": 0, "end": 8, "price": 0.28},
        {"period": "peak",   "start": 8, "end": 12, "price": 0.95},
        {"period": "flat",   "start": 12, "end": 17, "price": 0.58},
        {"period": "peak",   "start": 17, "end": 21, "price": 0.95},
        {"period": "flat",   "start": 21, "end": 24, "price": 0.58},
    ],
    "midday_valley": [
        {"period": "valley",      "start": 0, "end": 6, "price": 0.25},
        {"period": "flat",        "start": 6, "end": 9, "price": 0.50},
        {"period": "peak",        "start": 9, "end": 12, "price": 0.90},
        {"period": "deep_valley", "start": 12, "end": 15, "price": 0.15},
        {"period": "flat",        "start": 15, "end": 18, "price": 0.50},
        {"period": "peak",        "start": 18, "end": 22, "price": 0.90},
        {"period": "valley",      "start": 22, "end": 24, "price": 0.25},
    ],
    "summer_peak": [
        {"period": "valley",     "start": 0, "end": 6, "price": 0.30},
        {"period": "flat",       "start": 6, "end": 8, "price": 0.55},
        {"period": "peak",       "start": 8, "end": 11, "price": 0.95},
        {"period": "super_peak", "start": 11, "end": 14, "price": 1.20},
        {"period": "flat",       "start": 14, "end": 17, "price": 0.55},
        {"period": "peak",       "start": 17, "end": 21, "price": 0.95},
        {"period": "valley",     "start": 21, "end": 24, "price": 0.30},
    ],
}


def _get_tou_hour_prices(tariff_curve: str = "typical") -> list[float]:
    """返回 24 小时的分时电价（元/kWh）。"""
    periods = _TARIFF_CURVES.get(tariff_curve, _TOU_PERIODS)
    prices = [0.0] * 24
    for p in periods:
        for h in range(p["start"], p["end"]):
            prices[h] = p["price"]
    return prices


# ---------- 行政分时电价（全国） ----------

@router.get("/tariff/administrative/provinces")
def list_tariff_provinces():
    """返回可用的省份列表。"""
    tou_dir = DATA_DIR / "tariff" / "administrative_tariff"
    if not tou_dir.exists():
        return []
    return sorted([d.name for d in tou_dir.iterdir() if d.is_dir()])


@router.get("/tariff/administrative/months/{province}")
def list_tariff_months(province: str):
    """返回指定省份可用的月份列表。"""
    prov_dir = DATA_DIR / "tariff" / "administrative_tariff" / province
    if not prov_dir.exists():
        raise HTTPException(404, f"省份 {province} 不存在")
    months = set()
    for f in prov_dir.glob("*.csv"):
        name = f.stem  # e.g. "202606_commercial"
        ym = name.split("_")[0]
        if ym.isdigit() and len(ym) == 6:
            months.add(ym)
    return sorted(months, reverse=True)


@router.get("/tariff/administrative/business-types/{province}/{month}")
def list_tariff_business_types(province: str, month: str):
    """返回指定省份/月份可用的用电类别列表。"""
    prov_dir = DATA_DIR / "tariff" / "administrative_tariff" / province
    if not prov_dir.exists():
        raise HTTPException(404, f"省份 {province} 不存在")
    types = []
    for f in sorted(prov_dir.glob(f"{month}_*.csv")):
        name = f.stem  # e.g. "202606_commercial"
        bt = name.split("_", 1)[1] if "_" in name else name
        types.append(bt)
    return types


@router.get("/tariff/administrative/data/{province}/{month}/{business_type}")
def get_tariff_data(province: str, month: str, business_type: str):
    """返回指定条件的分时电价数据。"""
    prov_dir = DATA_DIR / "tariff" / "administrative_tariff" / province
    if not prov_dir.exists():
        raise HTTPException(404, f"省份 {province} 不存在")

    # 查找匹配的文件
    target = f"{month}_{business_type}"
    matched = None
    for f in prov_dir.glob(f"{target}*.csv"):
        matched = f
        break
    if not matched:
        # 模糊匹配
        for f in prov_dir.glob(f"{month}_*.csv"):
            if business_type in f.stem:
                matched = f
                break
    if not matched:
        raise HTTPException(404, f"未找到 {province}/{month}/{business_type} 的电价数据")

    df = pd.read_csv(matched, comment='#', encoding='utf-8-sig')
    # 解析电压等级列（排除 hour 和 时段 列）
    voltage_cols = [c for c in df.columns if c not in ('hour', '时段')]
    # 处理 NaN 值（转换为 null，避免 JSON 序列化错误）
    import math
    records = []
    for _, row in df.iterrows():
        record = {}
        for col in df.columns:
            val = row[col]
            if pd.isna(val):
                record[col] = None
            elif isinstance(val, float) and (math.isinf(val) or math.isnan(val)):
                record[col] = None
            else:
                record[col] = val
        records.append(record)
    return {
        "province": province,
        "month": month,
        "business_type": business_type,
        "file": matched.name,
        "voltage_levels": voltage_cols,
        "data": records,
    }


def _get_dispatch_load(region: str = "henan") -> list[float]:
    """加载统调负荷曲线（MW）。"""
    try:
        return ConfigLoader.load_dispatch_load(region)
    except FileNotFoundError:
        return [3000.0] * 24


def decompose_contract(
    total_mwh: float,
    curve_type: str,
    tariff_curve: str = "typical",
) -> list[float]:
    """将合约电量按分解曲线分配到 24 小时。

    Args:
        total_mwh: 合约总电量（MWh）
        curve_type: 分解曲线类型
        tariff_curve: 标的分时电价曲线

    Returns:
        24 元素列表，每小时合约电量（MWh）
    """
    if curve_type == "load":
        load = _get_dispatch_load()
        total_load = sum(load)
        if total_load == 0:
            return [total_mwh / 24] * 24
        return [total_mwh * v / total_load for v in load]

    prices = _get_tou_hour_prices(tariff_curve)

    if curve_type == "D2":
        # 平均分配
        return [total_mwh / 24] * 24

    if curve_type in ("D1", "D3", "D4", "D5"):
        # 按价格加权分配（仅在指定时段内）
        if curve_type == "D1":
            # 峰平谷：所有时段按价格加权
            weights = prices
        elif curve_type == "D3":
            # 高峰（含尖峰）：仅峰段
            weights = [prices[h] if prices[h] >= 0.9 else 0 for h in range(24)]
        elif curve_type == "D4":
            # 平段：仅平段
            weights = [prices[h] if 0.5 < prices[h] < 0.9 else 0 for h in range(24)]
        else:
            # 谷段（含深谷）：仅谷段
            weights = [prices[h] if prices[h] <= 0.3 else 0 for h in range(24)]

        total_weight = sum(weights)
        if total_weight == 0:
            return [0.0] * 24
        return [total_mwh * w / total_weight for w in weights]

    return [total_mwh / 24] * 24


@router.get("/params/contract-curve")
def get_contract_curve(
    total_mwh: float = 80.0,
    curve_type: str = "D1",
    tariff_curve: str = "typical",
):
    """返回合约电量 24 小时分解结果。"""
    data = decompose_contract(total_mwh, curve_type, tariff_curve)
    tou_prices = _get_tou_hour_prices(tariff_curve)
    return {
        "total_mwh": total_mwh,
        "curve_type": curve_type,
        "hourly_mwh": [round(v, 4) for v in data],
        "tou_prices": tou_prices,
    }
