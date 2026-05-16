"""调度相关数据模型。"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class PricingMode(str, Enum):
    M1_ADMIN_TOU = "M1"
    M2_JIANGSU = "M2"
    M3_CONTRACT_TOU = "M3"
    M4_SPOT_LINKED = "M4"
    M5_FLAT = "M5"


class BusinessModel(str, Enum):
    B1_USER_ESS = "B1"
    B2A_RETAILER = "B2a"
    B2B_ESS = "B2b"
    B2C_USER = "B2c"
    B3A_COMBINED = "B3a"
    B3B_USER = "B3b"
    B4_UNIFIED = "B4"


@dataclass
class ESSParams:
    """储能系统参数。"""
    cap_rated: float = 5000          # kWh
    c_rate: float = 0.5               # 倍率
    eta_roundtrip: float = 0.85       # 往返效率
    soc_min: float = 0.10             # SOC 下限
    soc_max: float = 0.90             # SOC 上限
    unit_cost: float = 0.9            # 元/Wh
    r_om: float = 0.01                # 年运维比例
    design_life: int = 10             # 年
    r_degrade: float = 0.025          # 年衰减率

    @property
    def max_power(self) -> float:
        return self.cap_rated * self.c_rate

    @property
    def eta_single(self) -> float:
        return self.eta_roundtrip ** 0.5

    @property
    def initial_investment(self) -> float:
        return self.cap_rated * self.unit_cost * 1000  # 元（Wh→kWh: ×1000）


@dataclass
class FinancialParams:
    """财务参数。"""
    r_discount: float = 0.06          # 折现率
    r_user: float = 0.30              # 用户分成比例


@dataclass
class HourlyData:
    """单小时输入数据。"""
    hour: int                         # 0..23
    load_real: float                  # kWh, 用户真实负荷
    P_user: float                     # 元/kWh, 用户侧电价
    P_da: float                       # 元/kWh, 日前电价
    P_rt: float                       # 元/kWh, 实时电价
    Q_contract: float                 # kWh, 中长期合约量
    P_contract: float                 # 元/kWh, 中长期合约价
    Q_dayahead: float                 # kWh, 日前申报量


@dataclass
class DispatchResult:
    """调度结果。"""
    load_ESS: list[float] = field(default_factory=lambda: [0.0] * 24)   # kWh
    SOC: list[float] = field(default_factory=lambda: [0.0] * 24)         # 0..1
    load_grid: list[float] = field(default_factory=lambda: [0.0] * 24)   # kWh

    # 收益分解
    user_bill_no_ess: float = 0.0
    user_bill_with_ess: float = 0.0
    user_savings: float = 0.0
    user_net: float = 0.0

    retail_revenue: float = 0.0
    purchase_cost: float = 0.0
    C_mlt: float = 0.0
    C_da: float = 0.0
    C_rt: float = 0.0
    retail_profit: float = 0.0

    ess_revenue: float = 0.0
    ess_net_annual: float = 0.0

    combined_profit: float = 0.0
    total_welfare: float = 0.0

    # 投资指标
    irr: float = 0.0
    npv: float = 0.0
    payback_years: float = 0.0
    equivalent_cycles: float = 0.0
    daily_arbitrage: float = 0.0
