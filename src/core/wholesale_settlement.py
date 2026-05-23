"""批发市场购电电费结算（文档第五章综合方案）。

单位与全项目一致：电量 kWh，电价 元/kWh，电费 元。

- GUANGDONG_STYLE:
    Σ_t [ Q_LT·P_LT + C_lt_block,t + (Q_DA−Q_LT)·P_DA + (Q_act−Q_DA)·P_RT ] + C̄
- GUANGXI_STYLE:
    Σ_t [ Q_LT·(P_LT + P_DA − P_ref) + (Q_DA−Q_LT)·P_DA + (Q_act−Q_DA)·P_RT ] + C_smooth + C̄
- SHANXI_STYLE:
    与广东型三部制数值一致 + 山西附加项（细则差价完整版可后续替换 f_shanxi_v16）。
- SHANDONG_TBD:
    暂等同 GUANGDONG_STYLE。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from src.models.dispatch import HourlyData
from src.models.wholesale import (
    DaQuantityDefinition,
    SettlementMode,
    WholesaleSettlementConfig,
)


@dataclass
class WholesalePurchaseBreakdown:
    """批发购电分项（元）。"""

    C_mlt: float
    C_da: float
    C_rt: float
    C_lt_block: float
    C_month_smooth: float
    C_monthly_constant: float
    C_shanxi_addon: float
    purchase_cost: float


def _q_da(h: HourlyData, definition: DaQuantityDefinition) -> float:
    if definition == DaQuantityDefinition.CLEARED and h.q_dayahead_cleared is not None:
        return float(h.q_dayahead_cleared)
    return float(h.Q_dayahead)


def compute_wholesale_purchase_cost(
    hourly: List[HourlyData],
    load_grid: List[float],
    P_da: List[float],
    P_rt: List[float],
    cfg: WholesaleSettlementConfig,
) -> WholesalePurchaseBreakdown:
    """按结算模式计算售电公司批发市场购电总成本与分解项。"""
    if len(hourly) != 24 or len(load_grid) != 24:
        raise ValueError("购电结算仅支持 24 时段")
    mode = cfg.settlement_mode
    if mode == SettlementMode.SHANDONG_TBD:
        mode = SettlementMode.GUANGDONG_STYLE

    C_lt_block = 0.0
    C_mlt_energy = 0.0
    C_da = 0.0
    C_rt = 0.0

    for t, h in enumerate(hourly):
        q_lt = float(h.Q_contract)
        p_lt = float(h.P_contract)
        p_ref = float(h.P_ref)
        q_act = float(load_grid[t])
        q_da = _q_da(h, cfg.da_quantity_definition)
        p_da = float(P_da[t])
        p_rt = float(P_rt[t])
        block = float(h.c_lt_block_yuan)

        if mode == SettlementMode.GUANGDONG_STYLE:
            C_mlt_energy += q_lt * p_lt
            C_lt_block += block
            C_da += (q_da - q_lt) * p_da
            C_rt += (q_act - q_da) * p_rt

        elif mode == SettlementMode.GUANGXI_STYLE:
            C_mlt_energy += q_lt * (p_lt + p_da - p_ref)
            C_lt_block += block
            C_da += (q_da - q_lt) * p_da
            C_rt += (q_act - q_da) * p_rt

        elif mode == SettlementMode.SHANXI_STYLE:
            # 购电侧暂用广东型三部制 + 可配置附加项；完整山西差价合约另建模
            C_mlt_energy += q_lt * p_lt
            C_lt_block += block
            C_da += (q_da - q_lt) * p_da
            C_rt += (q_act - q_da) * p_rt

        else:
            raise ValueError(f"未知结算模式: {cfg.settlement_mode}")

    C_month_smooth = (
        cfg.guangxi_month_smooth_yuan
        if cfg.settlement_mode == SettlementMode.GUANGXI_STYLE
        else 0.0
    )
    C_shanxi_addon = (
        cfg.shanxi_wholesale_addon_yuan
        if cfg.settlement_mode == SettlementMode.SHANXI_STYLE
        else 0.0
    )

    C_mlt = C_mlt_energy + C_lt_block
    C_bar = cfg.purchase_monthly_constant_yuan
    total = C_mlt + C_da + C_rt + C_month_smooth + C_bar + C_shanxi_addon

    return WholesalePurchaseBreakdown(
        C_mlt=C_mlt,
        C_da=C_da,
        C_rt=C_rt,
        C_lt_block=C_lt_block,
        C_month_smooth=C_month_smooth,
        C_monthly_constant=C_bar,
        C_shanxi_addon=C_shanxi_addon,
        purchase_cost=total,
    )
