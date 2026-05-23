# ESS_simulink — 储能运营模拟计算器

## 项目概述

构建一个储能运营模拟计算器，计算在不同电价模式（电力市场、行政分时电价等）、
不同主体（售电公司、储能投资商、终端用户等）、不同商业模式下的综合收益。
核心目的是帮助用户理解所有外部条件如何传导到储能收益。

## 技术栈

- Python 3.14+（虚拟环境：`venv/`）
- 数据处理：pandas, numpy
- 优化求解：scipy, cvxpy
- 可视化：matplotlib, seaborn, plotly
- UI 交互：streamlit
- 测试：pytest

## 项目结构

```
ESS_simulink/
├── PRD/              # 需求冻结、CHANGELOG、交互/实现日志、追溯矩阵（见 PRD/README.md）
├── data/
│   ├── raw/          # 原始输入数据（电价曲线、负荷曲线等）
│   └── processed/    # 清洗/转换后的数据
├── src/
│   ├── core/         # 核心计算引擎（调度优化、收益计算）
│   ├── models/       # 数据模型定义（pydantic）
│   ├── utils/        # 工具函数（数据加载、时间处理等）
│   └── ui/           # Streamlit 界面
├── tests/            # 单元测试和集成测试
├── docs/             # 文档
├── notebooks/        # Jupyter 探索性分析
├── scripts/          # 一次性脚本
├── venv/             # Python 虚拟环境
├── CLAUDE.md         # 本文件
└── requirements.txt  # Python 依赖
```

## 开发规范

### 代码风格
- 类型标注：所有公共函数必须标注参数和返回值类型
- 命名：类用 PascalCase，函数/变量用 snake_case，常量用 UPPER_SNAKE_CASE
- 文档：公共 API 用简洁的中文 docstring

### 数据模型
- 使用 pydantic 定义核心数据结构（电价方案、储能参数、收益结果等）
- 所有金额单位为"元"，能量单位为"kWh"，功率单位为"kW"

### 计算引擎设计原则
- 每个电价模式作为独立策略（Strategy 模式）
- 优化调度与收益计算分离
- 参数可配置化，方便对比不同场景

### Git 规范
- 提交信息用中文
- 数据文件不入库（除极小样本外）
```

## 交互约定

- 实施计划、分析总结用中文
- 先讨论方案再写代码
- 保持代码简洁，不过早抽象
