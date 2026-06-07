"""全局单位注册表。所有数据文件的单位在此集中记录。"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict


class Unit(str, Enum):
    """常用单位枚举。"""
    # 功率
    W = "W"
    KW = "kW"
    MW = "MW"
    GW = "GW"
    # 能量
    WH = "Wh"
    KWH = "kWh"
    MWH = "MWh"
    # 价格
    YUAN_PER_KWH = "元/kWh"
    YUAN_PER_MWH = "元/MWh"
    # 其他
    PERCENT = "%"
    DIMENSIONLESS = "-"


@dataclass(frozen=True)
class FieldMeta:
    """字段元数据：名称、中文描述、单位。"""
    name: str
    description: str
    unit: Unit


@dataclass
class UnitRegistry:
    """全局单位注册表，记录每个数据集中每个字段的单位。"""
    datasets: Dict[str, Dict[str, FieldMeta]] = field(default_factory=dict)

    def register(self, dataset: str, field: str, description: str, unit: Unit) -> None:
        if dataset not in self.datasets:
            self.datasets[dataset] = {}
        self.datasets[dataset][field] = FieldMeta(name=field, description=description, unit=unit)

    def get(self, dataset: str, field: str) -> FieldMeta | None:
        return self.datasets.get(dataset, {}).get(field)

    def list_datasets(self) -> list[str]:
        return list(self.datasets.keys())

    def list_fields(self, dataset: str) -> Dict[str, FieldMeta]:
        return self.datasets.get(dataset, {})


# 全局单例
REGISTRY = UnitRegistry()

# ---- 负荷数据 ----
REGISTRY.register("load_henan", "Load_real", "实际负荷（扣除储能后）", Unit.KWH)
REGISTRY.register("load_henan", "date", "日期", Unit.DIMENSIONLESS)
REGISTRY.register("load_henan", "hour", "小时（0~23）", Unit.DIMENSIONLESS)
REGISTRY.register("load_henan", "source", "数据来源地区", Unit.DIMENSIONLESS)

# ---- 现货电价数据 ----
REGISTRY.register("spot_price_henan", "day_ahead", "日前统一出清价", Unit.YUAN_PER_MWH)
REGISTRY.register("spot_price_henan", "real_time", "实时统一出清价", Unit.YUAN_PER_MWH)
REGISTRY.register("spot_price_henan", "date", "日期", Unit.DIMENSIONLESS)
REGISTRY.register("spot_price_henan", "hour", "小时（0~23）", Unit.DIMENSIONLESS)
REGISTRY.register("spot_price_henan", "source", "数据可信度/来源类型", Unit.DIMENSIONLESS)
