# 储能运营模拟计算器（ESS Simulator）

荷源网储售综合模拟仿真系统，用于模拟储能系统在电力市场环境下的运营策略，量化分析不同参数配置对储能收益的影响，辅助投资决策与方案对比。

---

## 功能概览

- **单方案分析** — 配置储能参数、电价模式、商业模式，运行仿真并查看详细的财务指标和时序曲线
- **多方案对比** — 并列对比多个方案的收益、现金流、运营指标，智能分析差异原因
- **方案管理器** — 保存、加载、复制、删除仿真方案，支持 JSON 格式导入导出
- **全局参数库** — 管理储能系统、光伏、金融、电价等默认参数

### 内置模型

| 模型 | 说明 |
|------|------|
| 电价模式 M1~M5 | 涵盖目录电价、合约电价、江苏模式、现货市场等多种电价结构 |
| 商业模式 B1~B4 | 用户侧削峰填谷、需量管理、现货套利、需求响应等 |
| 统一 P_eff 框架 | 储能充放电效率的通用推导框架 |
| 批发侧结算 | 中长期合约 + 日前现货 + 实时平衡的全链路结算模拟 |
| 金融指标 | IRR、NPV、投资回收期、LCOE 等完整评价体系 |

---

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | 原生 HTML/CSS/JS SPA |
| 图表 | ECharts |
| 计算引擎 | NumPy / SciPy / CVXPY |
| 后端 | FastAPI + Uvicorn |
| 数据存储 | CSV（配置）/ JSON（方案） |
| 测试 | pytest |
| 样式 | 自定义 CSS（深色主题） |

---

## 快速开始

### 环境要求

- Python 3.10+
- pip / conda

### 安装

```bash
# 克隆仓库
git clone https://github.com/jursber/ESS_simulink.git
cd ESS_simulink

# 创建虚拟环境（推荐）
python -m venv venv
# Windows: venv\Scripts\activate
# Linux/Mac: source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 运行

**启动应用：**

```bash
python run.py
```

浏览器打开 http://127.0.0.1:8000/

API 文档： http://127.0.0.1:8000/docs

---

## 项目结构

```
ESS_simulink/
├── run.py                  # FastAPI 启动脚本
├── requirements.txt        # Python 依赖
├── .gitignore
│
├── src/                    # 核心源码
│   ├── core/               # 计算引擎层
│   │   ├── calculator.py   #   主计算器
│   │   ├── dispatch.py     #   储能调度优化
│   │   ├── pricing.py      #   电价计算
│   │   ├── wholesale_settlement.py  # 批发侧结算
│   │   └── registry.py     #   公式/模型注册
│   ├── data/               # 数据访问层
│   │   ├── config.py       #   配置加载器
│   │   ├── loader.py       #   数据加载器
│   │   └── scenario.py     #   方案管理器
│   ├── models/             # 数据模型
│   │   ├── dispatch.py     #   调度模型
│   │   └── wholesale.py    #   批发结算模型
│   └── utils/              # 工具函数
│
├── api/                    # FastAPI 后端
│   ├── main.py
│   ├── routes.py
│   └── schemas.py
│
├── frontend/               # 前端 SPA（由 FastAPI 静态托管）
│   ├── index.html
│   ├── css/
│   └── js/
│
├── data/                   # 数据文件
│   ├── params/             # 全局参数默认值（储能、光伏、财务、批发结算）
│   ├── tariff/             # 分省/分类型电价数据
│   ├── spot_price/         # 分省现货价格（日前/实时统一出清价）
│   ├── dispatch_load/      # 分省统调负荷，用于中长期分解
│   ├── load/               # 用户典型负荷 profile，不按地区划分
│   ├── pv_curves/          # 分省/曲线类型光伏出力
│   ├── trading_strategy/   # 中长期/日前持仓 profile，不按地区划分
│   ├── demand_capacity/    # 分省需量/容量单价
│   ├── catalog/            # 数据可信度登记
│   └── scenarios/          # 方案 JSON 文件
│
├── tests/                  # 测试
│   ├── test_calculator.py
│   ├── test_dispatch_all.py
│   ├── test_integration.py
│   └── ...
│
├── Design/                 # 架构设计文档
├── docs/                   # 政策研究与文档
├── PRD/                    # 产品需求文档
├── scripts/                # 工具脚本
└── ui_prototype/           # UI 原型
```

---

## 运行测试

```bash
pytest tests/ -v
```

带覆盖率报告：

```bash
pytest tests/ --cov=src --cov-report=term-missing
```

---

## 配置说明

核心数据以 CSV 格式存储。当前目录口径如下：

| 路径 | 内容 |
|------|------|
| `data/params/ess_defaults.csv` | 储能系统默认参数（容量、功率、效率、成本等） |
| `data/params/pv_defaults.csv` | 光伏系统默认参数 |
| `data/params/financial_defaults.csv` | 金融计算默认参数（贴现率、年限等） |
| `data/params/wholesale_settlement.csv` | 批发侧结算默认参数 |
| `data/tariff/administrative_tariff/{region}/` | 分省行政分时电价 |
| `data/tariff/contract_tariff/` | 合同分时电价 profile |
| `data/tariff/flat_rate/` | 一口价 profile |
| `data/spot_price/{region}/` | 分省现货价格，保留日前统一出清价和实时统一出清价 |
| `data/dispatch_load/{region}/` | 分省统调负荷曲线，用于中长期分解 |
| `data/load/` | 用户典型负荷 profile，不按地区划分 |
| `data/pv_curves/{region}/` | 分省光伏出力曲线 |
| `data/trading_strategy/contract_position/{profile}/` | 中长期持仓策略 profile，不按地区划分 |
| `data/trading_strategy/dayahead_position/{profile}/` | 日前持仓策略 profile，不按地区划分 |
| `data/demand_capacity/{region}/` | 分省需量/容量单价 |
| `data/catalog/data_trust.csv` | 数据可信度登记，不记录敏感来源细节 |

---

## 文档索引

| 文档 | 位置 | 说明 |
|------|------|------|
| 产品需求文档 | `PRD/PRD_v1.0.3.md` | 冻结需求正文 |
| 架构设计 | `Design/architecture_v1.0.md` | 三层架构、技术选型、算法设计 |
| 版本变更日志 | `PRD/CHANGELOG.md` | 版本历史 |
| 实现日志 | `PRD/IMPLEMENTATION_LOG.md` | 代码实现登记 |
| 需求追溯矩阵 | `PRD/implementation_matrix.md` | PRD ↔ 代码 ↔ 测试 |
| 当前前端入口 | `docs/FRONTEND_ENTRYPOINT.md` | 真实前端与废弃入口说明 |
| 视觉规范 | `PRD/ui_spec_v1.md` | UI 设计规范 |
| 政策文档 | `docs/` | 电力市场政策研究 |

---

## 许可

MIT
