"""配置文件加载器。

从 data/config/ 目录加载全局参数 CSV 文件，保存修改后的配置。
"""
from pathlib import Path
from typing import Optional, Union

import pandas as pd

from src.models.dispatch import ESSParams
from src.models.wholesale import WholesaleSettlementConfig

CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "config"

CONTRACT_CURVE_FILES = {"mock_henan": "contract_position_henan.csv"}
DAYAHEAD_CURVE_FILES = {"mock_henan": "dayahead_position_henan.csv"}
WHOLESALE_SETTLEMENT_PATH = CONFIG_DIR / "wholesale_settlement_defaults.csv"


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
    def load_contract_position(
        region: str,
        date: Optional[str] = None,
        profile: str = "mock_henan",
    ) -> pd.DataFrame:
        """加载中长期合约持仓（含 P_ref、阻塞附加费等可选列）。

        Args:
            region: 地区标识（预留；当前数据为河南示范曲线）
            date: 方案日期；若 CSV 含 date 列则只加载该日 24 点
            profile: 合约曲线配置名，见 CONTRACT_CURVE_FILES
        """
        _ = region
        fname = CONTRACT_CURVE_FILES.get(profile, next(iter(CONTRACT_CURVE_FILES.values())))
        raw = pd.read_csv(CONFIG_DIR / fname)
        df = _filter_hourly_csv_by_date(raw, date, fname)
        if "p_ref_yuan_per_kwh" not in df.columns:
            df["p_ref_yuan_per_kwh"] = 0.0
        if "c_lt_block_yuan" not in df.columns:
            df["c_lt_block_yuan"] = 0.0
        return df

    @staticmethod
    def load_dayahead_position(
        region: str,
        date: Optional[str] = None,
        profile: str = "mock_henan",
    ) -> pd.DataFrame:
        """加载日前电量（含出清电量列，用于 cleared 口径）。"""
        _ = region
        fname = DAYAHEAD_CURVE_FILES.get(profile, next(iter(DAYAHEAD_CURVE_FILES.values())))
        raw = pd.read_csv(CONFIG_DIR / fname)
        df = _filter_hourly_csv_by_date(raw, date, fname)
        if "q_dayahead_cleared_kwh" not in df.columns:
            df["q_dayahead_cleared_kwh"] = df["q_dayahead_kwh"]
        return df

    @staticmethod
    def load_wholesale_settlement() -> WholesaleSettlementConfig:
        """加载售电批发购电结算全局配置（第五章表 5.4）。"""
        if not WHOLESALE_SETTLEMENT_PATH.exists():
            return WholesaleSettlementConfig()
        df = pd.read_csv(WHOLESALE_SETTLEMENT_PATH)
        d: dict[str, str | float] = {}
        for _, r in df.iterrows():
            key = str(r["param"])
            val = r["value"]
            if key in (
                "purchase_monthly_constant_yuan",
                "guangxi_month_smooth_yuan",
                "shanxi_wholesale_addon_yuan",
            ):
                d[key] = float(val)
            else:
                d[key] = val
        return WholesaleSettlementConfig.from_flat_dict(d)

    @staticmethod
    def save_wholesale_settlement(cfg: WholesaleSettlementConfig) -> None:
        """保存售电批发购电结算配置。"""
        flat = cfg.to_flat_dict()
        rows = [(k, v, "-", "true") for k, v in flat.items()]
        out = pd.DataFrame(rows, columns=["param", "value", "unit", "editable"])
        out.to_csv(WHOLESALE_SETTLEMENT_PATH, index=False, encoding="utf-8-sig")

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
