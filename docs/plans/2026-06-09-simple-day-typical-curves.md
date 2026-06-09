# 单日典型曲线模拟实施计划

> 面向产品决策的计划正文优先说明架构、边界、逻辑、优缺点和风险；代码样例与测试片段统一放在文末“技术附件”。

## 目标

把当前单方案分析页第一版收敛为“单日简单模拟”模式：用户只能从后台已准备好的典型曲线中选择负荷、光伏、现货、零售电价、批发侧交易 profile 等输入，快速完成一个典型日测算；月度和年度结果按典型日结果 `*30`、`*365` 粗略折算。

多日深度模拟暂不实现，但从命名、数据目录和接口边界上预留未来扩展空间。

## 关键修正原则

单日简单模拟和多日深度模拟的差异只在“曲线数据层”：

- 光伏、储能、财务参数、商业模式、调度算法、结算模型、投资评价模型应共用同一套专业模型。
- 不能把单日简单模拟做成“低专业度版本”，也不能为多日深度模拟另造一套光伏/储能固有信息。
- 单日模式使用典型曲线作为输入，强调快速反馈和粗略折算。
- 多日模式未来使用真实全量曲线或用户导入曲线作为输入，强调时间范围、数据完整性、跨日连续性和结果可信度。
- 两种模式的专业复杂度不应体现在设备参数或业务模型缩水，而应体现在可使用的数据时间范围、数据粒度、曲线来源和结果汇总方式不同。

## 架构判断

推荐新增“单日典型曲线 catalog 层”，但不立刻搬迁现有数据目录。

当前项目里已有多类数据入口：`data/load/` 负荷曲线、`data/pv_typical_curves/` 光伏典型曲线、`data/spot_typical_prices/` 现货典型价格、`data/trading_strategy/` 批发侧 profile、`data/tariff/` 零售电价。第一版应先用一个只读 catalog 服务把这些资产统一枚举出来，前端只消费 catalog，不直接理解文件目录结构。

计算链路继续保持 24 小时调度算法不变。`calculate()` 只需要从方案快照里的 curve/profile ID 解析出 24 点输入曲线，然后把这些曲线喂给既有调度、结算、投资评价逻辑。

未来多日深度模拟可以在同一设备模型、同一算法框架下扩展为多日曲线加载器。届时新增的是“数据读取和时间域管理”，不是另一个光伏模型或储能模型。

## 本期范围

本期必须做：

1. 建立单日典型曲线 catalog 服务，统一枚举负荷、光伏、现货、零售电价和批发侧 profile。
2. 新增 `/api/simple-day/catalog`，供前端所有曲线下拉加载。
3. 让 `calculate()` 能识别 `run_curves` 中的典型曲线 ID，例如 `pv_curve_id`、`spot_curve_id`、`retail_curve_id`。
4. 前端单方案页把曲线选择改成只读下拉，不暴露上传、自定义、编辑曲线入口。
5. A/B/C/D 快照保存曲线 ID/profile ID，切换、保存、刷新、对比时必须复现一致。
6. 结果展示标注“单日典型曲线测算，月度/年度为粗略折算”。
7. 在 PRD 中追加本轮需求记录。

本期明确不做：

1. 不做多日深度模拟。
2. 不做用户导入自定义曲线。
3. 不做数据管理模块。
4. 不改调度优化算法。
5. 不把光伏、储能、财务、商业模式做成两套专业度不同的模型。
6. 不把 `data/pv_typical_curves/` 和 `data/spot_typical_prices/` 的大批量 CSV 直接纳入 Git；后续单独决定 Git LFS、外部数据包或本地生成策略。

## 数据边界

第一版建议保持物理目录不动，只在代码层建立“单日典型曲线视图”：

- 负荷典型曲线：继续使用 `data/load/`。
- 光伏典型曲线：读取 `data/pv_typical_curves/catalog.csv`。
- 现货典型曲线：读取 `data/spot_typical_prices/catalog.csv`。
- 批发侧合同/日前 profile：继续使用 `data/trading_strategy/` 与 `wholesale_overrides`。
- 零售电价曲线：继续使用 `data/tariff/` 与电价模式配置。

未来如果要彻底隔离，可演进为：

- `data/simple_day/`：只放固定典型日曲线，面向快速模拟。
- `data/deep_simulation/`：放真实长周期曲线、用户导入曲线和数据管理模块资产。

但第一版不搬目录，避免牵动过大。

## 快照契约

方案快照不保存曲线数组，只保存曲线 ID 或 profile ID。

建议字段：

- `run_curves.load_profile`：负荷典型曲线 ID。
- `run_curves.pv_curve_id`：光伏典型曲线 ID。
- `run_curves.spot_curve_id`：现货典型价格 ID。
- `run_curves.retail_curve_id`：零售电价曲线 ID。
- `wholesale_overrides.contract_curve_profile`：批发侧合约持仓 profile。
- `wholesale_overrides.dayahead_curve_profile`：日前申报 profile。

兼容规则：

