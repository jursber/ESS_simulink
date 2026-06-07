# PRD ↔ 代码 ↔ 测试 追溯矩阵

> 对应 PRD：[PRD_v1.0.3.md](PRD_v1.0.3.md) 章节号。随实现演进更新本表。  
> 最后更新：2026-06-07（删除旧 Streamlit 前端，确认 FastAPI + SPA 为唯一运行入口）

| PRD 章节 | 主题 | 主要实现 | 测试（pytest） |
|----------|------|----------|----------------|
| §1 | 项目概述 / 范围 | （文档） | — |
| §2 | 物理模型、SOC、`load_real`/`load_grid`/`load_ESS` | [src/core/dispatch.py](../src/core/dispatch.py) `simulate_sequential`、`run_dispatch`；[src/data/loader.py](../src/data/loader.py) 组装 `HourlyData` | [tests/test_loader.py](../tests/test_loader.py)、[tests/test_dispatch_all.py](../tests/test_dispatch_all.py) |
| §3 | 电价模式 M1~M5、`P_user` | [src/core/pricing.py](../src/core/pricing.py) `compute_user_price` | [tests/test_pricing.py](../tests/test_pricing.py) |
| §4 | 商业模式与优化目标、B1~B4 | [src/core/dispatch.py](../src/core/dispatch.py) `compute_effective_price`、`optimize_arbitrage`；[src/models/dispatch.py](../src/models/dispatch.py) `BusinessModel` | [tests/test_dispatch_all.py](../tests/test_dispatch_all.py) |
| §5 | 公式体系（用户账单、售电购电、投资指标等） | [src/core/dispatch.py](../src/core/dispatch.py)；[src/core/wholesale_settlement.py](../src/core/wholesale_settlement.py)；[src/core/calculator.py](../src/core/calculator.py) | [tests/test_purchase_cost.py](../tests/test_purchase_cost.py)、[tests/test_wholesale_settlement.py](../tests/test_wholesale_settlement.py)、[tests/test_calculator.py](../tests/test_calculator.py) |
| §6 | 数据清单、CSV、`date` 筛选 24 点 | [src/data/config.py](../src/data/config.py)；[src/data/loader.py](../src/data/loader.py) | [tests/test_config.py](../tests/test_config.py)、[tests/test_loader.py](../tests/test_loader.py) |
| §7 | 算法需求（离散搜索等） | [src/core/dispatch.py](../src/core/dispatch.py) | [tests/test_dispatch_all.py](../tests/test_dispatch_all.py) |
| §8 | 架构原则 | 分层：`frontend` / `api` → `calculator` / `data` → `core` | [tests/test_integration.py](../tests/test_integration.py)（端到端倾向） |
| §9 | Web 交互（当前 SPA） | [frontend/index.html](../frontend/index.html)、[frontend/css/](../frontend/css/)、[frontend/js/](../frontend/js/)；[api/main.py](../api/main.py) 挂载静态前端；[run.py](../run.py) 启动 FastAPI | [tests/test_integration.py](../tests/test_integration.py)；浏览器访问 `http://127.0.0.1:8000/` 人工验收 |
| §10 | 附录 | 参数默认值等多来自 `data/params/*.csv`，分省时序数据来自 `data/tariff/`、`data/spot_price/`、`data/dispatch_load/` 等目录 | [tests/test_config.py](../tests/test_config.py) |
| — | 方案 JSON 读写 | [src/data/scenario.py](../src/data/scenario.py) `ScenarioConfig`、`ScenarioManager` | [tests/test_scenario.py](../tests/test_scenario.py) |
| — | 批发结算配置模型 | [src/models/wholesale.py](../src/models/wholesale.py) | [tests/test_wholesale_settlement.py](../tests/test_wholesale_settlement.py) |

**缺口提示（维护用）**：矩阵不替代覆盖率统计；若 PRD 新增小节或新增省份/结算分支，请同步增行并补测试文件列。
