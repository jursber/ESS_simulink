"""荷源网储售综合模拟仿真系统 — Streamlit 入口。

启动方式: streamlit run app.py
"""
import streamlit as st

from src.ui.pages.params_page import show as params_show
from src.ui.pages.scenarios_page import show as scenarios_show
from src.ui.pages.analysis_page import show as analysis_show
from src.ui.pages.compare_page import show as compare_show
from src.ui.state import AppState
from src.ui.components.style import inject_global_css

st.set_page_config(
    page_title="荷源网储售综合模拟仿真系统",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        "Get help": None,
        "Report a Bug": None,
        "About": None,
    },
)

inject_global_css()

NAV_OPTIONS = ["单方案分析", "多方案对比", "方案管理器", "全局参数库"]

if "main_nav" not in st.session_state:
    st.session_state.main_nav = NAV_OPTIONS[0]

AppState.init()

from src.ui.pages import analysis_page as analysis_page_module

if st.session_state.pop("header_save_requested", False):
    if st.session_state.get("main_nav") == NAV_OPTIONS[0]:
        analysis_page_module.try_header_save()
    else:
        st.warning("请先切换到「单方案分析」再保存。")

with st.container(key="topbar"):
    tb_l, tb_c, tb_r = st.columns([2.5, 5.0, 2.5], gap="small")
    with tb_l:
        st.markdown("&nbsp;", unsafe_allow_html=True)
    with tb_c:
        st.markdown('<div class="topbar-title">荷源网储售综合模拟仿真系统</div>', unsafe_allow_html=True)
    with tb_r:
        bc1, bc2, bc3 = st.columns(3, gap="small")
        with bc1:
            if st.button("加载", use_container_width=True, key="hdr_load", help="刷新页面"):
                st.rerun()
        with bc2:
            if st.button("保存", use_container_width=True, key="hdr_save", help="保存当前方案"):
                st.session_state["header_save_requested"] = True
                st.rerun()
        with bc3:
            if st.button("重置", use_container_width=True, key="hdr_reset", help="清空计算缓存与单页会话覆盖"):
                AppState.invalidate()
                for k in list(st.session_state.keys()):
                    if k.startswith("analysis_") or k.startswith("ov_") or k.startswith("wui_"):
                        del st.session_state[k]
                st.session_state.pop("header_save_requested", None)
                st.rerun()

with st.container(key="body"):
    nav_col, main_col = st.columns([0.045, 0.955], gap="small")

    with nav_col:
        with st.container(key="nav"):
            for opt in NAV_OPTIONS:
                is_active = st.session_state.main_nav == opt
                ckey = f"navitem_{opt}_{'on' if is_active else 'off'}"
                with st.container(key=ckey):
                    if st.button(opt, key=f"nav_{opt}", use_container_width=True):
                        st.session_state.main_nav = opt
                        st.rerun()
            st.markdown('<div class="nav-spacer"></div>', unsafe_allow_html=True)
            with st.container(key="nav_defaults_wrap"):
                if st.button("☐ 默认参数", key="nav_defaults", use_container_width=True,
                              help="还原全局默认参数"):
                    AppState.invalidate()
                    for k in list(st.session_state.keys()):
                        if k.startswith("analy_") or k.startswith("wui_") or k.startswith("ov_"):
                            del st.session_state[k]
                    st.rerun()

    with main_col:
        nav = st.session_state.main_nav
        if nav == "单方案分析":
            analysis_show()
        elif nav == "多方案对比":
            compare_show()
        elif nav == "方案管理器":
            scenarios_show()
        else:
            params_show()
