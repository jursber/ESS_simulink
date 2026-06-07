"""配置文件加载器。

从 data/ 目录加载参数 CSV 文件，保存修改后的配置。
"""
from pathlib import Path
from typing import Optional, Union

import pandas as pd

from src.models.dispatch import ESSParams
from src.models.wholesale import WholesaleSettlementConfig

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
PARAMS_DIR = DATA_DIR / "params"
WHOLESALE_SETTLEMENT_PATH = PARAMS_DIR / "wholesale_settlement.csv"


def _ym(date_str: Optional[str]) -> str:
    """从日期字符串提取 YYYYMM，用于按月读取文件。"""
    if date_str:
        return date_str[:4] + date_str[5:7]
    return ""

# 时段中文 → 英文映射
_PERIOD_MAP = {'谷': 'valley', '深谷': 'deep_valley', '平': 'flat', '峰': 'peak', '尖峰': 'super_peak'}
_PERIOD_LABEL = {'谷': '谷段', '深谷': '深谷', '平': '平段', '峰': '峰段', '尖峰': '尖峰'}


def _convert_tariff_format(raw: pd.DataFrame) -> pd.DataFrame:
    """将新格式 CSV（hour,时段,电压等级列...）转换为旧格式（period,start_hour,end_hour,price_yuan_per_kwh,label）。"""
    # 取第一个电压等级列作为价格
    price_cols = [c for c in raw.columns if c not in ('hour', '时段')]
    if not price_cols:
        raise ValueError("CSV 中未找到电价列")
    price_col = price_cols[0]

    # 按时段分组，计算 start_hour 和 end_hour
    segments = []
    cur_period = None
    cur_start = 0
    cur_price = 0.0
    for _, row in raw.iterrows():
        period_cn = str(row['时段'])
        price = row[price_col]
        if pd.isna(price):
            price = 0.0
        hour = int(row['hour'])
        if period_cn != cur_period:
            if cur_period is not None:
                segments.append({
                    'period': _PERIOD_MAP.get(cur_period, cur_period),
                    'start_hour': cur_start,
                    'end_hour': hour,
                    'price_yuan_per_kwh': cur_price,
                    'label': _PERIOD_LABEL.get(cur_period, cur_period),
                })
            cur_period = period_cn
            cur_start = hour
            cur_price = float(price)
        else:
            cur_price = float(price)  # 取该时段最后一个价格（同一时段价格相同）
    # 最后一段
    if cur_period is not None:
        segments.append({
            'period': _PERIOD_MAP.get(cur_period, cur_period),
            'start_hour': cur_start,
            'end_hour': 24,
            'price_yuan_per_kwh': cur_price,
            'label': _PERIOD_LABEL.get(cur_period, cur_period),
        })
    return pd.DataFrame(segments)


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
    """配置加载器。读写 data/ 下的参数文件。"""

    # ---- ESS 参数 ----

    @staticmethod
    def load_ess_defaults(region: str) -> ESSParams:
        """从 params/ess_defaults.csv 加载储能系统默认参数。"""
        path = PARAMS_DIR / "ess_defaults.csv"
        df = pd.read_csv(path, comment='#')
        row = {}
        for _, r in df.iterrows():
            k = str(r['param'])
            v = r['value']
            if k in ('design_life', 'cycle_life'):
                row[k] = int(v)
            elif k in ('degrade_enabled', 'cycle_enabled', 'r_ess_share'):
                if k in ('degrade_enabled', 'cycle_enabled'):
                    row[k] = bool(int(v))
                else:
                    row[k] = float(v)
            else:
                row[k] = float(v)
        return ESSParams(
            cap_rated=row.get('cap_rated', 1000),
            power_rated=row.get('power_rated', 0.5),
            eta_roundtrip=row.get('eta_roundtrip', 0.87),
            eta_charge=row.get('eta_charge', 0.92),
            soc_min=row.get('soc_min', 0.10),
            soc_max=row.get('soc_max', 0.90),
            design_life=int(row.get('design_life', 10)),
            r_degrade=row.get('r_degrade', 0.025),
            degrade_enabled=row.get('degrade_enabled', False),
            cycle_life=int(row.get('cycle_life', 5000)),
            cycle_enabled=row.get('cycle_enabled', False),
            unit_cost=row.get('unit_cost', 0.9),
            r_om=row.get('r_om', 0.01),
            r_ess_share=row.get('r_ess_share', 0.20),
        )

    @staticmethod
    def save_ess_defaults(params: ESSParams, path: Path = None) -> None:
        """保存 ESSParams 到 CSV。"""
        if path is None:
            path = PARAMS_DIR / "ess_defaults.csv"
        rows = [
            ("cap_rated", params.cap_rated, "kWh", "true"),
            ("power_rated", params.power_rated, "MW", "true"),
            ("eta_roundtrip", params.eta_roundtrip, "-", "true"),
            ("eta_charge", params.eta_charge, "-", "true"),
            ("soc_min", params.soc_min, "-", "true"),
            ("soc_max", params.soc_max, "-", "true"),
            ("design_life", params.design_life, "年", "true"),
            ("r_degrade", params.r_degrade, "-", "true"),
            ("degrade_enabled", int(params.degrade_enabled), "-", "true"),
            ("cycle_life", params.cycle_life, "次", "true"),
            ("cycle_enabled", int(params.cycle_enabled), "-", "true"),
            ("unit_cost", params.unit_cost, "元/Wh", "true"),
            ("r_om", params.r_om, "-", "true"),
            ("r_ess_share", params.r_ess_share, "-", "true"),
        ]
        df = pd.DataFrame(rows, columns=["param", "value", "unit", "editable"])
        df.to_csv(path, index=False, encoding="utf-8-sig")

    # ---- 光伏参数 ----

    @staticmethod
    def load_pv_defaults(region: str) -> dict:
        """从 params/pv_defaults.csv 加载光伏默认参数。"""
        path = PARAMS_DIR / "pv_defaults.csv"
        if not path.exists():
            return {
                "cap_rated": 1.0, "feed_in_tariff": 0.4, "self_use_discount": 0.80,
                "unit_cost": 3.5, "r_om": 0.015,
                "design_life": 25, "r_degrade_first": 0.02, "r_degrade": 0.005,
                "region": "henan", "curve_type": "annual_avg",
            }
        df = pd.read_csv(path, comment='#')
        row = {}
        for _, r in df.iterrows():
            k = str(r['param'])
            v = r['value']
            if k in ('design_life',):
                row[k] = int(v)
            elif k in ('region', 'curve_type'):
                row[k] = str(v)
            else:
                row[k] = float(v)
        return row

    @staticmethod
    def save_pv_defaults(data: dict, path: Path = None) -> None:
        """保存光伏参数到 CSV。"""
        if path is None:
            path = PARAMS_DIR / "pv_defaults.csv"
        rows = [(k, v, "-", "true") for k, v in data.items()]
        df = pd.DataFrame(rows, columns=["param", "value", "unit", "editable"])
        df.to_csv(path, index=False, encoding="utf-8-sig")

    @staticmethod
    def load_pv_curve(region: str, curve_type: str, minute: bool = False) -> list[float]:
        """加载光伏出力曲线（归一化出力，0~1）。

        Args:
            region: 省份
            curve_type: 曲线类型
            minute: True 返回 1440 点分钟级，False 返回 24 点小时级（聚合）
        """
        path = DATA_DIR / "pv_curves" / region / f"{curve_type}.csv"
        if not path.exists():
            path = DATA_DIR / "pv_curves" / region / "annual_avg.csv"
        if not path.exists():
            return [0.0] * (1440 if minute else 24)
        df = pd.read_csv(path, comment='#')
        if df.empty:
            return [0.0] * (1440 if minute else 24)
        if "output" in df.columns:
            # 1440 点分钟级格式
            minute_data = df["output"].tolist()
            if minute:
                return minute_data
            # 聚合为 24 点
            return [sum(minute_data[h*60:(h+1)*60]) / 60.0 for h in range(24)]
        # 兼容旧格式（24 列）
        row = df.iloc[0]
        return [float(row[str(h)]) for h in range(24)]

    @staticmethod
    def list_pv_curves(region: str = "henan") -> list[str]:
        """返回指定省份可用的光伏曲线类型列表。"""
        pv_dir = DATA_DIR / "pv_curves" / region
        if not pv_dir.exists():
            return []
        return [f.stem for f in sorted(pv_dir.glob("*.csv"))]

    # ---- 电价表 ----

    @staticmethod
    def load_tariff(region: str, mode: str) -> Union[pd.DataFrame, dict]:
        """加载电价表。

        Args:
            region: 地区（当前单用户，用于未来扩展）
            mode: 'admin' | 'contract' | 'flat'

        Returns:
            admin/contract → DataFrame (列: period, start_hour, end_hour, price_yuan_per_kwh, label)
            flat → dict
        """
        ym = _ym(getattr(ConfigLoader, '_current_date', None)) or "202603"
        if mode == "admin":
            path = DATA_DIR / "tariff" / "administrative_tariff" / "Beijing" / f"{ym}_commercial.csv"
            if not path.exists():
                admin_dir = DATA_DIR / "tariff" / "administrative_tariff" / "Beijing"
                files = sorted(admin_dir.glob(f"{ym}_*.csv"))
                if not files:
                    raise FileNotFoundError(f"未找到行政分时电价文件: {admin_dir}")
                path = files[0]
            raw = pd.read_csv(path, comment='#', encoding='utf-8-sig')
            return _convert_tariff_format(raw)
        elif mode == "flat":
            path = DATA_DIR / "tariff" / "flat_rate" / "flat_rate.csv"
            df = pd.read_csv(path, comment='#')
            return {r['param']: r['value'] for _, r in df.iterrows()}
        elif mode == "contract":
            contract_dir = DATA_DIR / "tariff" / "contract_tariff"
            files = sorted(contract_dir.glob("*.csv"))
            if not files:
                raise FileNotFoundError(f"未找到合同分时电价文件: {contract_dir}")
            return pd.read_csv(files[0], comment='#')
        raise ValueError(f"未知电价模式: {mode}")

    # ---- 合约持仓 ----

    @staticmethod
    def load_contract_position(
        region: str,
        date: Optional[str] = None,
        profile: str = "mock_henan",
    ) -> pd.DataFrame:
        """加载中长期合约持仓（含 P_ref、阻塞附加费等可选列）。"""
        ym = _ym(date)
        path = DATA_DIR / "contract_position" / f"{ym}.csv"
        if not path.exists():
            # fallback: 读取目录下第一个文件
            pos_dir = DATA_DIR / "contract_position"
            files = sorted(pos_dir.glob("*.csv"))
            if not files:
                raise FileNotFoundError(f"未找到中长期合约持仓文件: {pos_dir}")
            path = files[0]
        raw = pd.read_csv(path, comment='#')
        df = _filter_hourly_csv_by_date(raw, date, path.name)
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
        ym = _ym(date)
        path = DATA_DIR / "dayahead_position" / f"{ym}.csv"
        if not path.exists():
            pos_dir = DATA_DIR / "dayahead_position"
            files = sorted(pos_dir.glob("*.csv"))
            if not files:
                raise FileNotFoundError(f"未找到日前报电量文件: {pos_dir}")
            path = files[0]
        raw = pd.read_csv(path, comment='#')
        df = _filter_hourly_csv_by_date(raw, date, path.name)
        if "q_dayahead_cleared_kwh" not in df.columns:
            df["q_dayahead_cleared_kwh"] = df["q_dayahead_kwh"]
        return df

    @staticmethod
    def load_wholesale_settlement() -> WholesaleSettlementConfig:
        """加载售电批发购电结算全局配置。"""
        if not WHOLESALE_SETTLEMENT_PATH.exists():
            return WholesaleSettlementConfig()
        df = pd.read_csv(WHOLESALE_SETTLEMENT_PATH, comment='#')
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
        """从 params/financial_defaults.csv 加载财务默认参数。"""
        path = PARAMS_DIR / "financial_defaults.csv"
        df = pd.read_csv(path, comment='#')
        return {r['param']: r['value'] for _, r in df.iterrows()}

    @staticmethod
    def save_financial_defaults(data: dict, path: Path = None) -> None:
        """保存财务默认参数到 CSV。"""
        if path is None:
            path = PARAMS_DIR / "financial_defaults.csv"
        rows = [(k, v, "-", "true") for k, v in data.items()]
        df = pd.DataFrame(rows, columns=["param", "value", "unit", "editable"])
        df.to_csv(path, index=False, encoding="utf-8-sig")

    # ---- 系统负荷 ----

    @staticmethod
    def load_system_load(date: Optional[str] = None) -> list[float]:
        """加载统调负荷曲线（24 小时 MW）。"""
        ym = _ym(date)
        path = DATA_DIR / "system_load" / f"{ym}.csv"
        if not path.exists():
            sload_dir = DATA_DIR / "system_load"
            files = sorted(sload_dir.glob("*.csv"))
            if not files:
                return [3000.0] * 24
            path = files[0]
        df = pd.read_csv(path, comment='#')
        df = _filter_hourly_csv_by_date(df, date, path.name)
        return [float(df[df["hour"] == h]["system_load_mw"].iloc[0]) for h in range(24)]
