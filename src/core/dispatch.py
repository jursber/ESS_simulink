"""统一储能调度优化算法。

通过推导"有效价格信号 P_eff"，将全部商业模式 (B1~B4) 的调度优化
统一为同一个问题：max Σ(load_ESS[t] × P_eff[t])，受物理约束。
"""

import math
from typing import List, Tuple, Optional

from src.core.registry import register_algorithm
from src.models.dispatch import (
    ESSParams, PVParams, FinancialParams, HourlyData, DispatchResult,
    BusinessModel, PricingMode,
)
from src.models.wholesale import WholesaleSettlementConfig
from src.core.wholesale_settlement import compute_wholesale_purchase_cost


def compute_effective_price(
    bm: BusinessModel,
    P_user: List[float],
    P_TOU: List[float],
    P_rt: List[float],
    r_user: float,
) -> List[float]:
    """推导优化目标下的有效价格信号。

    对于最大化目标 max Σ(load_ESS[t] × P_eff[t])：
      - P_eff[t] > 0 的小时倾向于放电
      - P_eff[t] < 0 的小时倾向于充电
      - |P_eff[t]| 越大，该小时在排序中优先级越高
    """
    P_eff = [0.0] * 24

    if bm == BusinessModel.B1_USER_ESS:
        # 用户+储能，行政分时：套利 = 谷充峰放
        # 只取正值部分作为放电激励，负值表示充电成本低
        for h in range(24):
            P_eff[h] = P_TOU[h]

    elif bm == BusinessModel.B2A_RETAILER:
        # 售电公司最优：P_eff = P_rt - P_user
        for h in range(24):
            P_eff[h] = P_rt[h] - P_user[h]

    elif bm in (BusinessModel.B2B_ESS, BusinessModel.B2C_USER, BusinessModel.B3B_USER):
        # 储能运营商或用户最优：套利基于用户侧电价
        for h in range(24):
            P_eff[h] = P_user[h]

    elif bm == BusinessModel.B3A_COMBINED:
        # 储售一体：P_eff = P_rt - r_user × P_user
        for h in range(24):
            P_eff[h] = P_rt[h] - r_user * P_user[h]

    elif bm == BusinessModel.B4_UNIFIED:
        # 社会总福利：P_eff = P_rt
        for h in range(24):
            P_eff[h] = P_rt[h]

    return P_eff


def simulate_sequential(
    hours_charge: List[int],
    hours_discharge: List[int],
    P_max: float,
    cap_rated: float,
    eta_single: float,
    soc_initial: float,
    soc_min: float,
    soc_max: float,
) -> Tuple[List[float], List[float]]:
    """按 0→23 逐时顺序模拟，返回 (load_ESS, SOC)。

    约束：
      - |load_ESS| ≤ P_max
      - SOC ∈ [soc_min, soc_max]
      - 充放电互斥
      - 充电时：SOC 上升 = |load_ESS| × eta_single / cap_rated
      - 放电时：SOC 下降 = load_ESS / eta_single / cap_rated
    """
    load_ESS = [0.0] * 24
    SOC = [0.0] * 24
    soc = soc_initial

    charge_set = set(hours_charge)
    discharge_set = set(hours_discharge)

    for h in range(24):
        if h in charge_set and h not in discharge_set and soc < soc_max - 1e-9:
            # 充电
            max_energy = min(
                P_max,
                (soc_max - soc) * cap_rated / eta_single
            )
            if max_energy > 1e-6:
                load_ESS[h] = -max_energy
                soc += max_energy * eta_single / cap_rated

        elif h in discharge_set and h not in charge_set and soc > soc_min + 1e-9:
            # 放电
            max_energy = min(
                P_max,
                (soc - soc_min) * cap_rated * eta_single
            )
            if max_energy > 1e-6:
                load_ESS[h] = max_energy
                soc -= max_energy / eta_single / cap_rated

        SOC[h] = soc

    return load_ESS, SOC


