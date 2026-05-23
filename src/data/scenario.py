"""方案管理器。

方案 = 全局默认参数 + 方案私有参数覆盖。
存储为 data/scenarios/{id}.json。
"""
import json
import uuid
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from copy import deepcopy


SCENARIO_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "scenarios"


class ScenarioConfig:
    """方案配置。"""

    def __init__(
        self,
        name: str,
        region: str = "henan",
        pricing_mode: str = "M1",
        business_model: str = "B1",
        ess_params: dict | None = None,
        financial_params: dict | None = None,
        selected_date: str = "2026-03-15",
        private_overrides: dict | None = None,
        id: str | None = None,
        created_at: str | None = None,
    ):
        self.id = id
        self.name = name
        self.created_at = created_at or datetime.now(timezone.utc).isoformat()
        self.region = region
        self.pricing_mode = pricing_mode
        self.business_model = business_model
        self.ess_params = ess_params or {}
        self.financial_params = financial_params or {}
        self.selected_date = selected_date
        self.private_overrides = private_overrides or {}

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at,
            "region": self.region,
            "pricing_mode": self.pricing_mode,
            "business_model": self.business_model,
            "ess_params": self.ess_params,
            "financial_params": self.financial_params,
            "selected_date": self.selected_date,
            "private_overrides": self.private_overrides,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ScenarioConfig":
        return cls(
            id=d.get("id"),
            name=d["name"],
            created_at=d.get("created_at"),
            region=d.get("region", "henan"),
            pricing_mode=d.get("pricing_mode", "M1"),
            business_model=d.get("business_model", "B1"),
            ess_params=d.get("ess_params", {}),
            financial_params=d.get("financial_params", {}),
            selected_date=d.get("selected_date", "2026-03-15"),
            private_overrides=d.get("private_overrides", {}),
        )

    def resolve_params(self, global_ess: dict, global_fin: dict) -> tuple[dict, dict]:
        """按优先级解析参数：private_overrides > scenario 私有 > 全局默认。

        Returns:
            (ess_params, fin_params) 两个 dict
        """
        ess = deepcopy(global_ess)
        fin = deepcopy(global_fin)

        # 方案私有参数覆盖全局
        if self.ess_params:
            ess.update(self.ess_params)
        if self.financial_params:
            fin.update(self.financial_params)

        # private_overrides 最高优先级
        for path, value in self.private_overrides.items():
            obj_name, key = path.split(".", 1)
            if obj_name == "ess_params":
                ess[key] = value
            elif obj_name == "financial_params":
                fin[key] = value

        return ess, fin


class ScenarioManager:
    """方案管理器。读写 data/scenarios/ 下的 JSON 文件。"""

    def __init__(self, storage_dir: str | Path = None):
        self._dir = Path(storage_dir) if storage_dir else SCENARIO_DIR
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, scenario_id: str) -> Path:
        return self._dir / f"{scenario_id}.json"

    def save(self, config: ScenarioConfig) -> str:
        """保存方案。无 id 时自动生成。返回方案 ID。"""
        if config.id is None:
            config.id = uuid.uuid4().hex[:12]
        path = self._path(config.id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config.to_dict(), f, ensure_ascii=False, indent=2)
        return config.id

    def load(self, scenario_id: str) -> ScenarioConfig:
        """加载方案。"""
        path = self._path(scenario_id)
        if not path.exists():
            raise FileNotFoundError(f"方案 {scenario_id} 不存在: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return ScenarioConfig.from_dict(json.load(f))

    def list_all(self) -> list[dict]:
        """列出所有方案（仅 id + name）。"""
        items = []
        for fname in self._dir.glob("*.json"):
            with open(fname, "r", encoding="utf-8") as f:
                d = json.load(f)
            items.append({"id": d["id"], "name": d["name"]})
        return sorted(items, key=lambda x: x["name"])

    def delete(self, scenario_id: str) -> None:
        """删除方案。"""
        path = self._path(scenario_id)
        if not path.exists():
            raise FileNotFoundError(f"方案 {scenario_id} 不存在")
        os.remove(path)

    def copy_params(self, from_id: str, to_id: str, param_keys: list[str] | None = None) -> None:
        """从源方案复制参数到目标方案。

        Args:
            from_id: 源方案 ID
            to_id: 目标方案 ID
            param_keys: 要复制的参数路径列表 (如 ["ess_params.cap_rated"])，None 表示全部
        """
        src = self.load(from_id)
        tgt = self.load(to_id)

        if param_keys is None:
            tgt.private_overrides = deepcopy(src.private_overrides)
        else:
            for key in param_keys:
                if key in src.private_overrides:
                    tgt.private_overrides[key] = deepcopy(src.private_overrides[key])

        self.save(tgt)
