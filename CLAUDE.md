# ESS_simulink — 储能运营模拟计算器

## 项目概述

储能运营模拟计算器，计算在不同电价模式（行政分时、合同分时、现货联动等）、
不同主体（售电公司、储能运营商、终端用户等）、不同商业模式下的综合收益。
核心目的是帮助用户理解所有外部条件如何传导到储能/光伏收益。

## 技术栈

- Python 3.11+（虚拟环境由 uv/hermes 管理）
- 后端：FastAPI + uvicorn（端口 8000）
- 前端：纯 HTML/CSS/JS + ECharts 5.5.0（CDN），暗色主题仪表盘
- 数据处理：pandas, numpy
- 优化求解：scipy
- 可视化：plotly（Streamlit）、ECharts（前端 SPA）
- UI 交互：streamlit（旧版，逐步迁移到前端 SPA）
- 测试：pytest

## 项目结构

```
ESS_simulink/
├── api/                    # FastAPI 后端
│   ├── main.py             # 应用入口，CORS，挂载前端静态文件
│   ├── routes.py           # 所有 API 端点
│   └── schemas.py          # Pydantic 请求/响应模型
├── data/
│   ├── raw/                # 原始输入数据（逐分钟电价、设备负荷）
│   ├── processed/          # 清洗后数据（逐时电价、负荷）
│   ├── config/             # 配置 CSV（ESS、电价、批发、光伏等）
│   └── scenarios/          # 方案 JSON 文件
├── frontend/               # 前端 SPA（FastAPI 静态托管）
│   ├── index.html          # HTML 骨架
│   ├── css/style.css       # 全局样式
│   └── js/                 # JS 模块（app/analysis/charts/flow/params/compare）
├── src/
│   ├── core/               # 核心计算引擎
│   │   ├── calculator.py   # 统一计算入口 calculate()
│   │   ├── dispatch.py     # 调度优化（滑窗穷举）
│   │   ├── pricing.py      # 电价模式计算（M1~M5）
│   │   └── wholesale_settlement.py  # 批发结算（广东/广西/山西/山东）
│   ├── models/             # 数据模型（dataclass）
│   │   ├── dispatch.py     # ESSParams, HourlyData, DispatchResult, 枚举
│   │   └── wholesale.py    # WholesaleSettlementConfig
│   ├── data/               # 数据加载层
│   │   ├── config.py       # ConfigLoader（CSV 读写）
│   │   ├── loader.py       # DataLoader（processed 数据）
│   │   └── scenario.py     # ScenarioManager（方案 CRUD）
│   ├── ui/                 # Streamlit 界面（旧版，逐步废弃）
│   └── utils/              # 工具函数
├── tests/                  # 单元测试
├── scripts/                # 数据处理脚本
├── run.py                  # python run.py 启动 FastAPI
├── CLAUDE.md               # 本文件
└── requirements.txt        # Python 依赖
```

## 启动方式

```bash
python run.py   # 启动 FastAPI，http://127.0.0.1:8000
```

前端通过 FastAPI 静态托管，访问 `http://127.0.0.1:8000/` 即可。

## 计算流程

```
POST /api/calculate
  → routes.py: run_calculation()
    → calculator.py: calculate(config, wholesale_cfg)
      → DataLoader 加载电价/负荷数据
      → ConfigLoader 加载 ESS/财务/电价配置
      → pricing.py: compute_user_price() → P_user[24]
      → dispatch.py: run_dispatch()
        → compute_effective_price() → P_eff[24]
        → optimize_arbitrage() → load_ESS[24], SOC[24]
        → 收益分解 + 批发结算 + 投资指标
      → DispatchResult
    → _build_response() → CalculateResponse JSON
```

## 前端架构

前端为纯 JS SPA，通过 `App` 命名空间通信：

```javascript
window.App = {
  state: {},           // 全局状态
  api: fn,             // API 调用封装
  charts: {},          // ECharts 图表函数
  flow: {},            // 能量流动图
  analysis: {},        // 单方案分析页
  params: {},          // 缺省参数页
  compare: {}          // 多方案对比页
};
```

HTML 内联 onclick 通过全局代理转发，例如：
```javascript
window.runCalculation = () => App.analysis.runCalculation();
```

## 开发规范

### 代码风格
- 类型标注：所有公共函数必须标注参数和返回值类型
- 命名：类用 PascalCase，函数/变量用 snake_case，常量用 UPPER_SNAKE_CASE
- 文档：公共 API 用简洁的中文 docstring

### 数据模型
- 使用 dataclass 定义核心数据结构（ESSParams、HourlyData、DispatchResult 等）
- 所有金额单位为"元"，能量单位为"kWh"，功率单位为"kW"
- CSV 配置文件格式：param, value, unit, editable

### 计算引擎设计原则
- 每个电价模式作为独立策略（pricing.py）
- 优化调度与收益计算分离（dispatch.py vs calculator.py）
- 参数可配置化，方便对比不同场景

### Git 规范
- 提交信息用中文
- 数据文件不入库（除极小配置 CSV 外）
- **禁止自动 push**：未经用户明确指示，不执行 git push

### 前端规范
- 深色主题，CSS 变量定义在 `:root`
- ECharts 图表统一样式：tooltip 背景 #1e2330，线宽 0.5，横坐标 0~23 全显示
- 表格居中，表头加粗
- 输入框样式：深色底 #1a1f2d，蓝色边框聚焦

## 交互约定

- **所有输出、计划、分析使用中文**（除非用户明确要求英文）
- 先讨论方案再写代码
- 保持代码简洁，不过早抽象
- 修改参数后切换页面需提示未保存
- 重置按钮需确认弹窗

## 当前状态

- 单方案分析：完整（方案概览、多方收益、光储投资分析、调度曲线）
- 缺省参数：完整（5 分类 16 子项，左右分栏）
- 多方案对比：待实现
- 方案管理：待实现
- 光伏模块：参数框架已实现，计算逻辑待接入

## 并行开发规则（两个 Claude 窗口同时工作时）

**如果你是第二个打开此项目的 Claude 窗口，请先提示用户确认文件分工，避免冲突。**

前端已拆分为独立 JS 模块，分工如下：

| 负责方 | 文件 |
|--------|------|
| Session 1（单方案分析） | `js/analysis.js`, `js/charts.js`, `js/flow.js` |
| Session 2（缺省参数） | `js/params.js` |
| 共享（禁止同时编辑） | `js/app.js`, `css/style.v4.css`, `index.html`, `api/routes.py` |

- 任一方编辑共享文件前，必须先确认另一方没有在编辑
- 重启服务前确认对方不在编辑状态
- 新增 API 端点由一方集中添加

## 其他奇怪的要求
- 每次回复正文之后，都在最后面加上一句 "Over！"