- 新字段优先。
- 旧字段兜底，例如 `pv_region`、`pv_curve_type`。
- A/B/C/D 保存、复现、对比只传 ID，不传曲线本体。

## 产品利弊

优点：

- 用户调参体验快，单日 24 点计算天然适配现有架构。
- 曲线选择变成枚举项后，方案更容易复现和对比。
- 数据目录和业务模型分离，未来换数据资产不必重写前端。
- 不会因为多日深度模拟的复杂度拖慢第一版交付。
- 保留同一套光伏、储能、财务和商业模型，避免产品口径分裂。

代价：

- `*30`、`*365` 只能是粗略折算，不能表达真实年度波动。
- 典型曲线 catalog 需要治理，否则下拉会变成“数据文件列表”而不是产品选项。
- 多日深度模拟未来仍要处理跨日 SOC、缺失值、数据粒度、性能、图表降采样等复杂问题。
- 大批量曲线数据未入库时，协作环境需要明确数据安装或生成流程。

## 实施任务

### 任务 1：建立单日典型曲线 catalog 服务层

目标：让后端有一个统一入口枚举和读取单日典型曲线。

涉及文件：

- 新增 `src/data/simple_day_catalog.py`
- 新增 `tests/test_simple_day_catalog.py`

验收标准：

- 能列出负荷典型曲线。
- 有 `data/pv_typical_curves/catalog.csv` 时能列出光伏典型曲线。
- 有 `data/spot_typical_prices/catalog.csv` 时能列出现货典型曲线。
- catalog 缺失时返回空列表，不导致系统启动失败。

### 任务 2：新增单日典型曲线 API

目标：前端不再直接依赖静态 option 或数据目录，而是统一调用 API 获取可选曲线。

涉及文件：

- 修改 `api/routes.py`
- 必要时修改 `api/schemas.py`
- 修改 `tests/test_project_audit.py`

建议接口：

- `GET /api/simple-day/catalog`

返回内容：

- `mode`
- `load_profiles`
- `pv_profiles`
- `spot_profiles`
- `retail_profiles`
- `wholesale_profiles`

验收标准：

- API 返回结构稳定。
- 缺少某类数据时该类为空列表，而不是 500。
- 保留现有 `/api/params/load-profiles`，不影响缺省参数页。

### 任务 3：让计算入口识别曲线 ID

目标：`calculate()` 根据方案快照里的 ID 加载对应 24 点曲线。

涉及文件：

- 修改 `src/core/calculator.py`
- 必要时修改 `src/data/config.py`
- 必要时修改 `src/data/loader.py`
- 修改 `tests/test_calculator.py`

处理逻辑：

- 有 `spot_curve_id` 时，使用典型现货曲线覆盖当前按日期读取现货数据的逻辑。
- 无 `spot_curve_id` 时，保留旧逻辑。
- 有 `pv_curve_id` 时，使用光伏典型曲线 catalog 读取并聚合成 24 点。
- 无 `pv_curve_id` 时，保留 `pv_region`、`pv_curve_type` 旧逻辑。
- 负荷继续使用 `load_profile`，但不再允许前端写入自定义缩放参数。

验收标准：

- 携带 `pv_curve_id`、`spot_curve_id` 的方案能正常返回 24 点结果。
- 不携带新字段的旧方案仍可运行。
- A/B/C/D 中不同 curve ID 计算结果不串。

### 任务 4：前端曲线选择改为只读下拉

目标：单方案页所有曲线都从 catalog 下拉选择，不允许用户自定义。

涉及文件：

- 修改 `frontend/index.html`
- 修改 `frontend/js/workbench.v4.js`
- 修改 `frontend/js/app.v4.js`
- 修改 `frontend/js/analysis.v4.js`

交互要求：

- 负荷、光伏、现货/电价曲线都从 `/api/simple-day/catalog` 加载。
- 隐藏或禁用负荷曲线“编辑”入口。
- 不出现上传、自定义、手动录入曲线入口。
- A 新增 B 时，B 继承 A 当前曲线选择。
- A/B/C/D 切换后，各自曲线选择复现。

验收标准：

- 页面刷新后下拉正常加载。
- 保存方案后刷新，曲线 ID 仍复现。
- 比较页带入当前四槽快照。

### 任务 5：结果口径标注为典型日粗略折算

目标：避免用户把典型日 `*365` 理解为真实年度仿真。

涉及文件：

- 修改 `api/schemas.py`
- 修改 `api/routes.py`
- 修改 `frontend/js/analysis.v4.js`
- 修改 `frontend/index.html`

建议响应增加 `simulation` 元信息：

- `mode = simple_day`
- `scaling_method = typical_day_multiply`
- `day_count_month = 30`
- `day_count_year = 365`
- `disclaimer`

前端展示：

- 用短标签表达：`单日典型曲线 | 月度*30 | 年度*365`
- 避免大段说明占据主界面。

验收标准：

- API 响应包含 simulation meta。
- 前端结果页能看到口径标签。
- 月度/年度指标含义与标签一致。

### 任务 6：保护快照和对比契约

