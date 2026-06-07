"""售电公司批发市场购电结算配置（文档第五章统一数据对象与结算模式）。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class MarketRegionCode(str, Enum):
    """电力市场区域代码（仿真配置用，可与负荷/电价 region 独立）。"""

    CN = "CN"
    GD = "GD"
    GX = "GX"
    SX = "SX"
    SD = "SD"


class SettlementMode(str, Enum):
    """批发侧电能量结算模式。"""

    GUANGDONG_STYLE = "GUANGDONG_STYLE"
    GUANGXI_STYLE = "GUANGXI_STYLE"
    SHANXI_STYLE = "SHANXI_STYLE"
    SHANDONG_TBD = "SHANDONG_TBD"


class TimeGranularity(str, Enum):
    """时间粒度（当前引擎仅实现 24 点即 1h 等效）。"""

    H1 = "1h"
    MIN15 = "15min"


class DaQuantityDefinition(str, Enum):
    """日前偏差结算所用的日前电量口径。"""

    DECLARATION = "declaration"
    CLEARED = "cleared"


@dataclass(frozen=True)
class WholesaleSettlementConfig:
    """第五章表 5.1 数据对象 + 表 5.4 仿真配置项。

    电量电价序列仍来自 CSV（合约/日前/现货），此处为全局结算规则开关。
    """

    market_region_code: MarketRegionCode = MarketRegionCode.CN
    settlement_mode: SettlementMode = SettlementMode.GUANGDONG_STYLE
    time_granularity: TimeGranularity = TimeGranularity.H1
    da_quantity_definition: DaQuantityDefinition = DaQuantityDefinition.DECLARATION
    contract_curve_profile: str = "mock_henan"
    dayahead_curve_profile: str = "mock_henan"
    purchase_monthly_constant_yuan: float = 0.0
    guangxi_month_smooth_yuan: float = 0.0
    shanxi_wholesale_addon_yuan: float = 0.0

    @staticmethod
    def from_flat_dict(d: dict[str, str | float]) -> "WholesaleSettlementConfig":
        """从 wholesale_settlement_defaults.csv 行字典解析。"""
        return WholesaleSettlementConfig(
            market_region_code=MarketRegionCode(str(d.get("market_region_code", "CN"))),
            settlement_mode=SettlementMode(str(d.get("settlement_mode", "GUANGDONG_STYLE"))),
            time_granularity=TimeGranularity(str(d.get("time_granularity", "1h"))),
            da_quantity_definition=DaQuantityDefinition(
                str(d.get("da_quantity_definition", "declaration"))
            ),
            contract_curve_profile=str(d.get("contract_curve_profile", "mock_henan")),
            dayahead_curve_profile=str(d.get("dayahead_curve_profile", "mock_henan")),
            purchase_monthly_constant_yuan=float(d.get("purchase_monthly_constant_yuan", 0.0)),
            guangxi_month_smooth_yuan=float(d.get("guangxi_month_smooth_yuan", 0.0)),
            shanxi_wholesale_addon_yuan=float(d.get("shanxi_wholesale_addon_yuan", 0.0)),
        )

    def to_flat_dict(self) -> dict[str, str | float]:
        return {
            "market_region_code": self.market_region_code.value,
            "settlement_mode": self.settlement_mode.value,
            "time_granularity": self.time_granularity.value,
            "da_quantity_definition": self.da_quantity_definition.value,
            "contract_curve_profile": self.contract_curve_profile,
            "dayahead_curve_profile": self.dayahead_curve_profile,
            "purchase_monthly_constant_yuan": self.purchase_monthly_constant_yuan,
            "guangxi_month_smooth_yuan": self.guangxi_month_smooth_yuan,
            "shanxi_wholesale_addon_yuan": self.shanxi_wholesale_addon_yuan,
        }


# 配置页下拉：每项暂只维护一个可选项，便于后续追加
UI_OPTION_LISTS: dict[str, list[tuple[str, str]]] = {
    "market_region_code": [("CN", "全国（示范）")],
    "settlement_mode": [("GUANGDONG_STYLE", "广东型三部制")],
    "time_granularity": [("1h", "1 小时（24 点）")],
    "da_quantity_definition": [("declaration", "日前申报量")],
    "contract_curve_profile": [("mock_henan", "交易策略：合约电量/电价/P_ref")],
    "dayahead_curve_profile": [("mock_henan", "河南示范：日前申报/出清电量")],
}
