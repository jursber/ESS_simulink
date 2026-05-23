"""全局 UI 样式 token 与 Streamlit 控件覆盖。

设计基线：Ant Design 5（Light）视觉 token；蓝色主色、工业风、亮色主题、最小字号 12px。
通过 `inject_global_css()` 在 app 入口注入一次，先于任何页面渲染。
"""
from __future__ import annotations

import streamlit as st


# ---- 设计 token ---------------------------------------------------------

PRIMARY = "#1677FF"
PRIMARY_HOVER = "#4096FF"
PRIMARY_ACTIVE = "#0958D9"
DANGER = "#FF4D4F"
SUCCESS = "#52C41A"
WARNING = "#FAAD14"

TEXT_PRIMARY = "#1F1F1F"
TEXT_REGULAR = "#595959"
TEXT_SECONDARY = "#8C8C8C"
TEXT_DISABLED = "#BFBFBF"

BORDER = "#D9D9D9"
DIVIDER = "#F0F0F0"
BG_PAGE = "#F5F7FA"
BG_CARD = "#FFFFFF"
BG_HOVER = "#FAFAFA"

RADIUS = "6px"
SHADOW = "0 1px 2px rgba(0,0,0,.04)"

TOPBAR_H = 44
LEFTNAV_W = 96
RIGHTPANEL_W = 290


# ---- CSS ----------------------------------------------------------------

