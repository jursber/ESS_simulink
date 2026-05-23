"""数据加载器。

从处理后的 CSV 加载小时级数据，执行单位换算（元/MWh → 元/kWh），
组装为 HourlyData 对象供计算引擎使用。
"""
from pathlib import Path
from typing import Tuple, Optional

import pandas as pd

from src.models.dispatch import HourlyData

ROOT = Path(__file__).resolve().parent.parent.parent
LOAD_DIR = ROOT / "data" / "processed" / "load"
PRICE_DIR = ROOT / "data" / "processed" / "spot_price"


class DataLoader:
    """数据加载器。提供负荷、电价、合约数据的加载和组装。"""

    @staticmethod
    def get_available_dates(region: str) -> list[str]:
        """返回该地区有完整数据的日期列表。"""
        load_path = LOAD_DIR / f"load_{region}.csv"
        price_path = PRICE_DIR / f"price_{region}.csv"
        if not load_path.exists() or not price_path.exists():
            return []
        load_dates = set(pd.read_csv(load_path, dtype={"date": str})["date"].unique())
        price_dates = set(pd.read_csv(price_path, dtype={"date": str})["date"].unique())
        return sorted(load_dates & price_dates)

    @staticmethod
    def load_spot_prices(region: str, date: str) -> Tuple[list[float], list[float]]:
        """加载指定日期的日前和实时电价。

        Returns:
            (P_da, P_rt): 各 24 元素的电价列表 (元/kWh)
        """
        price_path = PRICE_DIR / f"price_{region}.csv"
        if not price_path.exists():
            raise ValueError(f"未找到电价数据: {price_path}")

        df = pd.read_csv(price_path, dtype={"date": str, "hour": int})
        day = df[df["date"] == date].sort_values("hour")
        if len(day) != 24:
            raise ValueError(f"日期 {date} 在 {price_path} 中未找到 24 小时数据（实际 {len(day)} 行）")

        P_da = (day["day_ahead"] / 1000.0).tolist()
        P_rt = (day["real_time"] / 1000.0).tolist()
        return P_da, P_rt

    @staticmethod
    def load_processed_load(
        region: str,
        date: str,
        P_da: list[float],
        P_rt: list[float],
        Q_contract: list[float],
        P_contract: list[float],
        Q_dayahead: list[float],
        P_ref: Optional[list[float]] = None,
        q_dayahead_cleared: Optional[list[float]] = None,
        c_lt_block_yuan: Optional[list[float]] = None,
    ) -> list[HourlyData]:
        """加载指定日期的处理后的负荷数据，组装为 HourlyData 列表。

        Args:
            region: 地区标识
            date: 日期 (YYYY-MM-DD)
            P_da: 日前电价 (元/kWh), 24 元素
            P_rt: 实时电价 (元/kWh), 24 元素
            Q_contract: 合约电量 (kWh), 24 元素
            P_contract: 合约电价 (元/kWh), 24 元素
            Q_dayahead: 日前申报电量 (kWh), 24 元素
            P_ref: 中长期结算参考点电价 (元/kWh)，缺省为 24 个 0
            q_dayahead_cleared: 日前出清电量；缺省为 None（表示与 Q_dayahead 相同）
            c_lt_block_yuan: 各时段中长期阻塞等附加电费 (元)；缺省为 0
        """
        for name, arr in [("P_da", P_da), ("P_rt", P_rt), ("Q_contract", Q_contract),
                          ("P_contract", P_contract), ("Q_dayahead", Q_dayahead)]:
            if len(arr) != 24:
                raise ValueError(f"{name} 必须为 24 元素，实际 {len(arr)}")
        if P_ref is None:
            P_ref = [0.0] * 24
        elif len(P_ref) != 24:
            raise ValueError("P_ref 必须为 24 元素或 None")
        if c_lt_block_yuan is None:
            c_lt_block_yuan = [0.0] * 24
        elif len(c_lt_block_yuan) != 24:
            raise ValueError("c_lt_block_yuan 必须为 24 元素或 None")
        if q_dayahead_cleared is not None and len(q_dayahead_cleared) != 24:
            raise ValueError("q_dayahead_cleared 必须为 24 元素或 None")

        load_path = LOAD_DIR / f"load_{region}.csv"
        if not load_path.exists():
            raise ValueError(f"未找到负荷数据: {load_path}")

        df = pd.read_csv(load_path, dtype={"date": str, "hour": int})
        day = df[df["date"] == date].sort_values("hour")
        if len(day) != 24:
            raise ValueError(f"日期 {date} 在 {load_path} 中未找到 24 小时数据（实际 {len(day)} 行）")

        hourly = []
        for h in range(24):
            row = day[day["hour"] == h].iloc[0]
            q_clr = None if q_dayahead_cleared is None else float(q_dayahead_cleared[h])
            hourly.append(HourlyData(
                hour=h,
                load_real=float(row["Load_real"]),
                P_user=0.0,  # 由定价模块填入
                P_da=P_da[h],
                P_rt=P_rt[h],
                Q_contract=Q_contract[h],
                P_contract=P_contract[h],
                Q_dayahead=Q_dayahead[h],
                P_ref=float(P_ref[h]),
                q_dayahead_cleared=q_clr,
                c_lt_block_yuan=float(c_lt_block_yuan[h]),
            ))
        return hourly

    @staticmethod
    def get_monthly_pda(region: str) -> list[float]:
        """返回全月日前电价扁平列表 (元/kWh)。用于 M4 现货联动电价计算。"""
        price_path = PRICE_DIR / f"price_{region}.csv"
        if not price_path.exists():
            raise ValueError(f"未找到电价数据: {price_path}")
        df = pd.read_csv(price_path, dtype={"date": str, "hour": int})
        return (df["day_ahead"] / 1000.0).tolist()
