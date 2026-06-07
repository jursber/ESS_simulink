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
    cap_rated: float = 1000           # kWh（显示为 MWh）
    power_rated: float = 0.5          # MW（额定功率）
    eta_roundtrip: float = 0.87       # 往返效率 RTE
    eta_charge: float = 0.92          # 单程充电效率 η
    soc_min: float = 0.10             # SOC 下限
    soc_max: float = 0.90             # SOC 上限
    design_life: int = 10             # 年
    r_degrade: float = 0.025          # 储能容量年衰减比例
    degrade_enabled: bool = False     # 启用年衰减
    cycle_life: int = 5000            # 储能循环次数（100% DoD）
    cycle_enabled: bool = False       # 启用循环次数约束
    unit_cost: float = 0.9            # 元/Wh（财务参数）
    r_om: float = 0.01                # 年运维支出比例（财务参数）
    r_ess_share: float = 0.20         # 储能收益分成比例

    @property
    def max_power(self) -> float:
        return self.power_rated * 1000  # MW → kW

    @property
    def eta_single(self) -> float:
        return self.eta_roundtrip ** 0.5

    @property
    def initial_investment(self) -> float:
        return self.cap_rated * self.unit_cost * 1000  # 元（Wh→kWh: ×1000）


@dataclass
class PVParams:
    """光伏系统参数。"""
    cap_rated: float = 1.0           # kWp
    feed_in_tariff: float = 0.4      # 元/kWh, 余电上网电价
    self_use_discount: float = 0.80  # 自用折扣系数
    unit_cost: float = 3.5           # 元/Wp
    r_om: float = 0.015              # 年运维支出比例
    design_life: int = 25            # 年
    r_degrade_first: float = 0.02    # 首年衰减率
    r_degrade: float = 0.005         # 后续年衰减率

    @property
    def initial_investment(self) -> float:
        return self.cap_rated * self.unit_cost * 1000  # kWp × 元/Wp × 1000 = 元


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
    Q_contract: float                 # kWh, 中长期净合约电量 Q_LT
    P_contract: float                 # 元/kWh, 中长期合约综合价 P_LT
    Q_dayahead: float                 # kWh, 日前申报电量（declaration 口径）
    P_ref: float = 0.0                # 元/kWh, 中长期结算参考点价格（广西等）
    q_dayahead_cleared: Optional[float] = None  # kWh, 日前出清电量；None 时与 Q_dayahead 相同


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
    C_guangxi_month_smooth: float = 0.0
    C_purchase_monthly_constant: float = 0.0
    C_shanxi_wholesale_addon: float = 0.0
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

    # 光伏
    pv_generation: list[float] = field(default_factory=lambda: [0.0] * 24)   # kWh, 每小时发电量
    pv_self_consumed: list[float] = field(default_factory=lambda: [0.0] * 24) # kWh, 自发自用
    pv_fed_in: list[float] = field(default_factory=lambda: [0.0] * 24)       # kWh, 余电上网
    pv_cap_kw: float = 0.0
    pv_total_gen_daily: float = 0.0    # kWh, 典型日总发电
    pv_self_daily: float = 0.0         # 元, 典型日自用收益
    pv_feed_in_daily: float = 0.0      # 元, 典型日上网收益
    pv_self_rate: float = 0.0          # 自用率
    pv_irr: float = 0.0
    pv_npv: float = 0.0
    pv_payback_years: float = 0.0

    # 电价曲线（用于前端图表）
    P_user_curve: list[float] = field(default_factory=lambda: [0.0] * 24)
    P_da_curve: list[float] = field(default_factory=lambda: [0.0] * 24)
    P_rt_curve: list[float] = field(default_factory=lambda: [0.0] * 24)
