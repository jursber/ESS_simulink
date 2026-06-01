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
| UI 框架 | Streamlit |
| 图表 | Plotly Express |
| 计算引擎 | NumPy / SciPy / CVXPY |
| API 后端 | FastAPI + Uvicorn |
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

**Streamlit 应用（主界面）：**

```bash
streamlit run app.py
```

浏览器打开 http://localhost:8501

**API 后端（可选）：**

```bash
python run.py
```

浏览器打开 http://localhost:8000/docs（Swagger）

---

## 项目结构

```
ESS_simulink/
├── app.py                  # Streamlit 入口
├── run.py                  # FastAPI 启动脚本
├── requirements.txt        # Python 依赖
├── .gitignore
│
├── src/                    # 核心源码
│   ├── core/               # 计算引擎层（无 Streamlit 依赖）
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
│   ├── ui/                 # UI 层
│   │   ├── state.py        #   会话状态管理
│   │   ├── components/     #   可复用 UI 组件
│   │   └── pages/          #   页面
│   └── utils/              # 工具函数
│
├── api/                    # FastAPI 后端
│   ├── main.py
│   ├── routes.py
│   └── schemas.py
│
├── frontend/               # 静态前端原型
│   ├── index.html
│   ├── css/
│   └── js/
│
├── data/                   # 数据文件
│   ├── config/             # CSV 配置文件（电价、参数默认值等）
│   ├── processed/          # 处理后数据
│   ├── raw/                # 原始数据
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

核心配置数据位于 `data/config/` 目录，以 CSV 格式存储：

| 文件 | 内容 |
|------|------|
| `ess_defaults.csv` | 储能系统默认参数（容量、功率、效率、成本等） |
| `pv_defaults.csv` | 光伏系统默认参数 |
| `financial_defaults.csv` | 金融计算默认参数（贴现率、年限等） |
| `tariff_admin_henan.csv` | 河南目录电价 |
| `tariff_contract_henan.csv` | 河南合约电价 |
| `tariff_jiangsu_mode_henan.csv` | 河南江苏模式电价 |
| `system_load_henan.csv` | 河南系统负荷曲线 |
| `contract_position_henan.csv` | 中长期合约持仓 |
| `dayahead_position_henan.csv` | 日前现货持仓 |
| `pv_curves.csv` | 光伏出力曲线 |
| `wholesale_settlement_defaults.csv` | 批发侧结算默认参数 |

---

## 文档索引

| 文档 | 位置 | 说明 |
|------|------|------|
| 产品需求文档 | `PRD/PRD_v1.0.3.md` | 冻结需求正文 |
| 架构设计 | `Design/architecture_v1.0.md` | 三层架构、技术选型、算法设计 |
| 版本变更日志 | `PRD/CHANGELOG.md` | 版本历史 |
| 实现日志 | `PRD/IMPLEMENTATION_LOG.md` | 代码实现登记 |
| 需求追溯矩阵 | `PRD/implementation_matrix.md` | PRD ↔ 代码 ↔ 测试 |
| 视觉规范 | `PRD/ui_spec_v1.md` | UI 设计规范 |
| 政策文档 | `docs/` | 电力市场政策研究 |

---

## 许可

MIT
