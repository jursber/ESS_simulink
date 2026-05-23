# 代码实现登记（IMPLEMENTATION_LOG）

> 规则：每次完成**代码层级**交付后追加一节；纯文档梳理若涉及仓库内文件增删改，也可记一条便于审计。  
> 详见证：[VERSIONING.md](VERSIONING.md)

---

## IML-20260523-001 — 项目梳理（文档与 PRD 体系）

- **类型**：文档 / 仓库结构（无应用逻辑代码变更）。
- **关联**：PRD 治理约定 [VERSIONING.md](VERSIONING.md)；CHANGELOG **v1.0.4** 文档体系条目。
- **变更摘要**：
  - 新增：`PRD/VERSIONING.md`、`PRD/SESSION_LOG.md`、`PRD/IMPLEMENTATION_LOG.md`、`PRD/implementation_matrix.md`、`PRD/README.md`。
  - 重命名：`PRD/PRD_v1.0.1.md` → `PRD/PRD_v1.0.3.md`；正文内增加规范文件名说明。
  - 更新：`PRD/CHANGELOG.md`（v1.0.4）、`PRD/requirements.md`（Backlog 说明）、`Design/architecture_v1.0.md`（目录与模块状态与仓库一致）。
- **未改**：`src/**` 下 Python 源码（本轮不做行为变更）。

---

## IML-20260523-002 — 前端视觉框架重建对齐原型（v1.1.0）

- **类型**：前端视觉层重建（UI/CSS/HTML，不动业务逻辑）。
- **关联**：CHANGELOG **v1.1.0**；原型基准图 `assets/c__Users_..._image-a33f6516-840b-4d58-92e6-c5367e414590.png`；PRD §9 Web 交互需求。
- **变更摘要**：
  - **新增**：
    - [src/ui/components/style.py](../src/ui/components/style.py)：Ant Design 5 风格 token + 整屏无滚动 CSS + Streamlit 控件覆盖（字号 12~18px、`#1677FF` 蓝色主色、`.card / .kv-row / .pl-row / .metric-strip / .section-title / .tbl` 等工具类）。
    - [src/ui/components/blocks.py](../src/ui/components/blocks.py)：`card / section_title / kv_row / kv_block / pl_row / metric_strip / simple_table / view_button / plus_button / topbar`。
    - [src/ui/components/topology.py](../src/ui/components/topology.py)：拓扑示意 SVG（电网 → 售电公司 → 用户 / 储能 + 关口标识）。
  - **重写**：
    - [app.py](../app.py)：顶栏 44px（标题居中 + 加载/保存/重置）、左导航 4 项 + 底部「☐ 默认参数」、保留 `header_save_requested / AppState.invalidate` 钩子。
    - [src/ui/pages/analysis_page.py](../src/ui/pages/analysis_page.py)：按原型三列重写视觉层；保留 `try_header_save / _init_analysis_session / _build_work_config / _build_wholesale_from_session / _build_save_dict` 接口及全部 session key 命名规则；新增三个 UI 局部 session key：`analy_<sid>_user_profile / coop_mode / share_ratio / show_b3a / show_b2a / show_b4`。
    - 内部辅助：`_wh_select`（保留批发结算下拉 + 查看按钮）、`_simple_select_with_view`、`_mini_bar`（多方收益小柱图）。
  - **轻改**：
    - [src/ui/pages/compare_page.py](../src/ui/pages/compare_page.py)、[scenarios_page.py](../src/ui/pages/scenarios_page.py)、[params_page.py](../src/ui/pages/params_page.py)：把主体 body 抽成 `_run()`，外层套 `with card(title=...)`；内容不重排。
- **不动**：`src/core/**`、`src/data/**`、`src/models/**`、`tests/**`、`data/**`、方案 JSON 结构。
- **验证**：
  - `pytest tests/`：**129 passed**（覆盖率与之前一致）。
  - `python -c "import app"`：导入零错误。
  - `streamlit run app.py --server.port 8520`：HTTP 200。
  - **人工待验**：1366×768 与 1920×1080 浏览器中确认整屏不滚动（应用已起在 `http://localhost:8520/`）。
- **已知 UI 占位**（下一轮可补）：
  - 三复选框「储售投资一体 / 售电公司套利 / 总社会福利最高」只 UI 切换，不接入多商业模式联合计算；
  - 右栏"查看"按钮使用 `st.toast` 占位；
  - "自定义参数 ＋" 入口仅 `st.toast`；
  - 拓扑图为静态 SVG，可后续替换为 Plotly Sankey；
  - "默认参数"按钮清理 widget session，但不写盘。
