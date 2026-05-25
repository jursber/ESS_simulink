"""全局 UI 样式 token 与 Streamlit 控件覆盖。

设计基线：PRD/ui_spec_v1.md — 工业线框风、纯白背景、蓝色主色、最小字号 12px。
"""
from __future__ import annotations

import streamlit as st

# ---- 设计 token（与 PRD/ui_spec_v1.md 一致）--------------------------------

PRIMARY = "#1677FF"
PRIMARY_HOVER = "#4096FF"
PRIMARY_ACTIVE = "#0958D9"
SUCCESS = "#52C41A"

TEXT_PRIMARY = "#1F1F1F"
TEXT_REGULAR = "#595959"
TEXT_SECONDARY = "#8C8C8C"
TEXT_DISABLED = "#BFBFBF"

BORDER = "#E5E7EB"
DIVIDER = "#F0F0F0"
BG_PAGE = "#FFFFFF"
BG_CARD = "#FFFFFF"
BG_STRIP = "#FAFBFC"

RADIUS = "4px"

TOPBAR_H = 40
LEFTNAV_W = 84
RIGHTPANEL_W = 280

_CSS = f"""
<style>
  :root {{
    --primary: {PRIMARY};
    --primary-hover: {PRIMARY_HOVER};
    --primary-active: {PRIMARY_ACTIVE};
    --success: {SUCCESS};
    --text-1: {TEXT_PRIMARY};
    --text-2: {TEXT_REGULAR};
    --text-3: {TEXT_SECONDARY};
    --text-4: {TEXT_DISABLED};
    --border: {BORDER};
    --divider: {DIVIDER};
    --bg-page: {BG_PAGE};
    --bg-card: {BG_CARD};
    --bg-strip: {BG_STRIP};
    --radius: {RADIUS};
    --fs-12: 12px;
    --fs-13: 13px;
    --fs-14: 14px;
    --fs-16: 16px;
    --topbar-h: {TOPBAR_H}px;
    --leftnav-w: {LEFTNAV_W}px;
    --rightpanel-w: {RIGHTPANEL_W}px;
    --body-h: calc(100vh - var(--topbar-h) - 8px);
    --grid-gap: 6px;
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
  [data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] {{
    gap: 0 !important;
  }}
  [data-testid="stVerticalBlock"] {{
    gap: var(--grid-gap) !important;
  }}
  [data-testid="stHorizontalBlock"] {{
    gap: var(--grid-gap) !important;
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
  h1 {{ font-size: var(--fs-16) !important; }}
  h2 {{ font-size: var(--fs-14) !important; }}
  h3, h4, h5 {{ font-size: var(--fs-13) !important; }}

  p, li, label, span, div {{ font-size: var(--fs-13); }}
  .stCaption, [data-testid="stCaptionContainer"] {{
    color: var(--text-3) !important;
    font-size: var(--fs-12) !important;
  }}

  /* ---- 顶栏 ---- */
  .st-key-topbar {{
    height: var(--topbar-h);
    background: var(--bg-card);
    border-bottom: 1px solid var(--border);
    margin: 0;
    padding: 0 12px;
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
    height: 26px;
    min-height: 26px;
    background: var(--bg-card);
    color: var(--text-2);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    width: 100%;
    box-shadow: none;
  }}
  .st-key-topbar [data-testid="stButton"] button:hover {{
    color: var(--primary);
    border-color: var(--primary);
  }}

  /* ---- 主体 ---- */
  .st-key-body {{
    padding: 0 8px 8px 8px;
    height: var(--body-h);
    overflow: hidden;
  }}
  .st-key-body > [data-testid="stHorizontalBlock"] {{
    height: 100%;
    align-items: stretch !important;
  }}
  .st-key-body > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:last-child {{
    height: 100%;
    overflow: hidden;
  }}
  .st-key-body > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:last-child
    > [data-testid="stVerticalBlock"] {{
    height: 100%;
  }}

  /* ---- 左导航 ---- */
  .st-key-nav {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 6px 4px;
    height: 100%;
    box-sizing: border-box;
  }}
  .nav-spacer {{ flex: 1; min-height: 8px; }}
  .st-key-nav [data-testid="stButton"] button {{
    width: 100%;
    text-align: center;
    font-size: var(--fs-13);
    padding: 6px 2px;
    border-radius: var(--radius);
    border: 1px solid transparent;
    background: transparent;
    color: var(--text-2);
    font-weight: 500;
    height: 32px;
    min-height: 32px;
    box-shadow: none;
  }}
  .st-key-nav [data-testid="stButton"] button:hover {{
    background: var(--bg-strip);
    color: var(--primary);
    border-color: var(--divider);
  }}
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

  /* ---- 单方案分析 2×2 栅格 ---- */
  .st-key-analysis_page {{
    height: 100%;
  }}
  .st-key-analysis_page > [data-testid="stHorizontalBlock"] {{
    height: 100%;
    align-items: stretch !important;
  }}
  .st-key-analysis_center {{
    height: 100%;
  }}
  .st-key-analysis_center > [data-testid="stVerticalBlock"] {{
    height: 100%;
    gap: var(--grid-gap) !important;
    display: flex;
    flex-direction: column;
  }}
  .st-key-analysis_row1,
  .st-key-analysis_row2 {{
    flex: 1 1 50%;
    min-height: 0;
    overflow: hidden;
  }}
  .st-key-analysis_row1 > [data-testid="stHorizontalBlock"],
  .st-key-analysis_row2 > [data-testid="stHorizontalBlock"] {{
    height: 100%;
    align-items: stretch !important;
  }}
  .st-key-analysis_row1 [data-testid="stColumn"] > [data-testid="stVerticalBlock"],
  .st-key-analysis_row2 [data-testid="stColumn"] > [data-testid="stVerticalBlock"] {{
    height: 100%;
  }}

  .st-key-param_panel {{
    height: 100%;
    overflow: hidden;
  }}
  .st-key-param_panel > [data-testid="stVerticalBlock"] {{
    height: 100%;
  }}

  /* ---- 卡片 ---- */
  .card {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    box-shadow: none;
    padding: 8px 10px;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    margin: 0;
    box-sizing: border-box;
  }}
  .card-fill {{
    height: 100%;
    min-height: 0;
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
    flex-shrink: 0;
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
  .panel-title {{
    font-size: var(--fs-14);
    font-weight: 600;
    color: var(--text-1);
    line-height: 28px;
  }}

  /* ---- 键值行（亲密性：左对齐） ---- */
  .kv-row {{
    display: flex;
    align-items: baseline;
    justify-content: flex-start;
    gap: 8px;
    padding: 2px 0;
    font-size: var(--fs-13);
    line-height: 1.5;
  }}
  .kv-row .k {{
    color: var(--text-3);
    white-space: nowrap;
    font-size: var(--fs-12);
    flex-shrink: 0;
  }}
  .kv-row .v {{
    color: var(--text-1);
    font-weight: 500;
    white-space: nowrap;
  }}
  .kv-row .u {{
    color: var(--text-3);
    font-size: var(--fs-12);
    margin-left: 2px;
    font-weight: 400;
  }}

  .fin-strip {{
    display: flex;
    gap: 0;
    background: var(--bg-strip);
    border: 1px solid var(--divider);
    border-radius: var(--radius);
    padding: 6px 0;
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

  .pl-row {{
    display: flex;
    align-items: center;
    justify-content: flex-start;
    gap: 4px;
    padding: 2px 0;
    font-size: var(--fs-13);
    line-height: 1.4;
  }}
  .pl-row .k {{
    color: var(--text-2);
    display: flex;
    align-items: center;
    gap: 6px;
    flex-shrink: 0;
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
    color: var(--primary);
    font-weight: 600;
    font-size: var(--fs-13);
  }}

  .metric-strip {{
    display: flex;
    align-items: stretch;
    background: var(--bg-strip);
    border: 1px solid var(--divider);
    border-radius: var(--radius);
    padding: 6px 0;
    margin-top: 4px;
    flex-shrink: 0;
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

  .section-title {{
    font-size: var(--fs-13);
    color: var(--text-1);
    font-weight: 600;
    height: 24px;
    line-height: 24px;
    margin: 8px 0 6px 0;
    padding-left: 8px;
    border-left: 3px solid var(--primary);
    flex-shrink: 0;
  }}
  .section-title:first-child {{ margin-top: 2px; }}

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
    background: var(--bg-strip);
    color: var(--text-2);
    font-weight: 600;
  }}
  .tbl td.k {{
    text-align: left;
    color: var(--text-2);
  }}

  /* ---- 控件 ---- */
  [data-testid="stSelectbox"] label,
  [data-testid="stTextInput"] label,
  [data-testid="stNumberInput"] label,
  [data-testid="stCheckbox"] label,
  [data-testid="stRadio"] label {{
    font-size: var(--fs-12) !important;
    color: var(--text-2) !important;
    font-weight: 400 !important;
    margin: 0 0 4px 0 !important;
    padding: 0 !important;
    line-height: 1.3 !important;
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
    border-color: var(--border) !important;
  }}
  [data-testid="stSelectbox"],
  [data-testid="stTextInput"],
  [data-testid="stNumberInput"] {{
    margin-bottom: 4px;
  }}

  .stButton button[kind="primary"] {{
    background: var(--primary);
    border-color: var(--primary);
    font-size: var(--fs-13);
    padding: 4px 14px;
    height: 28px;
    min-height: 28px;
    border-radius: var(--radius);
    font-weight: 500;
    box-shadow: none;
  }}
  .stButton button[kind="primary"]:hover {{
    background: var(--primary-hover);
    border-color: var(--primary-hover);
  }}
  .stButton button {{
    font-size: var(--fs-12);
    padding: 3px 10px;
    border-radius: var(--radius);
    box-shadow: none;
  }}

  .view-col {{
    display: flex;
    align-items: flex-end;
    padding-bottom: 2px;
    min-height: 58px;
  }}
  .view-col [data-testid="stButton"] button {{
    background: transparent;
    border: none;
    color: var(--primary);
    font-size: var(--fs-12);
    padding: 0 4px;
    height: 30px;
    min-height: 30px;
    font-weight: 400;
    width: 100%;
    box-shadow: none;
  }}
  .view-col [data-testid="stButton"] button:hover {{
    color: var(--primary-hover);
    text-decoration: underline;
    background: transparent;
  }}

  .plus-btn [data-testid="stButton"] button {{
    width: 100%;
    border: 1px dashed var(--border);
    background: transparent;
    color: var(--text-2);
    font-size: var(--fs-12);
    padding: 6px;
    box-shadow: none;
  }}
  .plus-btn [data-testid="stButton"] button:hover {{
    color: var(--primary);
    border-color: var(--primary);
  }}

  .js-plotly-plot, .plotly {{
    font-size: var(--fs-12) !important;
  }}
  [data-testid="stPlotlyChart"] {{
    margin: 0 !important;
  }}
</style>
"""


def inject_global_css() -> None:
    """注入全局 CSS。应在 app 入口最早调用一次。"""
    st.markdown(_CSS, unsafe_allow_html=True)
