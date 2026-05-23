"""共享计算器 — 统一的调度计算入口，避免页面间代码重复。"""

from src.data.scenario import ScenarioConfig
from src.data.loader import DataLoader
from src.data.config import ConfigLoader
from src.core.pricing import compute_user_price
from src.core.dispatch import run_dispatch
from src.models.dispatch import BusinessModel, PricingMode, FinancialParams


def calculate(config: ScenarioConfig):
    """执行完整调度计算并返回 DispatchResult。"""
    region = config.region
    date = config.selected_date

    P_da, P_rt = DataLoader.load_spot_prices(region, date)
    ct = ConfigLoader.load_contract_position(region, date)
    da = ConfigLoader.load_dayahead_position(region, date)
    Q_contract = [float(ct[ct["hour"] == h]["q_contract_kwh"].iloc[0]) for h in range(24)]
    P_contract = [float(ct[ct["hour"] == h]["p_contract_yuan_per_kwh"].iloc[0]) for h in range(24)]
    Q_dayahead = [float(da[da["hour"] == h]["q_dayahead_kwh"].iloc[0]) for h in range(24)]

    tariffs = {
        "admin": ConfigLoader.load_tariff(region, "admin"),
        "jiangsu": ConfigLoader.load_tariff(region, "jiangsu"),
        "contract": ConfigLoader.load_tariff(region, "contract"),
        "flat_price": 0.55,
    }
    P_user = compute_user_price(PricingMode(config.pricing_mode), tariffs,
                                 DataLoader.get_monthly_pda(region))

    hourly = DataLoader.load_processed_load(region, date, P_da, P_rt,
                                             Q_contract, P_contract, Q_dayahead)
    for i, h in enumerate(hourly):
        h.P_user = P_user[i]

    fin_defaults = ConfigLoader.load_financial_defaults(region)
    r_user_map = {"B1": float(fin_defaults["r_user_b1"]),
                  "B2": float(fin_defaults["r_user_b2"]),
                  "B3": float(fin_defaults["r_user_b3"])}
    bm_code = config.business_model
    bm_prefix = "B1" if bm_code == "B1" else ("B2" if bm_code.startswith("B2") else ("B3" if bm_code.startswith("B3") else "B2"))

    return run_dispatch(
        hourly,
        BusinessModel(bm_code),
        PricingMode(config.pricing_mode),
        ConfigLoader.load_ess_defaults(region),
        FinancialParams(
            r_discount=float(fin_defaults.get("r_discount", 0.06)),
            r_user=r_user_map.get(bm_prefix, 0.30),
        ),
    )