@register_algorithm("greedy_window", "贪心滑窗搜索（默认）——按价格排序后穷举充放电窗口组合")
def optimize_arbitrage(
    P_eff: List[float],
    params: ESSParams,
    soc_initial: float = 0.10,
    max_charge_hours: int = 6,
    max_discharge_hours: int = 6,
    pool_size: int = 12,
) -> Tuple[List[float], List[float], float]:
    """搜索最优充放电小时组合。

    按 P_eff 排序选出候选池（pool_size 个），再在池内用滑动窗口
    选取不同起点的 N 小时作为充/放电候选，确保时序多样性。
    """
    best_profit = -float("inf")
    best_load_ESS = [0.0] * 24
    best_SOC = [0.0] * 24

    sorted_asc = sorted(range(24), key=lambda h: P_eff[h])
    sorted_desc = sorted(range(24), key=lambda h: P_eff[h], reverse=True)

    charge_pool = sorted_asc[:pool_size]
    discharge_pool = sorted_desc[:pool_size]

    for n_charge in range(1, max_charge_hours + 1):
        for n_discharge in range(1, max_discharge_hours + 1):
            best_for_nm = -float("inf")
            best_ess_nm = None
            best_soc_nm = None

            # 滑动窗口：从 charge_pool 中选取连续 n_charge 个
            for ci in range(len(charge_pool) - n_charge + 1):
                c_set = set(charge_pool[ci:ci + n_charge])

                for di in range(len(discharge_pool) - n_discharge + 1):
                    d_set = set(discharge_pool[di:di + n_discharge])

                    if c_set & d_set:
                        continue

                    load_ESS, SOC = simulate_sequential(
                        hours_charge=list(c_set),
                        hours_discharge=list(d_set),
                        P_max=params.max_power,
                        cap_rated=params.cap_rated,
                        eta_single=params.eta_single,
                        soc_initial=soc_initial,
                        soc_min=params.soc_min,
                        soc_max=params.soc_max,
                    )

                    profit = sum(load_ESS[h] * P_eff[h] for h in range(24))

                    if profit > best_for_nm:
                        best_for_nm = profit
                        best_ess_nm = load_ESS
                        best_soc_nm = SOC

            if best_ess_nm is not None and best_for_nm > best_profit:
                best_profit = best_for_nm
                best_load_ESS = best_ess_nm
                best_SOC = best_soc_nm

    return best_load_ESS, best_SOC, best_profit


