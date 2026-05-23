"""电价模式计算。

根据五种电价模式 (M1~M5) 计算 24 小时用户侧电价 P_user[t]。
"""
from typing import Optional
import numpy as np
import pandas as pd
from src.models.dispatch import PricingMode


def lookup_tou(tariff_df: pd.DataFrame, hour: int) -> float:
    """从分时电价表中查询某小时的电价。

    tariff_df 列: period, start_hour, end_hour, price_yuan_per_kwh
    start 到 end-1 为有效小时。
    """
    for _, row in tariff_df.iterrows():
        start = int(row['start_hour'])
        end = int(row['end_hour'])
        if start <= hour < end:
            return float(row['price_yuan_per_kwh'])
    raise ValueError(f"未找到 hour={hour} 的电价，请检查电价表是否覆盖 0~23 小时")


def _jiangsu_coefficient(admin_tariff: pd.DataFrame, hour: int, cfg: dict) -> float:
    """根据 M1 时段划分查 M2 系数。"""
    period_map = {
        'valley': cfg['coefficient_valley'],
        'peak': cfg['coefficient_peak'],
        'flat': cfg['coefficient_flat'],
    }
    for _, row in admin_tariff.iterrows():
        start = int(row['start_hour'])
        end = int(row['end_hour'])
        if start <= hour < end:
            period = row['period']
            return float(period_map.get(period, 1.0))
    raise ValueError(f"未找到 hour={hour} 的时段划分")


def compute_user_price(
    mode: PricingMode,
    tariffs: dict,
    P_da: Optional[list[float]] = None,
) -> list[float]:
    """根据电价模式计算 24 小时 P_user。

    Args:
        mode: 电价模式 M1~M5
        tariffs: 从 config CSV 加载的电价表字典
            - 'admin': M1 行政分时电价表 DataFrame
            - 'jiangsu': M2 江苏模式参数字典
            - 'contract': M3 合同分时电价表 DataFrame
            - 'flat_price': M5 一口价 (float)
        P_da: 全月日前电价列表 (元/kWh)，M4 模式必需。长度为 31×24 或 (月天数)×24。

    Returns:
        24 元素 P_user[t] 列表 (元/kWh)
    """
    if mode == PricingMode.M1_ADMIN_TOU:
        return [lookup_tou(tariffs['admin'], h) for h in range(24)]

    elif mode == PricingMode.M2_JIANGSU:
        cfg = tariffs['jiangsu']
        p_base = float(cfg['p_base'])
        admin = tariffs['admin']
        return [p_base * _jiangsu_coefficient(admin, h, cfg) for h in range(24)]

    elif mode == PricingMode.M3_CONTRACT_TOU:
        return [lookup_tou(tariffs['contract'], h) for h in range(24)]

    elif mode == PricingMode.M4_SPOT_LINKED:
        if P_da is None:
            raise ValueError("M4 现货联动模式需要提供 P_da 数据")
        # P_da 为 月天数 × 24 小时 的扁平列表
        n_days = len(P_da) // 24
        arr = np.array(P_da).reshape(n_days, 24)
        return arr.mean(axis=0).tolist()

    elif mode == PricingMode.M5_FLAT:
        p_flat = tariffs.get('flat_price')
        if p_flat is None:
            raise ValueError("M5 一口价模式需要 tariffs['flat_price']")
        return [float(p_flat)] * 24

    raise ValueError(f"未知电价模式: {mode}")
