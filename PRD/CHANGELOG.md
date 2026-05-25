# PRD 版本变更日志

| PRD 版本 | 对话轮次 | 日期 | 变更摘要 |
|----------|----------|------|----------|
| v1.1.1 | 视觉返工落地 | 2026-05-25 | 规范与 mock 落盘至 `PRD/ui_spec_v1.md`、`PRD/ui_mock_v1.svg`；按工业线框风重写 `style.py` / `blocks.py` / `analysis_page.py`（2×2 栅格、纯白背景、亲密性、Plotly 透明底、无阴影）。详见 IMPLEMENTATION_LOG §IML-20260525-001 |
| v1.1.0 | 前端视觉重建 | 2026-05-23 | 新增前端视觉层（Ant Design 5 token，蓝色主色，整屏无滚动，字号 12~18px）：新增 `src/ui/components/style.py / blocks.py / topology.py`；重写 [app.py](../app.py) 顶栏与左导航；按原型三列重写 [analysis_page.py](../src/ui/pages/analysis_page.py)；其余三页套外壳。不动 `src/core/**`、测试与方案 JSON。详见 [IMPLEMENTATION_LOG.md](IMPLEMENTATION_LOG.md) §IML-20260523-002 |
| v1.0.4 | 文档体系 / 项目梳理 | 2026-05-23 | 新增 `VERSIONING.md`、`SESSION_LOG.md`、`IMPLEMENTATION_LOG.md`、`implementation_matrix.md`、`README.md`；`PRD_v1.0.1.md` 更名为 `PRD_v1.0.3.md` 与正文一致；`Design/architecture_v1.0.md` 与当前代码对齐。PRD **正文**仍为 v1.0.3 冻结，见 [VERSIONING.md](VERSIONING.md) |
| v1.0.3 | 第 7 轮（补充） | 2026-05-22 | 澄清：§6.2 中长期/日前持仓 CSV 按方案 `date` 筛选 24 小时后再参与购电公式；实现于 `ConfigLoader` + `calculate` |
| v1.0.2 | 第 7 轮 | 2026-05-16 | 修正：§5.6 UnitCost 注释恢复正确值；§5.7 重写为统一 P_eff 框架；§4 B1 澄清自动优化；§4 B2 增加 B2a 反常套利警示；§10.B 补充 r_user(B3)=40%；修复 `_annual_cashflow` B2c/B3b 口径错误 |
| v1.0.1 | 第 6 轮 | 2026-05-16 | 修正：运维成本 1.5%→1%，UnitCost 0.9 元/Wh，新增全局参数页面+方案私有参数+复制参数机制 |
| v1.0.0 | 第 0~5 轮 | 2026-05-16 | 初始版本：物理模型、5种电价模式(M1~M5)、4种商业模式(B1~B4)、完整公式体系（用户/售电/储能/投资评价）、数据清单、架构原则、Web交互需求 |

---

**版本号规则**（摘要；细则与交互/实现分工见 [VERSIONING.md](VERSIONING.md)）：

- **X.0.0**：不兼容变化（结算/物理口径、旧数据语义失效等）。
- **0.X.0**：向后兼容的新能力（新模式、新页面、新配置维度等）。
- **0.0.X**：澄清、修正、数据口径微调、纯测试/无行为重构；**仅文档体系**（SESSION/IMPLEMENTATION/矩阵）也可记为文档类发布行。

**说明**：表内 **v1.0.4** 为「仓库文档与协作治理」发布标签；**需求冻结正文**仍以 `PRD_v1.0.3.md` 内标题为准，直至下次正文升版。