目标：确保新 curve ID 加入后不破坏刚打牢的 A/B/C/D 契约。

涉及文件：

- 修改 `tests/test_scenario.py`
- 修改 `tests/test_project_audit.py`
- 必要时修改 `src/data/scenario.py`

验收标准：

- `ScenarioConfig` roundtrip 保留 `run_curves.*_curve_id`。
- `/api/calculate` 和 `/api/compare` 对同一子方案快照的核心指标一致。
- 前端保存父方案时，A 的根级字段和 `variants` 中各槽字段都不丢。

### 任务 7：补文档和 PRD

目标：把产品口径、数据边界和本期不做事项写清楚。

涉及文件：

- 修改 `PRD/requirements.md`
- 新增或修改 `docs/SIMPLE_DAY_SIMULATION_CONTRACT.md`
- 必要时更新 `docs/SIMULATION_HORIZON_DESIGN.md`

PRD 第 18 轮建议：

- R153：单日简单模拟仅允许选择后台典型曲线，不允许自定义曲线。
- R154：新增单日典型曲线 catalog API。
- R155：方案快照保存曲线 ID/profile ID。
- R156：月度/年度结果按典型日 `*30/*365` 粗略折算并标注。
- R157：多日深度模拟、用户导入和数据管理模块暂不实现。
- R158：单日和多日共用光伏、储能、财务、商业模式和调度模型，差异只在曲线数据层。

## 推荐执行顺序

1. 先做 catalog 服务层和 API。
2. 再让计算入口识别曲线 ID。
3. 再接前端只读下拉和 A/B/C/D 快照。
4. 再补结果口径标注。
5. 最后补测试、PRD 和契约文档。

## 验证清单

静态检查：

- `python -m compileall -q api src tests`
- `node --check frontend/js/app.v4.js`
- `node --check frontend/js/analysis.v4.js`
- `node --check frontend/js/workbench.v4.js`
- `node --check frontend/js/compare.v4.js`
- `git diff --check`

单元测试：

- `python -m pytest -p no:cacheprovider -q tests/test_scenario.py tests/test_simple_day_catalog.py tests/test_calculator.py`

运行态 smoke：

- `GET /api/simple-day/catalog` 返回 catalog。
- `POST /api/calculate` 携带 curve ID 返回 24 点结果。
- `POST /api/compare` 同一子方案快照核心指标与 calculate 一致。

浏览器验证：

- 下拉从 catalog 加载。
- A/B/C/D 选择不同曲线后切换不串。
- 保存后刷新可复现。
- 比较页带入当前四槽快照。

## 主要风险

- 大批量曲线数据目前未入库，协作环境需要明确数据准备方式。
- catalog 字段如果不治理，下拉会变成技术文件列表，影响产品可用性。
- 旧方案仍使用 `pv_region/pv_curve_type`，需要兼容期。
- Windows Python 3.12 下 `TestClient` 可能继续触发 access violation，重要 API 需要用 uvicorn HTTP smoke 兜底。
- 多日深度模拟不要在本轮顺手接入，否则会把跨日 SOC、性能、缺失值和图表降采样提前带进来。

## 技术附件

### 附件 A：建议快照结构

```json
{
  "run_curves": {
    "load_profile": "steady_24h",
    "pv_curve_id": "Henan:province_total:annual:typical",
    "spot_curve_id": "Henan:2026-03:spot_price",
    "retail_curve_id": "admin:Henan:202603:commercial"
  },
  "wholesale_overrides": {
    "settlement_mode": "GUANGDONG_STYLE",
    "contract_curve_profile": "mock_henan",
    "dayahead_curve_profile": "mock_henan"
  }
}
```

### 附件 B：catalog API 返回结构草案

```json
{
  "mode": "simple_day",
  "load_profiles": [],
  "pv_profiles": [],
  "spot_profiles": [],
  "retail_profiles": [],
  "wholesale_profiles": {
    "settlement_modes": [],
    "contract_profiles": [],
    "dayahead_profiles": []
  }
}
```

### 附件 C：测试样例草案

```python
def test_variant_roundtrip_preserves_simple_day_curve_ids():
    cfg = ScenarioConfig(
        name="curve-id-roundtrip",
        region="henan",
        variants={
            "A": {
                "run_curves": {
                    "load_profile": "steady_24h",
                    "pv_curve_id": "Henan:province_total:annual:typical",
                    "spot_curve_id": "Henan:2026-03:spot_price",
                    "retail_curve_id": "admin:Henan:202603:commercial",
                }
            }
        },
    )
    data = ScenarioConfig.from_dict(cfg.to_dict())
    assert data.variants["A"]["run_curves"]["pv_curve_id"] == "Henan:province_total:annual:typical"
```

```python
def test_simple_day_catalog_api_contract():
    client = TestClient(app)
    resp = client.get("/api/simple-day/catalog")
    assert resp.status_code == 200
    data = resp.json()
    assert {"load_profiles", "pv_profiles", "spot_profiles", "wholesale_profiles"} <= set(data)
```
