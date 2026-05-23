"""储能运营模拟计算器 — Streamlit 入口。

启动方式: streamlit run app.py
"""
import streamlit as st

from src.ui.pages.params_page import show as params_show
from src.ui.pages.scenarios_page import show as scenarios_show
from src.ui.pages.analysis_page import show as analysis_show
from src.ui.pages.compare_page import show as compare_show

st.set_page_config(
    page_title="储能运营模拟计算器",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        "Get help": None,
        "Report a Bug": None,
        "About": None,
    },
)

st.markdown("""
<style>
    .stApp { max-width: 1400px; margin: 0 auto; }
    h1 { font-size: 1.8rem !important; }
    h2 { font-size: 1.3rem !important; }
    h3 { font-size: 1.1rem !important; }
    /* 导航栏样式 */
    div[data-testid="stTabs"] button {
        font-size: 1.05rem;
        padding: 0.6rem 1.2rem;
    }
    /* 隐藏 Streamlit 默认 UI 元素 */
    [data-testid="stToolbar"] { visibility: hidden; }
    [data-testid="stDecoration"] { display: none; }
    [data-testid="stStatusWidget"] { display: none; }
    footer { visibility: hidden; }
    #MainMenu { visibility: hidden; }
    header[data-testid="stHeader"] { display: none; }
    /* 隐藏 deploy 按钮 */
    .stDeployButton { display: none !important; }
</style>
""", unsafe_allow_html=True)

# 顶部导航栏
st.markdown("### ⚡ 储能运营模拟计算器")

tab1, tab2, tab3, tab4 = st.tabs(["⚙ 全局参数库", "📋 方案管理", "📊 单方案分析", "📈 多方案对比"])

with tab1:
    params_show()
with tab2:
    scenarios_show()
with tab3:
    analysis_show()
with tab4:
    compare_show()