def run_dispatch(
    hourly: List[HourlyData],
    bm: BusinessModel,
    pricing: PricingMode,
    params: ESSParams,
    fin: FinancialParams,
    soc_initial: float = 0.10,
    wholesale_cfg: Optional[WholesaleSettlementConfig] = None,
    pv_params: Optional[PVParams] = None,
    pv_curve: Optional[List[float]] = None,
) -> DispatchResult:
    """执行完整调度计算。

    输入：24 小时数据、商业模式、电价模式、储能参数、财务参数。
    输出：完整的 DispatchResult，包含调度曲线和全部收益指标。

    Args:
        wholesale_cfg: 售电批发购电结算规则（第五章）；缺省为广东型三部制默认参数。
        pv_params: 光伏系统参数；None 表示无光伏。
        pv_curve: 光伏 24 小时归一化出力曲线 (0~1)；与 pv_params 配合使用。
    """
    n = len(hourly)
    assert n == 24, f"需要 24 小时数据，实际 {n} 小时"

    if wholesale_cfg is None:
        wholesale_cfg = WholesaleSettlementConfig()

    P_user = [d.P_user for d in hourly]
    P_da = [d.P_da for d in hourly]
    P_rt = [d.P_rt for d in hourly]
    P_TOU = [d.P_user for d in hourly]  # 用户侧电价即为 TOU
    load_real = [d.load_real for d in hourly]

    # 1. 计算有效价格信号
    P_eff = compute_effective_price(bm, P_user, P_TOU, P_rt, fin.r_user)

    # 2. 优化调度
    load_ESS, SOC, _ = optimize_arbitrage(
        P_eff, params, soc_initial=soc_initial,
    )

    # 3. 光伏发电计算
    has_pv = pv_params is not None and pv_curve is not None and pv_params.cap_rated > 0
    pv_generation = [0.0] * 24
    pv_self_consumed = [0.0] * 24
    pv_fed_in = [0.0] * 24

    if has_pv:
        for h in range(24):
            pv_gen = pv_params.cap_rated * pv_curve[h]
            pv_generation[h] = pv_gen
            # PV 自发自用：覆盖 ESS 调度后剩余的净负荷
            net_load_after_ess = load_real[h] - load_ESS[h]
            pv_self = min(pv_gen, max(0, net_load_after_ess))
            pv_self_consumed[h] = pv_self
            pv_fed_in[h] = pv_gen - pv_self

    # 4. 计算 load_grid（扣除储能和光伏自用）
    load_grid = [load_real[h] - load_ESS[h] - pv_self_consumed[h] for h in range(24)]

    result = DispatchResult()
    result.load_ESS = load_ESS
    result.SOC = SOC
    result.load_grid = load_grid

    # 4. 用户侧
    user_bill_no_ess = sum(load_real[h] * P_user[h] for h in range(24))
    user_bill_with_ess = sum(load_grid[h] * P_user[h] for h in range(24))
    savings = user_bill_no_ess - user_bill_with_ess

    result.user_bill_no_ess = user_bill_no_ess
    result.user_bill_with_ess = user_bill_with_ess
    result.user_savings = savings
    result.user_net = savings * fin.r_user

    # 5. 售电公司侧——仅含售电公司的模式才计算购电成本（统一批发结算引擎）
    has_retailer = bm not in (BusinessModel.B1_USER_ESS,)
    if has_retailer:
        P_da_list = [hourly[h].P_da for h in range(24)]
        P_rt_list = [hourly[h].P_rt for h in range(24)]
        bd = compute_wholesale_purchase_cost(
            hourly, load_grid, P_da_list, P_rt_list, wholesale_cfg
        )
        result.C_mlt = bd.C_mlt
        result.C_da = bd.C_da
        result.C_rt = bd.C_rt
        result.C_guangxi_month_smooth = bd.C_month_smooth
        result.C_purchase_monthly_constant = bd.C_monthly_constant
        result.C_shanxi_wholesale_addon = bd.C_shanxi_addon
        result.purchase_cost = bd.purchase_cost
        result.retail_revenue = user_bill_with_ess
        result.retail_profit = result.retail_revenue - result.purchase_cost

    # 6. 储能运营商侧
    result.ess_revenue = savings * (1 - fin.r_user)
    om_annual = params.initial_investment * params.r_om

    # 7. 组合收益
    result.combined_profit = result.retail_profit + result.ess_revenue if has_retailer else result.ess_revenue
    result.total_welfare = result.user_net + result.retail_profit + result.ess_revenue

    # 8. 投资指标（一天×365 放大）
    result.daily_arbitrage = sum(load_ESS[h] * P_eff[h] for h in range(24))
    total_investment = params.initial_investment

    # 根据优化目标选取年现金流口径
    annual_cashflow = _annual_cashflow(bm, result, om_annual)

    if annual_cashflow > 0:
        result.payback_years = total_investment / annual_cashflow
    else:
        result.payback_years = float("inf")

    result.npv = _npv(total_investment, annual_cashflow, params, fin)
    result.irr = _compute_irr(total_investment, annual_cashflow, params)

    result.ess_net_annual = result.ess_revenue * 365 - om_annual

    total_discharge = sum(max(0, load_ESS[h]) for h in range(24))
    result.equivalent_cycles = total_discharge / params.cap_rated

    # 9. 电价曲线（供前端图表使用）
    result.P_user_curve = P_user
    result.P_da_curve = P_da
    result.P_rt_curve = P_rt

    # 10. 光伏结果
    if has_pv:
        result.pv_generation = pv_generation
        result.pv_self_consumed = pv_self_consumed
        result.pv_fed_in = pv_fed_in
        result.pv_cap_kw = pv_params.cap_rated
        result.pv_total_gen_daily = sum(pv_generation)
        result.pv_self_daily = sum(pv_self_consumed[h] * P_user[h] for h in range(24))
        result.pv_feed_in_daily = sum(pv_fed_in[h] * pv_params.feed_in_tariff for h in range(24))
        total_gen = result.pv_total_gen_daily
        result.pv_self_rate = sum(pv_self_consumed) / total_gen if total_gen > 0 else 0

        # PV 投资指标（25 年期，含衰减）
        pv_om_annual = pv_params.initial_investment * pv_params.r_om
        pv_annual_revenue = (result.pv_self_daily + result.pv_feed_in_daily) * 365
        pv_annual_cf = pv_annual_revenue - pv_om_annual

        if pv_annual_cf > 0:
            result.pv_payback_years = pv_params.initial_investment / pv_annual_cf
        else:
            result.pv_payback_years = float("inf")

        result.pv_npv = _pv_npv(pv_params, pv_annual_cf, fin)
        result.pv_irr = _pv_irr(pv_params, pv_annual_cf)

    return result


