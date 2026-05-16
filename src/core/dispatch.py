"""统一储能调度优化算法。

通过推导"有效价格信号 P_eff"，将全部商业模式 (B1~B4) 的调度优化
统一为同一个问题：max Σ(load_ESS[t] × P_eff[t])，受物理约束。
"""

import math
from typing import List, Tuple, Optional
from dataclasses import dataclass

from src.models.dispatch import (
    ESSParams, FinancialParams, HourlyData, DispatchResult,
    BusinessModel, PricingMode,
)


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
) -> DispatchResult:
    """执行完整调度计算。

    输入：24 小时数据、商业模式、电价模式、储能参数、财务参数。
    输出：完整的 DispatchResult，包含调度曲线和全部收益指标。
    """
    n = len(hourly)
    assert n == 24, f"需要 24 小时数据，实际 {n} 小时"

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

    # 3. 计算 load_grid
    load_grid = [load_real[h] - load_ESS[h] for h in range(24)]

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

    # 5. 售电公司侧——仅含售电公司的模式才计算购电成本
    has_retailer = bm not in (BusinessModel.B1_USER_ESS,)
    if has_retailer:
        C_mlt = sum(hourly[h].Q_contract * hourly[h].P_contract for h in range(24))
        C_da = sum((hourly[h].Q_dayahead - hourly[h].Q_contract) * P_da[h] for h in range(24))
        C_rt = sum((load_grid[h] - hourly[h].Q_dayahead) * P_rt[h] for h in range(24))
        result.C_mlt = C_mlt
        result.C_da = C_da
        result.C_rt = C_rt
        result.purchase_cost = C_mlt + C_da + C_rt
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