_CSS = f"""
<style>
  :root {{
    --primary: {PRIMARY};
    --primary-hover: {PRIMARY_HOVER};
    --primary-active: {PRIMARY_ACTIVE};
    --danger: {DANGER};
    --success: {SUCCESS};
    --warning: {WARNING};
    --text-1: {TEXT_PRIMARY};
    --text-2: {TEXT_REGULAR};
    --text-3: {TEXT_SECONDARY};
    --text-4: {TEXT_DISABLED};
    --border: {BORDER};
    --divider: {DIVIDER};
    --bg-page: {BG_PAGE};
    --bg-card: {BG_CARD};
    --bg-hover: {BG_HOVER};
    --radius: {RADIUS};
    --shadow: {SHADOW};
    --fs-12: 12px;
    --fs-13: 13px;
    --fs-14: 14px;
    --fs-16: 16px;
    --fs-18: 18px;
    --fs-22: 22px;
    --topbar-h: {TOPBAR_H}px;
    --leftnav-w: {LEFTNAV_W}px;
    --rightpanel-w: {RIGHTPANEL_W}px;
  }}

  html, body {{
    height: 100vh;
    overflow: hidden;
    font-family: -apple-system, "PingFang SC", "Microsoft YaHei", "Segoe UI", Roboto, sans-serif;
    color: var(--text-1);
    background: var(--bg-page);
    font-size: var(--fs-13);
    line-height: 1.45;
  }}

  [data-testid="stAppViewContainer"] {{
    height: 100vh;
    overflow: hidden;
    background: var(--bg-page);
  }}
  [data-testid="stHeader"],
  [data-testid="stToolbar"],
  [data-testid="stDecoration"],
  [data-testid="stStatusWidget"],
  #MainMenu, footer, .stDeployButton {{
    display: none !important;
    visibility: hidden !important;
  }}

  [data-testid="stMain"] {{
    height: 100vh;
    overflow: hidden;
    padding: 0 !important;
  }}
  [data-testid="stMainBlockContainer"] {{
    max-width: 100% !important;
    padding: 0 !important;
    height: 100vh !important;
    overflow: hidden !important;
  }}
  [data-testid="stVerticalBlock"] {{
    gap: 4px !important;
  }}
  [data-testid="stHorizontalBlock"] {{
    gap: 6px !important;
    align-items: stretch !important;
  }}
  [data-testid="stElementContainer"] {{
    margin: 0 !important;
  }}

  h1, h2, h3, h4, h5 {{
    color: var(--text-1);
    margin: 0 0 4px 0 !important;
    padding: 0 !important;
    font-weight: 600;
    line-height: 1.3;
  }}
  h1 {{ font-size: var(--fs-18) !important; }}
  h2 {{ font-size: var(--fs-16) !important; }}
  h3 {{ font-size: var(--fs-14) !important; }}
  h4, h5 {{ font-size: var(--fs-13) !important; }}

  p, li, label, span, div {{ font-size: var(--fs-13); }}
  .stCaption, [data-testid="stCaptionContainer"] {{
    color: var(--text-3) !important;
    font-size: var(--fs-12) !important;
  }}

  /* ---- 顶栏：st.container(key="topbar") 渲染为 .st-key-topbar ---- */
  .st-key-topbar {{
    height: var(--topbar-h);
    background: var(--bg-card);
    border-bottom: 1px solid var(--border);
    margin: 0 0 8px 0;
    padding: 0 16px;
  }}
  .st-key-topbar [data-testid="stHorizontalBlock"] {{
    height: var(--topbar-h);
    align-items: center !important;
    gap: 8px !important;
  }}
  .st-key-topbar [data-testid="stColumn"] {{
    display: flex;
    align-items: center;
  }}
  .st-key-topbar [data-testid="stColumn"]:nth-child(2) {{
    justify-content: center;
  }}
  .st-key-topbar [data-testid="stColumn"]:nth-child(3) {{
    justify-content: flex-end;
  }}
  .topbar-title {{
    font-size: var(--fs-16);
    font-weight: 600;
    color: var(--text-1);
    letter-spacing: 0.02em;
    text-align: center;
    width: 100%;
  }}
  .st-key-topbar [data-testid="stButton"] button {{
    font-size: var(--fs-12);
    padding: 2px 10px;
    height: 28px;
    min-height: 28px;
    background: var(--bg-card);
    color: var(--text-2);
    border: 1px solid var(--border);
    border-radius: 4px;
    width: 100%;
  }}
  .st-key-topbar [data-testid="stButton"] button:hover {{
    color: var(--primary);
    border-color: var(--primary);
  }}

  /* ---- 主体区 ---- */
  .st-key-body {{
    padding: 0 10px;
    height: calc(100vh - var(--topbar-h) - 16px);
    overflow: hidden;
  }}

  /* ---- 卡片 ---- */
  .card {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    padding: 8px 10px;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    margin-bottom: 6px;
  }}
  .card-title {{
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    font-size: var(--fs-14);
    font-weight: 600;
    color: var(--text-1);
    margin-bottom: 4px;
    padding-bottom: 4px;
    border-bottom: 1px solid var(--divider);
  }}
  .card-title .sub {{
    font-size: var(--fs-12);
    color: var(--text-3);
    font-weight: 400;
  }}
  .card-title .right {{
    font-size: var(--fs-12);
    color: var(--text-3);
    font-weight: 400;
  }}

  /* ---- 键值行 ---- */
  .kv-row {{
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    padding: 2px 0;
    font-size: var(--fs-13);
    line-height: 1.5;
    border-bottom: 1px dashed transparent;
  }}
  .kv-row .k {{
    color: var(--text-3);
    margin-right: 8px;
    white-space: nowrap;
    font-size: var(--fs-12);
  }}
  .kv-row .v {{
    color: var(--text-1);
    font-weight: 500;
    text-align: right;
    white-space: nowrap;
  }}
  .kv-row .u {{
    color: var(--text-3);
    font-size: var(--fs-12);
    margin-left: 2px;
    font-weight: 400;
  }}

  /* 财务指标条（紧凑横排，每项 label/value 上下结构） */
  .fin-strip {{
    display: flex;
    gap: 8px;
    background: var(--bg-hover);
    border: 1px solid var(--divider);
    border-radius: var(--radius);
    padding: 8px;
    margin-top: 4px;
  }}
  .fin-strip .cell {{
    flex: 1;
    text-align: center;
    padding: 0 4px;
  }}
  .fin-strip .cell + .cell {{ border-left: 1px solid var(--divider); }}
  .fin-strip .cell .k {{
    font-size: var(--fs-12);
    color: var(--text-3);
    margin-bottom: 2px;
    line-height: 1.3;
  }}
  .fin-strip .cell .v {{
    font-size: var(--fs-16);
    font-weight: 600;
    color: var(--primary);
    line-height: 1.3;
  }}

  /* 收益条目（带左圆点） */
  .pl-row {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 3px 0;
    font-size: var(--fs-13);
    line-height: 1.5;
  }}
  .pl-row .k {{
    color: var(--text-2);
    display: flex;
    align-items: center;
    gap: 6px;
  }}
  .pl-row .k::before {{
    content: "";
    display: inline-block;
    width: 6px; height: 6px;
    border-radius: 50%;
    background: var(--primary);
    flex-shrink: 0;
  }}
  .pl-row .v {{
    color: var(--text-1);
    font-weight: 600;
    font-size: var(--fs-13);
  }}

  /* ---- 指标条 ---- */
  .metric-strip {{
    display: flex;
    align-items: stretch;
    gap: 0;
    background: var(--bg-hover);
    border: 1px solid var(--divider);
    border-radius: var(--radius);
    padding: 6px 0;
    margin-top: 4px;
  }}
  .metric-strip .cell {{
    flex: 1;
    text-align: center;
    border-right: 1px solid var(--divider);
    padding: 0 4px;
  }}
  .metric-strip .cell:last-child {{ border-right: none; }}
  .metric-strip .cell .v {{
    font-size: var(--fs-14);
    font-weight: 600;
    color: var(--text-1);
    line-height: 1.3;
  }}
  .metric-strip .cell .k {{
    font-size: var(--fs-12);
    color: var(--text-3);
    line-height: 1.3;
  }}

  /* ---- 分组标题 ---- */
  .section-title {{
    font-size: var(--fs-13);
    color: var(--text-1);
    font-weight: 600;
    margin: 8px 0 4px 0;
    padding-left: 8px;
    border-left: 3px solid var(--primary);
    line-height: 1.4;
  }}
  .section-title:first-child {{ margin-top: 2px; }}

  /* ---- 表格 ---- */
  .tbl {{
    width: 100%;
    border-collapse: collapse;
    font-size: var(--fs-12);
  }}
  .tbl th, .tbl td {{
    border: 1px solid var(--divider);
    padding: 4px 6px;
    text-align: center;
  }}
  .tbl th {{
    background: var(--bg-hover);
    color: var(--text-2);
    font-weight: 600;
  }}
  .tbl td.k {{
    text-align: left;
    color: var(--text-2);
  }}

  /* ---- 左导航 ---- */
  .st-key-nav {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 6px 4px;
    display: flex;
    flex-direction: column;
    height: calc(100vh - var(--topbar-h) - 16px);
  }}
  .nav-spacer {{ flex: 1; min-height: 12px; }}

  /* 左导航按钮：覆盖 Streamlit button */
  .st-key-nav [data-testid="stButton"] button {{
    width: 100%;
    text-align: center;
    font-size: var(--fs-13);
    padding: 6px 2px;
    border-radius: 4px;
    border: 1px solid transparent;
    background: transparent;
    color: var(--text-2);
    margin: 0;
    font-weight: 500;
    height: 32px;
    min-height: 32px;
  }}
  .st-key-nav [data-testid="stButton"] button:hover {{
    background: var(--bg-hover);
    color: var(--primary);
    border-color: var(--divider);
  }}
  /* 激活态：当前页对应 navitem_xxx_on 容器内的按钮 */
  [class*="st-key-navitem_"][class*="_on"] [data-testid="stButton"] button {{
    background: rgba(22, 119, 255, 0.08) !important;
    color: var(--primary) !important;
    border-color: rgba(22, 119, 255, 0.2) !important;
  }}
  .st-key-nav [data-testid="stElementContainer"] {{ margin-bottom: 4px !important; }}
  .st-key-nav_defaults_wrap {{
    border-top: 1px solid var(--divider);
    padding-top: 6px;
    margin-top: 6px;
  }}
  .st-key-nav_defaults_wrap [data-testid="stButton"] button {{
    color: var(--text-3);
    font-size: var(--fs-12);
  }}

  /* 顶栏右上按钮 */
  .topbar-btns [data-testid="stButton"] button {{
    font-size: var(--fs-12);
    padding: 2px 8px;
    height: 26px;
    min-height: 26px;
    background: var(--bg-card);
    color: var(--text-2);
    border: 1px solid var(--border);
    border-radius: 4px;
    width: 100%;
  }}
  .topbar-btns [data-testid="stButton"] button:hover {{
    color: var(--primary);
    border-color: var(--primary);
  }}

  /* ---- 通用控件 ---- */
  [data-testid="stSelectbox"] label,
  [data-testid="stTextInput"] label,
  [data-testid="stNumberInput"] label,
  [data-testid="stCheckbox"] label,
  [data-testid="stRadio"] label {{
    font-size: var(--fs-12) !important;
    color: var(--text-2) !important;
    font-weight: 400 !important;
    margin: 0 0 2px 0 !important;
    padding: 0 !important;
    line-height: 1.2 !important;
    min-height: 16px !important;
    height: 16px !important;
  }}
  [data-testid="stSelectbox"] > div > div {{
    font-size: var(--fs-13) !important;
    min-height: 30px !important;
  }}
  [data-testid="stTextInput"] input,
  [data-testid="stNumberInput"] input {{
    font-size: var(--fs-13) !important;
    min-height: 30px !important;
    height: 30px !important;
    padding: 4px 8px !important;
  }}
  [data-testid="stSelectbox"],
  [data-testid="stTextInput"],
  [data-testid="stNumberInput"] {{
    margin-bottom: 2px;
  }}

  /* select + view 同行对齐：view 列里的按钮顶端对齐到 select 输入框（label 16px + gap 2px = 18px） */
  [data-testid="stHorizontalBlock"] [data-testid="stColumn"]:has([data-testid="stButton"] button[kind="secondary"]) {{
    /* placeholder */
  }}

  /* Primary button */
  .stButton button[kind="primary"] {{
    background: var(--primary);
    border-color: var(--primary);
    font-size: var(--fs-13);
    padding: 4px 14px;
    height: 30px;
    border-radius: 4px;
    font-weight: 500;
  }}
  .stButton button[kind="primary"]:hover {{
    background: var(--primary-hover);
    border-color: var(--primary-hover);
  }}
  .stButton button {{
    font-size: var(--fs-12);
    padding: 3px 10px;
    border-radius: 4px;
  }}

  /* "查看" 链式按钮（同行配 selectbox 时，外层加 margin-top 对齐输入框） */
  .view-link {{
    margin-top: 18px;
  }}
  .view-link [data-testid="stButton"] button {{
    background: transparent;
    border: none;
    color: var(--primary);
    font-size: var(--fs-12);
    padding: 0 4px;
    height: 30px;
    min-height: 30px;
    text-decoration: none;
    font-weight: 400;
    width: 100%;
  }}
  .view-link [data-testid="stButton"] button:hover {{
    color: var(--primary-hover);
    text-decoration: underline;
    background: transparent;
  }}

  /* checkbox 紧凑 */
  [data-testid="stCheckbox"] {{
    margin: 0 !important;
  }}
  [data-testid="stCheckbox"] > label {{
    font-size: var(--fs-12) !important;
    color: var(--text-1) !important;
  }}

  /* expander 紧凑 */
  [data-testid="stExpander"] summary {{
    font-size: var(--fs-13);
    padding: 4px 8px;
  }}

  /* plotly 紧凑 */
  .js-plotly-plot, .plotly {{
    font-size: var(--fs-12) !important;
  }}

  /* dataframe / table */
  [data-testid="stTable"] table {{
    font-size: var(--fs-12);
  }}
  [data-testid="stTable"] th,
  [data-testid="stTable"] td {{
    padding: 4px 8px !important;
  }}

  /* 自定义参数 + 按钮 */
  .plus-btn [data-testid="stButton"] button {{
    width: 100%;
    border: 1px dashed var(--border);
    background: transparent;
    color: var(--text-2);
    font-size: var(--fs-12);
    padding: 6px;
  }}
  .plus-btn [data-testid="stButton"] button:hover {{
    color: var(--primary);
    border-color: var(--primary);
  }}

  /* st.container 默认显示边框/背景的处理：移除 main 区 container 边框 */
  [data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] {{
    gap: 0 !important;
  }}
</style>
"""


def inject_global_css() -> None:
    """注入全局 CSS。应在 app 入口最早调用一次。"""
    st.markdown(_CSS, unsafe_allow_html=True)