def _annual_cashflow(bm: BusinessModel, result: DispatchResult, om_annual: float) -> float:
    """根据商业模式选取对应的年现金流口径（日值×365-年成本）。"""
    daily = 0.0
    if bm == BusinessModel.B1_USER_ESS:
        # 用户即储能投资商
        daily = result.ess_revenue
    elif bm in (BusinessModel.B2A_RETAILER, BusinessModel.B2B_ESS, BusinessModel.B2C_USER):
        # 三方独立：储能投资商始终收取 ess_revenue
        daily = result.ess_revenue
    elif bm in (BusinessModel.B3A_COMBINED, BusinessModel.B3B_USER):
        # 储售一体：组合体是储能投资商
        daily = result.combined_profit
    elif bm == BusinessModel.B4_UNIFIED:
        daily = result.combined_profit
    else:
        daily = result.combined_profit
    return daily * 365 - om_annual


def _npv(investment: float, annual_cf: float, params: ESSParams, fin: FinancialParams) -> float:
    """计算 10 年 NPV。"""
    npv = -investment
    for yr in range(1, params.design_life + 1):
        cap_eff = params.cap_rated * (1 - params.r_degrade) ** yr
        ratio = cap_eff / params.cap_rated
        npv += annual_cf * ratio / (1 + fin.r_discount) ** yr
    return npv


def _compute_irr(investment: float, annual_cf: float, params: ESSParams,
                 max_iter: int = 200, tol: float = 1e-6) -> float:
    """二分法求解 IRR。"""
    lo, hi = -0.5, 2.0
    for _ in range(max_iter):
        mid = (lo + hi) / 2
        npv = -investment
        for yr in range(1, params.design_life + 1):
            cap_eff = params.cap_rated * (1 - params.r_degrade) ** yr
            ratio = cap_eff / params.cap_rated
            npv += annual_cf * ratio / (1 + mid) ** yr
        if abs(npv) < tol:
            return mid
        if npv > 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def _pv_capacity_ratio(pv: PVParams, year: int) -> float:
    """光伏第 year 年的容量保持率（首年衰减率不同）。"""
    if year == 1:
        return 1 - pv.r_degrade_first
    return (1 - pv.r_degrade_first) * (1 - pv.r_degrade) ** (year - 1)


def _pv_npv(pv: PVParams, annual_cf: float, fin: FinancialParams) -> float:
    """光伏 25 年 NPV。"""
    npv = -pv.initial_investment
    for yr in range(1, pv.design_life + 1):
        ratio = _pv_capacity_ratio(pv, yr)
        npv += annual_cf * ratio / (1 + fin.r_discount) ** yr
    return npv


def _pv_irr(pv: PVParams, annual_cf: float,
            max_iter: int = 200, tol: float = 1e-6) -> float:
    """二分法求解光伏 IRR。"""
    lo, hi = -0.5, 2.0
    for _ in range(max_iter):
        mid = (lo + hi) / 2
        npv = -pv.initial_investment
        for yr in range(1, pv.design_life + 1):
            ratio = _pv_capacity_ratio(pv, yr)
            npv += annual_cf * ratio / (1 + mid) ** yr
        if abs(npv) < tol:
            return mid
        if npv > 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2
