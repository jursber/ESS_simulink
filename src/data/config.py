"""配置文件加载器。

从 data/config/ 目录加载全局参数 CSV 文件，保存修改后的配置。
"""
from pathlib import Path
from typing import Optional, Union

import pandas as pd

from src.models.dispatch import ESSParams

CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "config"


def _filter_hourly_csv_by_date(df: pd.DataFrame, date: Optional[str], label: str) -> pd.DataFrame:
    """若存在 date 列且传入 date，则只保留该日 0~23 时各一行。"""
    if date is None or "date" not in df.columns:
        return df
    out = df[df["date"].astype(str) == str(date)].copy()
    if len(out) == 0:
        raise ValueError(f"{label}：未找到日期 {date} 的数据，请检查 CSV")
    out = out.sort_values("hour")
    if len(out) != 24 or set(int(h) for h in out["hour"]) != set(range(24)):
        raise ValueError(
            f"{label}：日期 {date} 须包含 hour=0..23 共 24 行，实际 {len(out)} 行"
        )
    return out


class ConfigLoader:
    """配置加载器。读写 data/config/ 下的全局参数文件。"""

    # ---- ESS 参数 ----

    @staticmethod
    def load_ess_defaults(region: str) -> ESSParams:
        """从 ess_defaults.csv 加载储能系统默认参数。"""
        path = CONFIG_DIR / "ess_defaults.csv"
        df = pd.read_csv(path)
        row = {r['param']: float(r['value']) for _, r in df.iterrows()}
        return ESSParams(
            cap_rated=row.get('cap_rated', 5000),
            c_rate=row.get('c_rate', 0.5),
            eta_roundtrip=row.get('eta_roundtrip', 0.85),
            soc_min=row.get('soc_min', 0.10),
            soc_max=row.get('soc_max', 0.90),
            unit_cost=row.get('unit_cost', 0.9),
            r_om=row.get('r_om', 0.01),
            design_life=int(row.get('design_life', 10)),
            r_degrade=row.get('r_degrade', 0.025),
        )

    @staticmethod
    def save_ess_defaults(params: ESSParams, path: Path = None) -> None:
        """保存 ESSParams 到 CSV。"""
        if path is None:
            path = CONFIG_DIR / "ess_defaults.csv"
        rows = [
            ("cap_rated", params.cap_rated, "kWh", "true"),
            ("c_rate", params.c_rate, "-", "true"),
            ("eta_roundtrip", params.eta_roundtrip, "-", "true"),
            ("soc_min", params.soc_min, "-", "true"),
            ("soc_max", params.soc_max, "-", "true"),
            ("unit_cost", params.unit_cost, "元/Wh", "true"),
            ("r_om", params.r_om, "-", "true"),
            ("design_life", params.design_life, "年", "true"),
            ("r_degrade", params.r_degrade, "-", "true"),
        ]
        df = pd.DataFrame(rows, columns=["param", "value", "unit", "editable"])
        df.to_csv(path, index=False, encoding="utf-8-sig")

    # ---- 电价表 ----

    @staticmethod
    def load_tariff(region: str, mode: str) -> Union[pd.DataFrame, dict]:
        """加载电价表。

        Args:
            region: 地区
            mode: 'admin' | 'jiangsu' | 'contract'

        Returns:
            admin/contract → DataFrame; jiangsu → dict
        """
        if mode == "admin":
            return pd.read_csv(CONFIG_DIR / "tariff_admin_henan.csv")
        elif mode == "jiangsu":
            df = pd.read_csv(CONFIG_DIR / "tariff_jiangsu_mode_henan.csv")
            return {r['param']: r['value'] for _, r in df.iterrows()}
        elif mode == "contract":
            return pd.read_csv(CONFIG_DIR / "tariff_contract_henan.csv")
        raise ValueError(f"未知电价模式: {mode}")

    # ---- 合约持仓 ----

    @staticmethod
    def load_contract_position(region: str, date: Optional[str] = None) -> pd.DataFrame:
        """加载中长期合约持仓。

        Args:
            region: 地区标识（当前文件名为 henan 固定后缀，与既有电价表一致）
            date: 方案日期；若 CSV 含 date 列则只加载该日 24 点，供购电成本与现货曲线对齐
        """
        _ = region  # 预留多地区文件名
        raw = pd.read_csv(CONFIG_DIR / "contract_position_henan.csv")
        return _filter_hourly_csv_by_date(raw, date, "contract_position_henan.csv")

    @staticmethod
    def load_dayahead_position(region: str, date: Optional[str] = None) -> pd.DataFrame:
        """加载日前申报电量。参数含义同 load_contract_position。"""
        _ = region
        raw = pd.read_csv(CONFIG_DIR / "dayahead_position_henan.csv")
        return _filter_hourly_csv_by_date(raw, date, "dayahead_position_henan.csv")

    # ---- 财务参数 ----

    @staticmethod
    def load_financial_defaults(region: str) -> dict:
        """从 financial_defaults.csv 加载财务默认参数。"""
        path = CONFIG_DIR / "financial_defaults.csv"
        df = pd.read_csv(path)
        return {r['param']: r['value'] for _, r in df.iterrows()}

    @staticmethod
    def save_financial_defaults(data: dict, path: Path = None) -> None:
        """保存财务默认参数到 CSV。"""
        if path is None:
            path = CONFIG_DIR / "financial_defaults.csv"
        rows = [(k, v, "-", "true") for k, v in data.items()]
        df = pd.DataFrame(rows, columns=["param", "value", "unit", "editable"])
        df.to_csv(path, index=False, encoding="utf-8-sig")
