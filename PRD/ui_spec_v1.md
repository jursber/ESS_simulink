# 单方案分析页 — 视觉规范 v1.1（工业线框风）

| 项 | 内容 |
|----|------|
| 版本 | v1.1（与 CHANGELOG **v1.1.1** 视觉返工对齐） |
| 状态 | **仓库内规范真源**（后续改 UI 须先改本文再改代码） |
| 关联 Cursor Plan | `C:\Users\Administrator\.cursor\plans\视觉规范与mock先行重做_c0fdccaa.plan.md`（讨论稿；**以本文件 + `PRD/ui_mock_v1.svg` 为准**） |
| 静态 Mock | [ui_mock_v1.svg](ui_mock_v1.svg) |
| 实现落点 | `src/ui/components/style.py`、`blocks.py`、`src/ui/pages/analysis_page.py`、`app.py` |

---

## 1. 问题定位与对策（摘要）

| 现象 | 对策 |
|------|------|
| 下方大块留白 | 中部 2×2 栅格；卡片在栅格内 `height: 100%` / `flex:1`，填满可视高度 |
| 标签与数值过远（亲密性） | `.kv-row`、`.pl-row` 左对齐 + 固定 `gap`，禁止 `space-between` 拉散 |
| 「批发市场」与「批发购电规则」重叠 | 取消对 Streamlit `label` 的强制 `height`；`.section-title` 固定 24px 行高 + 明确上下 margin |
| 白图 + 灰底突兀 | 页面与卡片背景统一 `#FFFFFF`；Plotly `paper_bgcolor` / `plot_bgcolor` 透明 |
| 规范不落盘 | 规范与 mock **必须**保存在本仓库 `PRD/`（用户新要求） |

---

## 2. 视觉基线（锁死）

**风格**：工业线框风（engineering wireframe）— 白底、1px 细灰描边、信息密度优先、**无阴影**。

### 2.1 Design Tokens（CSS 变量名建议）

| Token | 值 | 用途 |
|-------|-----|------|
| `--primary` | `#1677FF` | 主按钮、激活态、强调数值、财务条主值 |
| `--text-1` | `#1F1F1F` | 主文案 |
| `--text-2` | `#595959` | 次级 |
| `--text-3` | `#8C8C8C` | 弱文案、KV 标签 |
| `--bg-page` | `#FFFFFF` | **整页背景（纯白）** |
| `--bg-strip` | `#FAFBFC` | 指标条、表头浅底 |
| `--bg-card` | `#FFFFFF` | 卡片填充 |
| `--border` | `#E5E7EB` | 卡片与控件描边 |
| `--divider` | `#F0F0F0` | 卡片内分隔 |
| `--radius` | `4px` | 圆角 |
| 阴影 | **无** | `box-shadow: none` |
| 卡片/列间距 | `6px` | 横向、纵向一致 |
| 字号 | `12 / 13 / 14 / 16` px | 最小 **12**；不用 18/22 作正文 |
| 字体栈 | `-apple-system, "PingFang SC", "Microsoft YaHei", "Segoe UI", Roboto, sans-serif` | |

### 2.2 布局尺寸（1920×1080 视口基准）

| 区域 | 高度/宽度 |
|------|-----------|
| TopBar | **40px** 固定高 |
| Body | `calc(100vh - 40px - 8px)`（顶栏下留 8px 与主体衔接） |
| LeftNav | **84px** 宽（导航列比例由 `app.py` 与 CSS 共同约束） |
| ParamPanel（右栏） | **280px** 量级（列宽约 `0.22` 总宽或固定 min-width） |
| Center | 剩余宽度；内部 **两行各 50% 高** |

---

## 3. 一屏 Grid 蓝图

视口内容区约 **1920×960**。

```
┌─ TopBar 40px —────────────────────────────────────────────────────────────┐
│ [荷源网储售…]                    [加载] [保存] [重置]                      │
├────┬──────────────────────────────────────────────────────────────┬───────┤
│Nav │  Row1 50% h                                                 │ Param │
│84  │  ┌────────────────────┬────────────────────┐                │ 280   │
│    │  │ 方案概览           │ 多方收益分析        │                │       │
│    │  │ 下拉+拓扑+指标条   │ 终端/储售+柱图      │                │       │
│    │  └────────────────────┴────────────────────┘                │       │
│    │  Row2 50% h                                                 │       │
│    │  ┌────────────────────┬────────────────────┐                │       │
│    │  │ 储能本体建设收益    │ 典型日调度曲线      │                │       │
│    │  │ 基本参数/财务/经营  │ 大图                │                │       │
│    │  └────────────────────┴────────────────────┘                │       │
└────┴──────────────────────────────────────────────────────────────┴───────┘
```

与 Plan 中 mermaid 一致：**先上「概览 | 多方收益」，再下「储能本体 | 调度」**（与 v1.1.0 代码中「左列上下、中列上下」对调）。

---

## 4. 亲密性规则

| 组件 | 规则 |
|------|------|
| `.kv-row` | `display:flex; align-items:baseline; justify-content:flex-start; gap:8px;` 标签与数值紧挨 |
| `.pl-row` | 圆点 + 标签 + 数值左起横向排列，`gap: 6px` / 数值与标签 `4px`；数值 `#1677FF`、`font-weight:600`、`13px` |
| `.metric-strip` | 等分单元格可居中；单元内上值下说明 |
| `.fin-strip` | 三宫格；上灰小字标签、下主色加粗数值，垂直间距 ≤4px |
| `.section-title` | 高 24px，`margin: 8px 0 6px`；左侧 3px 主色条 |

---

## 5. Streamlit 控件与「查看」

- **禁止**对 `[data-testid="stSelectbox"] label` 等设置固定 `height` / `min-height`（避免与 `.section-title` 抢行高）。
- 「查看」与下拉：**同一行内**用两列 `[1, 0.22]`；**不使用** `.view-link { margin-top: 18px }`；查看列用 flex 底对齐或 `align-self: end` 与控件区对齐（见 `style.py`）。
- 右栏分组顺序：批发市场 → 零售 → 储能合作 → 自定义参数。

---

## 6. Plotly

- `paper_bgcolor: "rgba(0,0,0,0)"`，`plot_bgcolor: "rgba(0,0,0,0)"`。
- 柱/线主色 `#1677FF`，第二套 `#52C41A`；网格 `#F0F0F0`；`font.size` 10 左右。
- `margin` 紧凑：`dict(l=8, r=8, t=8, b=24)`（小图可略减底边）。

---

## 7. 元素 → 代码映射

| UI 元素 | 实现 |
|---------|------|
| 顶栏 | `app.py` + `.st-key-topbar` |
| 左导航 | `app.py` + `.st-key-nav` / `navitem_*` |
| 卡片外壳 | `blocks.card` + `.card` / `.card-title` |
| 方案概览 | `analysis_page` 上行左格 |
| 多方收益 | `analysis_page` 上行右格 |
| 储能本体 | `analysis_page` 下行左格 |
| 调度曲线 | `analysis_page` 下行右格 |
| 右栏参数 | `analysis_page` `right_col` |

---

## 8. 范围外（本轮不改）

- `src/core/**`、`src/data/**`、`src/models/**`、`tests/**` 行为与口径不变。
- 「查看」真实弹窗、自定义参数业务逻辑可继续占位。
