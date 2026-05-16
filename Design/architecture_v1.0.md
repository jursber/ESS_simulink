# 储能运营模拟计算器 — 架构设计文档 v1.0

> 目标：本文档覆盖前端 UI 设计、后端架构、算法实现细节，足够 Claude Code 据此完成全部代码开发。
> 配套文档：`PRD/PRD_v1.0.1.md`（需求冻结）、`PRD/requirements.md`（需求记录）

---

## 目录

1. [系统架构总览](#1-系统架构总览)
2. [技术选型](#2-技术选型)
3. [目录结构](#3-目录结构)
4. [计算引擎设计](#4-计算引擎设计)
5. [数据访问层设计](#5-数据访问层设计)
6. [UI 层设计](#6-ui-层设计)
7. [API 路由设计](#7-api-路由设计)
8. [状态管理设计](#8-状态管理设计)
9. [算法详细设计](#9-算法详细设计)
10. [实施路线](#10-实施路线)

---

## 1. 系统架构总览

```
┌──────────────────────────────────────────────────────────┐
│                    Streamlit UI Layer                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────────┐ │
│  │全局参数库│ │ 方案管理 │ │单方案分析│ │ 多方案对比  │ │
│  │  页面    │ │   页面   │ │   页面   │ │    页面     │ │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └──────┬──────┘ │
│       │            │            │               │        │
│       └────────────┴────────────┴───────────────┘        │
│                          │                                │
│              Session State (st.session_state)             │
│        global_params / scenarios / results_cache          │
├──────────────────────────┼────────────────────────────────┤
│                          │                                │
│              数据访问层 (Data Access Layer)               │
│  ┌───────────────┐ ┌──────────────┐ ┌──────────────────┐ │
│  │ ConfigLoader  │ │ DataLoader   │ │ ScenarioManager  │ │
│  │ (CSV configs) │ │ (processed)  │ │ (save/load JSON) │ │
│  └───────┬───────┘ └──────┬───────┘ └────────┬─────────┘ │
├──────────┼────────────────┼──────────────────┼───────────┤
│          │                │                  │            │
│              计算引擎层 (Calculation Engine)              │
│  ┌──────────────────────────────────────────────────────┐ │
│  │              Unified Dispatch Engine                  │ │
│  │  ┌─────────────┐ ┌──────────────┐ ┌───────────────┐ │ │
│  │  │ P_eff 推导  │ │ 优化搜索     │ │ 金融指标计算  │ │ │
│  │  └─────────────┘ └──────────────┘ └───────────────┘ │ │
│  └──────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

**分层原则**：
- 计算引擎层：纯 Python，无 Streamlit 依赖，可独立单元测试
- 数据访问层：文件 I/O，格式转换，数据校验
- UI 层：仅负责展示和交互，所有计算委托给引擎层

---

## 2. 技术选型

| 层 | 技术 | 理由 |
|----|------|------|
| UI 框架 | **Streamlit 1.32+** | Python 原生，无需前后端分离，快速交付 |
| 图表 | **Plotly Express** | 交互式图表，支持瀑布图/折线图/柱状图 |
| 数据表格 | **st.dataframe / AgGrid** | 可编辑参数表 |
| 计算引擎 | **纯 Python + NumPy** | 当前算法为离散搜索，无需 cvxpy |
| 数据存储 | **CSV (输入) / JSON (方案)** | 人工可编辑，Git 可 diff |
| 状态管理 | **st.session_state** | Streamlit 原生方案 |
| 样式 | **自定义 CSS (st.markdown)** | 轻量级品牌化 |

---

## 3. 目录结构

```
E:\Cursor\ESS_simulink\
├── app.py                        # Streamlit 入口
├── requirements.txt
├── .gitignore
│
├── PRD/                          # 需求文档
│   ├── PRD_v1.0.1.md
│   ├── requirements.md
│   └── CHANGELOG.md
│
├── Design/                       # 设计文档
│   └── architecture_v1.0.md
│
├── data/
│   ├── config/                   # 可编辑参数文件（CSV）
│   │   ├── ess_defaults.csv      # 储能默认参数
│   │   ├── tariff_admin_henan.csv
│   │   ├── tariff_jiangsu_mode_henan.csv
│   │   ├── tariff_contract_henan.csv
│   │   ├── contract_position_henan.csv
│   │   └── dayahead_position_henan.csv
│   │
│   ├── processed/                # 处理后的小时级数据（只读）
│   │   ├── load/
│   │   │   └── load_henan.csv
│   │   └── spot_price/
│   │       └── price_henan.csv
│   │
│   ├── raw/                      # 原始数据（只读，不入库）
│   │   ├── load_raw/
│   │   └── spot_price_minute/
│   │
│   └── scenarios/                # 用户保存的方案（JSON）
│       └── *.json
│
├── src/
│   ├── __init__.py
│   │
│   ├── core/                     # 计算引擎（无 UI 依赖）
│   │   ├── __init__.py
│   │   ├── dispatch.py           # [已实现] 统一调度算法
│   │   └── pricing.py            # [待实现] 电价模式计算
│   │
│   ├── models/                   # 数据模型
│   │   ├── __init__.py
│   │   └── dispatch.py           # [已实现] Dataclass/enum 定义
│   │
│   ├── data/                     # 数据访问层
│   │   ├── __init__.py
│   │   ├── loader.py             # [待实现] 加载处理后的数据
│   │   ├── config.py             # [待实现] 加载/保存配置
│   │   └── scenario.py           # [待实现] 方案 JSON 读写
│   │
│   ├── utils/                    # 工具
│   │   ├── __init__.py
│   │   └── units.py              # [已实现] 单位注册表
│   │
│   └── ui/                       # Streamlit UI 组件
│       ├── __init__.py
│       ├── pages/                # 各页面
│       │   ├── __init__.py
│       │   ├── params_page.py    # [待实现] 全局参数库
│       │   ├── scenarios_page.py # [待实现] 方案管理
│       │   ├── analysis_page.py  # [待实现] 单方案分析
│       │   └── compare_page.py   # [待实现] 多方案对比
│       ├── components/           # 可复用 UI 组件
│       │   ├── __init__.py
│       │   ├── param_editor.py   # [待实现] 参数编辑表单
│       │   ├── dispatch_chart.py # [待实现] 调度曲线图
│       │   ├── waterfall.py      # [待实现] 收益瀑布图
│       │   └── metrics_table.py  # [待实现] 投资指标表
│       └── state.py              # [待实现] session_state 管理
│
├── scripts/                      # 数据处理脚本
│   ├── process_load.py
│   └── process_price.py
│
└── tests/                        # 测试
    ├── test_dispatch_all.py      # [已实现] 全模型验证
    ├── test_pricing.py           # [待实现]
    └── test_scenario.py          # [待实现]
```

---

## 4. 计算引擎设计

### 4.1 模块职责

**`src/core/dispatch.py`** — 统一调度引擎（已实现，需微调）：
- `compute_effective_price()` — P_eff 推导
- `optimize_arbitrage()` — 搜索最优充放电组合
- `simulate_sequential()` — 逐时顺序模拟
- `run_dispatch()` — 完整调度管线
- `_annual_cashflow()` — 年现金流口径选择
- `_npv()` / `_compute_irr()` — 投资评价

**`src/core/pricing.py`** — 电价模式计算（待实现）：
- 输入：PricingMode, region, 原始电价数据
- 输出：24 小时 P_user[t] 数组
- 五种模式的具体实现（见下文算法部分）

### 4.2 数据模型

已实现在 `src/models/dispatch.py`：
- `PricingMode` (Enum): M1~M5
- `BusinessModel` (Enum): B1, B2a, B2b, B2c, B3a, B3b, B4
- `ESSParams` (dataclass): 储能物理参数 + 计算属性 (max_power, eta_single, initial_investment)
- `FinancialParams` (dataclass): r_discount, r_user
- `HourlyData` (dataclass): 单小时全部输入数据
- `DispatchResult` (dataclass): 完整调度输出

待新增模型：

```python
# src/models/scenario.py（待实现）
@dataclass
class ScenarioConfig:
    """方案配置。"""
    id: str                          # UUID
    name: str                        # 用户命名
    created_at: str                  # ISO datetime
    region: str                      # "henan"
    pricing_mode: PricingMode
    business_model: BusinessModel
    ess_params: ESSParams
    financial_params: FinancialParams
    selected_date: str               # "2026-03-15"
    private_overrides: dict          # 仅覆盖全局默认的参数 {param_path: value}

@dataclass  
class GlobalParams:
    """全局默认参数库。"""
    ess: ESSParams
    financial: dict[str, FinancialParams]  # 按商业模式分别存储
    tariffs: dict[str, pd.DataFrame]       # 电价表
    contracts: dict[str, pd.DataFrame]     # 合约持仓
```

---

## 5. 数据访问层设计

### 5.1 ConfigLoader (`src/data/config.py`)

```
class ConfigLoader:
    load_ess_defaults() -> ESSParams
    load_tariff(region, mode) -> pd.DataFrame
    load_contract_position(region) -> pd.DataFrame
    load_dayahead_position(region) -> pd.DataFrame
    save_ess_defaults(params: ESSParams) -> None
```

从 `data/config/*.csv` 加载配置，保存修改后的配置。

### 5.2 DataLoader (`src/data/loader.py`)

```
class DataLoader:
    load_processed_load(region, date) -> list[HourlyData]
    load_spot_prices(region, date) -> (list[float], list[float])  # P_da, P_rt
    get_available_dates(region) -> list[str]
    get_load_range(region, date) -> (float, float)  # min, max
```

**关键：单位换算集中在此完成**。原始电价 元/MWh → 元/kWh 除 1000。

### 5.3 ScenarioManager (`src/data/scenario.py`)

```
class ScenarioManager:
    save(scenario: ScenarioConfig) -> str       # 返回文件路径
    load(scenario_id: str) -> ScenarioConfig
    list_all() -> list[dict]                    # id + name 列表
    delete(scenario_id: str) -> None
    copy_params(from_id, to_id, param_keys) -> None
```

方案存储为 `data/scenarios/{id}.json`，JSON 结构：

```json
{
  "id": "uuid",
  "name": "基准方案-河南B1",
  "created_at": "2026-05-16T10:30:00",
  "region": "henan",
  "pricing_mode": "M1",
  "business_model": "B1",
  "ess_params": { "cap_rated": 5000, "c_rate": 0.5, ... },
  "financial_params": { "r_discount": 0.06, "r_user": 0.30 },
  "selected_date": "2026-03-15",
  "private_overrides": { "ess_params.cap_rated": 8000 }
}
```

---

## 6. UI 层设计

### 6.1 页面路由

使用 Streamlit 原生多页面（`app.py` + `src/ui/pages/*.py`）：

```
app.py                          # 入口，st.navigation 定义页面
├── 全局参数库 (params_page)     # icon: ⚙
├── 方案管理 (scenarios_page)    # icon: 📋
├── 单方案分析 (analysis_page)   # icon: 📊
└── 多方案对比 (compare_page)    # icon: 📈
```

### 6.2 全局参数库页面

**功能**：展示和编辑所有默认参数。修改后影响所有新建方案（不影响已保存方案的私有覆盖值）。

**布局**：

```
┌────────────────────────────────────────────────────┐
│  ⚙ 全局参数库                          [恢复默认] [保存] │
├────────────────────────────────────────────────────┤
│  ▸ 储能系统参数                                     │
│    Cap_rated  [5000] kWh   ← 滑块 (1000-20000)    │
│    C_rate     [0.5]  -     ← 滑块 (0.1-2.0)       │
│    η_rt       [85]   %     ← 滑块 (70-95)         │
│    SOC_min    [10]   %     ← 滑块 (0-30)          │
│    SOC_max    [90]   %     ← 滑块 (70-100)        │
│    UnitCost   [0.90] 元/Wh  ← 数字输入              │
│    r_om       [1.0]  %     ← 滑块 (0.5-3.0)       │
│    DesignLife [10]   年    ← 数字输入              │
│    r_degrade  [2.5]  %     ← 滑块 (1.0-5.0)       │
│                                                     │
│  ▸ 财务参数                                         │
│    r_discount [6.0]  %     ← 滑块 (2-15)          │
│    r_user_B1  [30]   %     ← 滑块 (10-50)         │
│    r_user_B2  [50]   %     ← 滑块 (10-50)         │
│    r_user_B3  [40]   %     ← 滑块 (10-50)         │
│                                                     │
│  ▸ 电价表 (展开显示/编辑 CSV 表格)                   │
│    M1 行政分时 [st.data_editor]                      │
│    M2 江苏模式 [参数表格]                            │
│    M3 合同分时 [st.data_editor]                      │
│    M5 一口价   [数字输入]                            │
│                                                     │
│  ▸ 合约持仓 (展开显示/编辑 CSV 表格)                  │
│    Q_contract / P_contract [st.data_editor]          │
│    Q_dayahead [st.data_editor]                       │
└────────────────────────────────────────────────────┘
```

**交互细节**：
- 所有滑块变化实时预览，但需点击"保存"才写入文件
- "恢复默认"按钮从 `ess_defaults.csv` 重新加载
- `st.data_editor` 支持直接在表格中修改电价时段和合约数据
- 滑块采用对数刻度（UnitCost 范围大）或线性刻度

### 6.3 方案管理页面

**功能**：创建/复制/删除方案，管理每个方案的私有参数覆盖。

**布局**：

```
┌────────────────────────────────────────────────────┐
│  📋 方案管理                                        │
├────────────────────────────────────────────────────┤
│  [+ 新建方案]  [复制参数▼]                           │
│                                                     │
│  ┌─────────────┬──────────────┬──────────────────┐ │
│  │ 方案列表     │ 方案配置     │ 参数覆盖          │ │
│  │             │              │                  │ │
│  │ ○ 基准方案  │ 名称: [____] │ ess_params:      │ │
│  │   B1-M1    │ 地区: henan  │ ┌────┬────┬────┐ │ │
│  │  2026-05-16│ 电价: M1    │ │参数│默认│覆盖│ │ │
│  │             │ 模式: B1    │ │Cap │5000│8000│ │ │
│  │ ● 对比方案  │ 日期: 03-15 │ │... │... │... │ │ │
│  │   B3a-M1   │              │ └────┴────┴────┘ │ │
│  │  2026-05-16│ [重新计算]   │ [+ 添加覆盖]     │ │
│  │             │ [删除方案]   │                  │ │
│  └─────────────┴──────────────┴──────────────────┘ │
└────────────────────────────────────────────────────┘
```

**交互细节**：
- 左侧列表单选方案，右侧显示详情
- "新建方案"：弹出对话框输入名称，自动复制全局默认参数
- "复制参数"：下拉选择源方案 → 多选要复制的参数 → 确认覆盖当前方案
- "添加覆盖"：从全局参数库中选择参数添加到当前方案的私有覆盖列表
- "重新计算"：运行 `run_dispatch()`，更新该方案的结果缓存
- "删除方案"：确认后删除 JSON 文件

### 6.4 单方案分析页面

**功能**：展示单个方案的完整调度结果和收益分解。

**布局**：

```
┌────────────────────────────────────────────────────┐
│  📊 单方案分析                                      │
├────────────────────────────────────────────────────┤
│  当前方案: [下拉选择已保存的方案▼]                    │
│                                                     │
│  ┌──────────────────────────────────────────────┐  │
│  │          关键指标卡片 (st.metric)              │  │
│  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐       │  │
│  │  │ IRR  │ │ NPV  │ │回收期│ │年循环│       │  │
│  │  │9.1%  │ │64.6万│ │5.7年 │ │540次 │       │  │
│  │  └──────┘ └──────┘ └──────┘ └──────┘       │  │
│  └──────────────────────────────────────────────┘  │
│                                                     │
│  ▸ 调度曲线 (plotly 双 Y 轴)                         │
│    ┌──────────────────────────────────────────┐    │
│    │ X 轴: 0~23 小时                           │    │
│    │ 左 Y 轴: 电量 kWh (堆叠面积图)             │    │
│    │   █ load_grid  █ load_ESS (充红放绿)      │    │
│    │ 右 Y 轴: SOC (折线, 0~1) + P_eff (虚线)  │    │
│    └──────────────────────────────────────────┘    │
│                                                     │
│  ▸ 收益分解瀑布图 (plotly waterfall)                 │
│    ┌──────────────────────────────────────────┐    │
│    │ 用户电费节省 → 运营商收入 → 用户净收益      │    │
│    │ → 售电利润 → 组合利润 → 总福利             │    │
│    │ (仅显示当前商业模式有值的项目)              │    │
│    └──────────────────────────────────────────┘    │
│                                                     │
│  ▸ 投资指标表                                       │
│    ┌──────────────────────────────────────────┐    │
│    │ 总投资 | 年现金流 | IRR | NPV | 回收期    │    │
│    │ 年运维 | 日套利  | 循环次数 | ESS年净     │    │
│    └──────────────────────────────────────────┘    │
│                                                     │
│  ▸ 24 小时数据表 (可展开)                            │
│    h | load_real | load_ESS | load_grid | SOC     │
│    | P_user | P_rt | P_eff | ...                  │
└────────────────────────────────────────────────────┘
```

**图表规格**：
- 调度曲线：Plotly `make_subplots` 双 Y 轴，左轴 kWh（堆叠柱状图），右轴 SOC（折线图，0-1 范围）+ P_eff（虚线折线，次 Y 轴右侧）
- 瀑布图：`plotly.graph_objects.Waterfall`，展示收益从用户电费到各方净收益的分解
- 颜色：充电=蓝色 `#1f77b4`，放电=橙色 `#ff7f0e`，load_grid=灰色

### 6.5 多方案对比页面

**功能**：选择 2~4 个方案并排对比。

**布局**：

```
┌────────────────────────────────────────────────────┐
│  📈 多方案对比                                      │
├────────────────────────────────────────────────────┤
│  选择方案: [☑ 方案A] [☑ 方案B] [☑ 方案C]          │
│                                                     │
│  ▸ 参数差异表                                       │
│    ┌──────────────────────────────────────────┐    │
│    │ 参数     │ 方案A │ 方案B │ 方案C │        │    │
│    │ Cap_rated│ 5000  │ 8000  │ 5000  │        │    │
│    │ r_user   │ 0.30  │ 0.30  │ 0.50  │        │    │
│    │ (高亮差异行)                               │    │
│    └──────────────────────────────────────────┘    │
│                                                     │
│  ▸ 调度曲线叠加 (plotly)                             │
│    ┌──────────────────────────────────────────┐    │
│    │ 左图: 各方案 load_ESS 折线叠加             │    │
│    │ 右图: 各方案 SOC 折线叠加                  │    │
│    └──────────────────────────────────────────┘    │
│                                                     │
│  ▸ 收益分解对比 (分组柱状图)                         │
│    ┌──────────────────────────────────────────┐    │
│    │ X 轴: 收益项目（用户节省、运营商收入...）   │    │
│    │ 分组: 各方案不同颜色柱子                   │    │
│    └──────────────────────────────────────────┘    │
│                                                     │
│  ▸ 投资指标对比表                                   │
│    ┌──────────────────────────────────────────┐    │
│    │ 指标 │ 方案A │ 方案B │ 方案C │ 差异分析  │    │
│    │ IRR  │ 9.1%  │ 12.3% │ 5.2%  │ B优于A   │    │
│    │ ...                                       │    │
│    └──────────────────────────────────────────┘    │
│                                                     │
│  ▸ 差异智能分析 (markdown 文本)                      │
│    "方案B IRR比方案A高3.2个百分点，主要原因是..."    │
└────────────────────────────────────────────────────┘
```

**差异智能分析逻辑**：

```python
def analyze_differences(scenarios: list[ScenarioConfig],
                        results: list[DispatchResult]) -> str:
    """自动生成差异原因分析文本。"""
    # 1. 参数差异：列出所有不同的参数及变化方向
    # 2. 收益差异：按收益分项（用户节省/售电利润/运营商收入）分解 IRR 差异
    # 3. 调度差异：比较充放电策略差异（时序/电量）
    # 4. 综合判断：哪个因素是 IRR 差异的主要驱动
```

---

## 7. API 路由设计

虽然 Streamlit 是单体应用无需 REST API，但**核心计算函数对外暴露标准接口**，方便未来迁移到 FastAPI：

```python
# src/core/engine.py（待实现——对 run_dispatch 的封装）

def calculate(request: dict) -> dict:
    """统一计算入口。

    request = {
        "region": "henan",
        "date": "2026-03-15",
        "pricing_mode": "M1",
        "business_model": "B1",
        "ess_params": {...},
        "financial_params": {...},
    }

    返回: DispatchResult 的 JSON 序列化形式
    """
```

如果未来需要 Web API，在此接口上包装 FastAPI router 即可：

```python
# 未来: api.py
@router.post("/api/v1/calculate")
async def calculate_endpoint(request: CalculationRequest) -> CalculationResponse:
    return calculate(request.dict())
```

### 7.1 内部函数调用链

```
UI Event (用户点击"计算")
  → state.run_calculation(scenario_id)
    → ConfigLoader.load_ess_defaults()
    → DataLoader.load_processed_load(region, date)
    → DataLoader.load_spot_prices(region, date)
    → ConfigLoader.load_contract_position(region)
    → ConfigLoader.load_dayahead_position(region)
    → pricing.compute_user_price(pricing_mode, tariffs, P_da)
    → dispatch.run_dispatch(hourly, bm, pricing_mode, ess, fin)
    → state.cache_result(scenario_id, result)
    → st.rerun()
```

---

## 8. 状态管理设计

### 8.1 Session State 结构

```python
# src/ui/state.py

class AppState:
    """Streamlit session_state 管理。"""

    @staticmethod
    def init():
        """首次运行时初始化所有 key。"""
        defaults = {
            "global_params": None,        # GlobalParams 对象
            "scenarios": {},              # {scenario_id: ScenarioConfig}
            "results_cache": {},          # {scenario_id: DispatchResult}
            "selected_scenario": None,    # 当前选中的方案 ID
            "compare_selection": [],      # 对比选中的方案 ID 列表
            "config_dirty": False,        # 全局参数是否有未保存修改
        }
        for key, val in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = val

    @staticmethod
    def get_global_params() -> GlobalParams:
        if st.session_state.global_params is None:
            st.session_state.global_params = load_global_params()
        return st.session_state.global_params

    @staticmethod
    def get_result(scenario_id: str) -> DispatchResult | None:
        return st.session_state.results_cache.get(scenario_id)

    @staticmethod
    def cache_result(scenario_id: str, result: DispatchResult):
        st.session_state.results_cache[scenario_id] = result

    @staticmethod
    def invalidate_cache(scenario_id: str = None):
        """参数变化后清除缓存。"""
        if scenario_id:
            st.session_state.results_cache.pop(scenario_id, None)
        else:
            st.session_state.results_cache.clear()
```

### 8.2 参数优先级

方案计算时的参数解析顺序：

```
1. 全局默认参数 (ess_defaults.csv)
2. → 方案私有覆盖 (scenario.private_overrides)
3. → 计算引擎 (run_dispatch)
```

实现：

```python
def resolve_params(scenario: ScenarioConfig, globals: GlobalParams) -> tuple[ESSParams, FinancialParams]:
    ess = copy(globals.ess)
    fin = copy(globals.financial[scenario.business_model])
    for path, value in scenario.private_overrides.items():
        # path 如 "ess_params.cap_rated"
        obj, attr = path.split(".")
        setattr(locals()[obj], attr, value)
    return ess, fin
```

---

## 9. 算法详细设计

### 9.1 算法总流程

```
输入: 24h 数据, 电价模式, 商业模式, 储能参数, 财务参数
输出: DispatchResult

Step 1: 电价映射
  P_user = compute_user_price(pricing_mode, tariffs, P_da, P_rt)
  
Step 2: 有效价格信号推导
  P_eff = compute_effective_price(bm, P_user, P_TOU, P_rt, r_user)
  
Step 3: 优化搜索
  load_ESS, SOC, profit = optimize_arbitrage(P_eff, params, soc_initial)
  
Step 4: 关口表计算
  load_grid[t] = load_real[t] - load_ESS[t]
  
Step 5: 收益分解
  用户侧: user_bill_no_ess, user_bill_with_ess, savings, user_net
  售电侧: C_mlt, C_da, C_rt, purchase_cost, retail_revenue, retail_profit
  储能侧: ess_revenue, om_annual, ess_net_annual
  组合: combined_profit, total_welfare
  
Step 6: 投资评价
  annual_cf = _annual_cashflow(bm, result, om_annual)
  payback, npv, irr
  
Step 7: 返回 DispatchResult
```

### 9.2 电价映射算法 (`src/core/pricing.py`)

```python
def compute_user_price(mode: PricingMode,
                       tariffs: dict,          # 从 config CSV 加载的电价表
                       P_da: list[float],      # 日前电价 (元/kWh)
                       P_contract: list[float] = None) -> list[float]:
    """根据电价模式计算 24 小时 P_user。"""
    if mode == PricingMode.M1_ADMIN_TOU:
        # 查行政分时电价表
        return [lookup_tou(tariffs['admin'], h) for h in range(24)]

    elif mode == PricingMode.M2_JIANGSU:
        # P_base × 系数，时段同 M1
        cfg = tariffs['jiangsu']
        p_base = cfg['p_base']
        coeff = {h: get_coefficient(cfg, h) for h in range(24)}
        return [p_base * coeff[h] for h in range(24)]

    elif mode == PricingMode.M3_CONTRACT_TOU:
        # 查合同分时电价表（独立时段划分）
        return [lookup_tou(tariffs['contract'], h) for h in range(24)]

    elif mode == PricingMode.M4_SPOT_LINKED:
        # 全月对应小时日前均价
        return [monthly_avg_by_hour(P_da, h) for h in range(24)]

    elif mode == PricingMode.M5_FLAT:
        p_flat = tariffs['flat_price']
        return [p_flat] * 24
```

**TOU 查表逻辑**：

```python
def lookup_tou(tariff_df: pd.DataFrame, hour: int) -> float:
    """从分时电价表中查询某小时的电价。
    
    tariff_df 列: period, start_hour, end_hour, price_yuan_per_kwh
    时段可能跨日（如 21-24），start 到 end-1 为有效小时。
    """
    for _, row in tariff_df.iterrows():
        start, end = int(row['start_hour']), int(row['end_hour'])
        if start <= hour < end:
            return float(row['price_yuan_per_kwh'])
    raise ValueError(f"未找到 hour={hour} 的电价")
```

### 9.3 P_eff 推导伪代码

已在 `src/core/dispatch.py:compute_effective_price()` 实现。核心逻辑：

```
function compute_effective_price(bm, P_user, P_TOU, P_rt, r_user):
    P_eff = zeros(24)
    
    switch bm:
        case B1:       P_eff = P_TOU
        case B2a:      P_eff = P_rt - P_user
        case B2b,B2c,B3b: P_eff = P_user
        case B3a:      P_eff = P_rt - r_user * P_user
        case B4:       P_eff = P_rt
    
    return P_eff
```

**数学验证**（已在自审中逐项验证）：

| 模式 | 优化目标 | ESS 相关项 | P_eff | 验证 |
|------|---------|-----------|-------|------|
| B1 | max Operator income | Σ(load_ESS × P_TOU) × (1-r_user) | P_TOU | ✓ |
| B2a | max Retailer profit | Σ(load_ESS × (P_rt − P_user)) | P_rt − P_user | ✓ |
| B2b | max Operator income | Σ(load_ESS × P_user) × (1-r_user) | P_user | ✓ |
| B2c | max User net | Σ(load_ESS × P_user) × r_user | P_user | ✓ |
| B3a | max Combined profit | Σ(load_ESS × (P_rt − r_user × P_user)) | P_rt − r_user × P_user | ✓ |
| B3b | max User net | Σ(load_ESS × P_user) × r_user | P_user | ✓ |
| B4 | max Social welfare | Σ(load_ESS × P_rt) | P_rt | ✓ |

### 9.4 优化搜索算法

**算法选择：排序+滑动窗口搜索**（已实现）。选择理由：
- 决策变量离散（24 小时，每小时的充/放/静三种状态）
- 搜索空间可压缩（按 P_eff 排序后，极端值最可能入选）
- 物理约束通过 `simulate_sequential` 逐时模拟隐式满足
- 无需调用 LP/MILP 求解器，无外部依赖

**伪代码** (`optimize_arbitrage`):

```
function optimize_arbitrage(P_eff, params, soc_initial, max_charge_hours=6, 
                            max_discharge_hours=6, pool_size=12):
    best_profit = -inf
    
    // 1. 按 P_eff 排序
    sorted_asc = argsort(P_eff)         // 充电候选池（P_eff 最小）
    sorted_desc = argsort(-P_eff)       // 放电候选池（P_eff 最大）
    
    charge_pool = sorted_asc[:pool_size]    // 取前 pool_size 个
    discharge_pool = sorted_desc[:pool_size]
    
    // 2. 穷举充放电小时数 + 滑动窗口位置
    for n_charge in 1..max_charge_hours:
        for n_discharge in 1..max_discharge_hours:
            
            for ci in 0..(len(charge_pool)-n_charge):
                c_set = charge_pool[ci : ci+n_charge]
                
                for di in 0..(len(discharge_pool)-n_discharge):
                    d_set = discharge_pool[di : di+n_discharge]
                    
                    if c_set ∩ d_set: continue  // 同一小时不能同时充放
                    
                    load_ESS, SOC = simulate_sequential(c_set, d_set, params)
                    profit = Σ(load_ESS[h] × P_eff[h])
                    
                    if profit > best_profit:
                        best_profit = profit
                        best_result = (load_ESS, SOC)
    
    return best_result
```

**复杂度分析**：
- pool_size=12, max_charge_hours=6, max_discharge_hours=6
- 枚举量级：6×6 × Σ(n 个滑动窗口)≈ 36 × ~40 × ~40 ≈ 57,600 次
- 每次 `simulate_sequential` O(24)
- 总计算量：~1.4M 次操作 → 毫秒级完成

**参数调优建议**：
- `pool_size` 越大搜索越全面（默认 12，覆盖半天的小时）
- `max_charge_hours` / `max_discharge_hours` 受限于 P_max × hours ≤ Cap_rated × (SOC_max - SOC_min)
- 当前默认值 6 小时对于 0.5C × 5000kWh = 2500kW，满充需 5000×0.8/2500 = 1.6h，6 小时足够

### 9.5 逐时模拟算法

**伪代码** (`simulate_sequential`):

```
function simulate_sequential(hours_charge, hours_discharge, params, soc_initial):
    load_ESS = zeros(24)
    SOC = zeros(24)
    soc = soc_initial
    
    for h in 0..23:
        if h in charge_set and soc < SOC_max - ε:
            max_energy = min(
                P_max,
                (SOC_max - soc) × Cap_rated / η_single
            )
            load_ESS[h] = -max_energy
            soc += max_energy × η_single / Cap_rated
            
        elif h in discharge_set and soc > SOC_min + ε:
            max_energy = min(
                P_max,
                (soc - SOC_min) × Cap_rated × η_single
            )
            load_ESS[h] = max_energy
            soc -= max_energy / η_single / Cap_rated
        
        SOC[h] = soc
    
    return load_ESS, SOC
```

**约束保证**：
- 功率约束：`max_energy ≤ P_max` ✓
- SOC 约束：`max_energy` 受剩余容量限制 ✓
- 充放电互斥：`if-elif` 结构 + 调用方保证 `c_set ∩ d_set = ∅` ✓
- 效率：充电时 SOC 增量 = energy × η_single / Cap，放电时 SOC 减量 = energy / η_single / Cap ✓

### 9.6 金融计算

**年现金流选择** (`_annual_cashflow`):

| 模式 | 日现金流口径 | 减去年运维 | 逻辑 |
|------|------------|-----------|------|
| B1 | ess_revenue | 是 | 用户即储能投资商 |
| B2a/B2b/B2c | ess_revenue | 是 | 三方独立，储能投资商始终收取服务费 |
| B3a/B3b | combined_profit | 是 | 储售一体，组合体是储能投资商 |
| B4 | combined_profit | 是 | 统一实体 |

**NPV 计算**：考虑容量衰减对年现金流的影响，10 年折现。

**IRR 计算**：二分法搜索，范围 [-50%, 200%]，200 次迭代，容差 1e-6。年现金流为负时 IRR 可能无解（返回边界均值）。

### 9.7 已知局限与后续优化方向

| 局限 | 影响 | 优化方向 |
|------|------|---------|
| 当前仅搜索 1 天 | 日间 SOC 传递不考虑 | 扩展为 2 天（48h）搜索，首日优化+次日约束 |
| 排序+滑动窗口 | 可能遗漏非连续排名组合 | 改用 TOP-N 全组合枚举（需 n choose k 爆炸，pool_size 需控制） |
| 多日年化简化为 ×365 | 忽略日间波动 | 多日典型日加权 |
| 不含光伏 | 场景受限 | 负荷 net_load = load_real - PV_output |

---

## 10. 实施路线

### Phase 1：计算引擎完善（预计 1 个会话）

1. **`src/core/pricing.py`** — 实现 5 种电价模式计算
2. **`src/data/loader.py`** — 实现 DataLoader（含单位换算）
3. **`src/data/config.py`** — 实现 ConfigLoader
4. **`src/data/scenario.py`** — 实现 ScenarioManager
5. 编写 `tests/test_pricing.py` 和 `tests/test_scenario.py`

### Phase 2：Streamlit UI（预计 1 个会话）

1. **`app.py`** — 入口 + 页面导航
2. **`src/ui/state.py`** — Session state 初始化
3. **`src/ui/pages/params_page.py`** — 全局参数库页面
4. **`src/ui/pages/scenarios_page.py`** — 方案管理页面
5. **`src/ui/components/param_editor.py`** — 参数编辑组件
6. **`src/ui/components/dispatch_chart.py`** — 调度曲线图
7. **`src/ui/components/waterfall.py`** — 收益瀑布图
8. **`src/ui/components/metrics_table.py`** — 投资指标表
9. **`src/ui/pages/analysis_page.py`** — 单方案分析页面
10. **`src/ui/pages/compare_page.py`** — 多方案对比页面
11. 端到端测试：创建方案 → 计算 → 查看结果 → 对比

### Phase 3：打磨（预计 0.5 个会话）

1. 自定义 CSS 样式
2. 差异智能分析逻辑
3. 数据导出（CSV/Excel）
4. 错误处理和边界提示
5. 最终测试 + Bug 修复

---

## 附录 A：UI 配色与样式规范

| 元素 | 颜色 | 用途 |
|------|------|------|
| 充电 | `#1f77b4` (蓝) | load_ESS < 0 |
| 放电 | `#ff7f0e` (橙) | load_ESS > 0 |
| 负荷 | `#7f7f7f` (灰) | load_grid / load_real |
| SOC | `#2ca02c` (绿) | SOC 折线 |
| P_eff | `#d62728` (红虚线) | 价格信号 |
| 正值收益 | `#2ca02c` (绿) | 瀑布图 positive |
| 负值/成本 | `#d62728` (红) | 瀑布图 negative |

全局样式：
- 字体：系统等宽/无衬线混合
- 卡片背景：`#f8f9fa`（浅灰）
- 间距：st.columns gap="medium"

## 附录 B：错误处理清单

| 场景 | 处理方式 |
|------|---------|
| 选定的日期无负荷数据 | `st.error("所选日期无数据，请选择其他日期")` 并列出可用日期 |
| 电价表有缺口（某小时无匹配时段） | 数据加载时校验，`ValueError` + 提示 |
| 合约/日前数据日期不匹配 | 自动匹配或 fallback 到最近日期，给出 `st.warning` |
| 所有 P_eff 接近 0（无套利空间）| `st.info("当前价差极小，储能无套利空间，IRR 可能为负")` |
| IRR 无解（所有年现金流为负） | 显示"无法回收投资"，IRR 显示为 "N/A" |
| 方案文件损坏 | 捕获 JSONDecodeError，提示用户删除或修复 |
| 参数超出物理范围（如 SOC_min > SOC_max）| 滑块 min/max 约束 + 保存前校验 |

---

*文档版本 v1.0 | 2026-05-16 | 待用户审核*
