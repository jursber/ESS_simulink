"""数据加载器。

从 data/ 目录加载小时级数据，执行单位换算（元/MWh → 元/kWh），
组装为 HourlyData 对象供计算引擎使用。
"""
from pathlib import Path
from typing import Tuple, Optional

import pandas as pd

from src.models.dispatch import HourlyData

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
SPOT_PRICE_DIR = DATA_DIR / "spot_price"
LOAD_DIR = DATA_DIR / "load"


def _ym(date_str: str) -> str:
    """从日期字符串提取 YYYYMM，用于按月读取文件。"""
    return date_str[:4] + date_str[5:7]


def _find_monthly_file(directory: Path, date: str) -> Path:
    """在目录中查找匹配月份的 CSV 文件，找不到则用最近的。"""
    ym = _ym(date)
    path = directory / f"{ym}.csv"
    if path.exists():
        return path
    # fallback: 优先找 daily_default.csv，再找第一个含 date 列的文件
    default = directory / "daily_default.csv"
    if default.exists():
        return default
    for f in sorted(directory.glob("*.csv")):
        try:
            cols = pd.read_csv(f, nrows=0, comment='#').columns.tolist()
            if "date" in cols:
                return f
        except Exception:
            pass
    raise FileNotFoundError(f"未找到数据文件: {directory}")


def aggregate_minute_to_hour(minute_data: list[float]) -> list[float]:
    """将 1440 个分钟值聚合为 24 个小时均值。每 60 个点取平均。"""
    if len(minute_data) != 1440:
        raise ValueError(f"期望 1440 个分钟值，实际 {len(minute_data)}")
    return [sum(minute_data[h*60:(h+1)*60]) / 60.0 for h in range(24)]


class DataLoader:
    """数据加载器。提供负荷、电价、合约数据的加载和组装。"""

    @staticmethod
    def get_available_dates(region: str) -> list[str]:
        """返回该地区有完整数据的日期列表。"""
        load_dir = LOAD_DIR
        price_dir = SPOT_PRICE_DIR
        if not load_dir.exists() or not price_dir.exists():
            return []

        # 收集所有月份文件中的日期
        load_dates: set[str] = set()
        price_dates: set[str] = set()

        for f in load_dir.glob("*.csv"):
            try:
                df = pd.read_csv(f, dtype={"date": str}, usecols=["date"], comment='#')
                load_dates.update(df["date"].unique())
            except Exception:
                pass

        for f in price_dir.glob("*.csv"):
            try:
                df = pd.read_csv(f, dtype={"date": str}, usecols=["date"], comment='#')
                price_dates.update(df["date"].unique())
            except Exception:
                pass

        return sorted(load_dates & price_dates)

    @staticmethod
    def load_spot_prices(region: str, date: str) -> Tuple[list[float], list[float]]:
        """加载指定日期的日前和实时电价。

        Returns:
            (P_da, P_rt): 各 24 元素的电价列表 (元/kWh)
        """
        price_path = _find_monthly_file(SPOT_PRICE_DIR, date)
        df = pd.read_csv(price_path, dtype={"date": str, "hour": int}, comment='#')
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

        load_path = _find_monthly_file(LOAD_DIR, date)
        df = pd.read_csv(load_path, dtype={"date": str, "hour": int}, comment='#')
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
        # 读取 spot_price 目录下所有月份文件
        all_pda: list[float] = []
        for f in sorted(SPOT_PRICE_DIR.glob("*.csv")):
            df = pd.read_csv(f, dtype={"date": str, "hour": int}, comment='#')
            all_pda.extend((df["day_ahead"] / 1000.0).tolist())
        if not all_pda:
            raise ValueError(f"未找到电价数据: {SPOT_PRICE_DIR}")
        return all_pda
