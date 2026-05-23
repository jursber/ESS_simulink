"""方案管理页面。"""
import streamlit as st

from src.data.scenario import ScenarioManager, ScenarioConfig
from src.data.config import ConfigLoader
from src.data.loader import DataLoader
from src.core.calculator import calculate
from src.ui.state import AppState

BM_OPTIONS = ["B1", "B2a", "B2b", "B2c", "B3a", "B3b", "B4"]
PM_OPTIONS = ["M1", "M2", "M3", "M4", "M5"]


def _run_calculation(config: ScenarioConfig):
    """执行调度计算并缓存结果。"""
    result = calculate(config)
    AppState.cache_result(config.id, result)
    return result


def show():
    st.title("方案管理")
    AppState.init()

    mgr = ScenarioManager()

    col_left, col_right = st.columns([1, 2])

    with col_left:
        st.subheader("方案列表")
        items = mgr.list_all()
        scenario_names = {f"{it['name']} ({it['id'][:6]})": it['id'] for it in items}

        selected_label = st.selectbox(
            "选择方案",
            list(scenario_names.keys()),
            key="scenario_selector",
            label_visibility="collapsed",
        ) if scenario_names else None

        if st.button("+ 新建方案"):
            cfg = ScenarioConfig(name=f"新方案-{len(items)+1}")
            mgr.save(cfg)
            st.rerun()

        if selected_label and st.button("删除方案", type="secondary"):
            sid = scenario_names[selected_label]
            mgr.delete(sid)
            AppState.invalidate(sid)
            st.rerun()

    with col_right:
        if selected_label:
            sid = scenario_names[selected_label]
            config = mgr.load(sid)

            st.subheader(f"编辑: {config.name}")

            config.name = st.text_input("名称", config.name)
            config.region = st.selectbox("地区", ["henan"], index=0)
            config.pricing_mode = st.selectbox("电价模式", PM_OPTIONS,
                                                index=PM_OPTIONS.index(config.pricing_mode) if config.pricing_mode in PM_OPTIONS else 0)
            config.business_model = st.selectbox("商业模式", BM_OPTIONS,
                                                  index=BM_OPTIONS.index(config.business_model) if config.business_model in BM_OPTIONS else 0)

            dates = DataLoader.get_available_dates(config.region)
            if config.selected_date not in dates:
                config.selected_date = dates[0] if dates else "2026-03-15"
            config.selected_date = st.selectbox("计算日期", dates,
                                                 index=dates.index(config.selected_date) if config.selected_date in dates else 0)

            st.divider()
            st.caption("私有参数覆盖 (留空则沿用全局默认)")
            override_cap = st.number_input("cap_rated", value=None, placeholder="全局默认")
            override_crate = st.number_input("c_rate", value=None, placeholder="全局默认")
            if override_cap is not None and override_crate is not None:
                config.private_overrides = {
                    "ess_params.cap_rated": override_cap,
                    "ess_params.c_rate": override_crate,
                }

            if st.button("保存方案", type="primary"):
                mgr.save(config)
                st.success("已保存")

            if st.button("计算", type="primary"):
                with st.spinner("计算中..."):
                    result = _run_calculation(config)
                st.success(f"计算完成 — IRR={result.irr*100:.1f}%")
        else:
            st.info("请选择一个方案或新建方案")
