"""全局参数库页面。"""
import streamlit as st
import pandas as pd

from src.data.config import ConfigLoader
from src.ui.state import AppState


def show():
    st.title("全局参数库")
    AppState.init()

    # 加载当前参数
    ess = ConfigLoader.load_ess_defaults("henan")
    fin = ConfigLoader.load_financial_defaults("henan")

    with st.expander("储能系统参数", expanded=True):
        c1, c2, c3 = st.columns(3)
        cap_rated = c1.number_input("额定容量 (kWh)", value=float(ess.cap_rated), min_value=100.0, step=100.0)
        c_rate = c2.number_input("充放电倍率", value=float(ess.c_rate), min_value=0.1, step=0.1)
        eta = c3.number_input("往返效率", value=float(ess.eta_roundtrip), min_value=0.7, max_value=0.95, step=0.01)

        c1, c2, c3 = st.columns(3)
        soc_min = c1.number_input("SOC 下限", value=float(ess.soc_min), min_value=0.0, max_value=0.5, step=0.05)
        soc_max = c2.number_input("SOC 上限", value=float(ess.soc_max), min_value=0.5, max_value=1.0, step=0.05)
        unit_cost = c3.number_input("建设单价 (元/Wh)", value=float(ess.unit_cost), min_value=0.1, step=0.1)

        c1, c2, c3 = st.columns(3)
        r_om = c1.number_input("年运维比例", value=float(ess.r_om), min_value=0.0, max_value=0.05, step=0.001, format="%.3f")
        design_life = c2.number_input("设计寿命 (年)", value=int(ess.design_life), min_value=1, max_value=30, step=1)
        r_degrade = c3.number_input("年衰减率", value=float(ess.r_degrade), min_value=0.0, max_value=0.1, step=0.005)

    with st.expander("财务参数", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        r_discount = c1.number_input("折现率", value=float(fin.get("r_discount", 0.06)),
                                      min_value=0.01, max_value=0.2, step=0.01)
        r_user_b1 = c2.number_input("用户分成 B1", value=float(fin.get("r_user_b1", 0.30)),
                                     min_value=0.1, max_value=0.9, step=0.05)
        r_user_b2 = c3.number_input("用户分成 B2", value=float(fin.get("r_user_b2", 0.50)),
                                     min_value=0.1, max_value=0.9, step=0.05)
        r_user_b3 = c4.number_input("用户分成 B3", value=float(fin.get("r_user_b3", 0.40)),
                                     min_value=0.1, max_value=0.9, step=0.05)

    with st.expander("电价表", expanded=False):
        tab1, tab2, tab3, tab4 = st.tabs(["M1 行政分时", "M2 江苏模式", "M3 合同分时", "M5 一口价"])
        with tab1:
            try:
                df = ConfigLoader.load_tariff("henan", "admin")
                st.dataframe(df, hide_index=True)
            except Exception:
                st.info("暂无数据")
        with tab2:
            try:
                cfg = ConfigLoader.load_tariff("henan", "jiangsu")
                st.json(cfg)
            except Exception:
                st.info("暂无数据")
        with tab3:
            try:
                df = ConfigLoader.load_tariff("henan", "contract")
                st.dataframe(df, hide_index=True)
            except Exception:
                st.info("暂无数据")
        with tab4:
            flat = st.number_input("一口价 (元/kWh)", value=0.55, step=0.01)

    with st.expander("合约持仓", expanded=False):
        try:
            ct = ConfigLoader.load_contract_position("henan")
            st.dataframe(ct, hide_index=True)
            da = ConfigLoader.load_dayahead_position("henan")
            st.dataframe(da, hide_index=True)
        except Exception:
            st.info("暂无数据")

    if st.button("保存设置", type="primary"):
        from src.models.dispatch import ESSParams
        new_ess = ESSParams(
            cap_rated=cap_rated, c_rate=c_rate, eta_roundtrip=eta,
            soc_min=soc_min, soc_max=soc_max, unit_cost=unit_cost,
            r_om=r_om, design_life=int(design_life), r_degrade=r_degrade,
        )
        ConfigLoader.save_ess_defaults(new_ess)
        ConfigLoader.save_financial_defaults({
            "r_discount": r_discount,
            "r_user_b1": r_user_b1, "r_user_b2": r_user_b2, "r_user_b3": r_user_b3,
        })
        AppState.invalidate()
        st.success("参数已保存")
