"""单方案分析页面。"""
import streamlit as st
import pandas as pd

from src.data.scenario import ScenarioManager
from src.data.loader import DataLoader
from src.data.config import ConfigLoader
from src.core.pricing import compute_user_price
from src.core.dispatch import compute_effective_price
from src.core.calculator import calculate
from src.models.dispatch import BusinessModel, PricingMode
from src.ui.state import AppState
from src.ui.components.dispatch_chart import render_dispatch_chart
from src.ui.components.waterfall import render_waterfall
from src.ui.components.metrics_table import render_metrics_table


def show():
    st.title("单方案分析")
    AppState.init()

    mgr = ScenarioManager()
    items = mgr.list_all()

    if not items:
        st.info("暂无方案，请先在方案管理中创建。")
        return

    scenario_labels = {f"{it['name']}": it['id'] for it in items}
    selected = st.selectbox("选择方案", list(scenario_labels.keys()))

    if not selected:
        return

    sid = scenario_labels[selected]
    config = mgr.load(sid)

    result = AppState.get_result(sid)
    if result is None:
        with st.spinner("计算中..."):
            result = calculate(config)
            AppState.cache_result(sid, result)

    ess = ConfigLoader.load_ess_defaults(config.region)
    ess_params = {
        "cap_rated": ess.cap_rated, "unit_cost": ess.unit_cost,
        "c_rate": ess.c_rate, "eta_roundtrip": ess.eta_roundtrip,
        "soc_min": ess.soc_min, "soc_max": ess.soc_max,
        "r_om": ess.r_om, "design_life": ess.design_life, "r_degrade": ess.r_degrade,
    }

    st.subheader("关键指标")
    render_metrics_table(result, ess_params)

    st.subheader("调度曲线")
    has_retailer = config.business_model != "B1"

    P_da, P_rt = DataLoader.load_spot_prices(config.region, config.selected_date)
    tariffs = {
        "admin": ConfigLoader.load_tariff(config.region, "admin"),
        "jiangsu": ConfigLoader.load_tariff(config.region, "jiangsu"),
        "contract": ConfigLoader.load_tariff(config.region, "contract"),
        "flat_price": 0.55,
    }
    P_user = compute_user_price(PricingMode(config.pricing_mode), tariffs,
                                 DataLoader.get_monthly_pda(config.region))
    fin_defaults = ConfigLoader.load_financial_defaults(config.region)
    r_user_map = {"B1": float(fin_defaults["r_user_b1"]),
                  "B2": float(fin_defaults["r_user_b2"]),
                  "B3": float(fin_defaults["r_user_b3"])}
    bm_code = config.business_model
    bm_prefix = "B1" if bm_code == "B1" else ("B2" if bm_code.startswith("B2") else ("B3" if bm_code.startswith("B3") else "B2"))
    r_user = r_user_map.get(bm_prefix, 0.30)

    P_eff = compute_effective_price(
        BusinessModel(config.business_model),
        P_user, P_user, P_rt, r_user,
    )

    fig1 = render_dispatch_chart(result, P_eff)
    st.plotly_chart(fig1, use_container_width=True)

    st.subheader("收益分解")
    fig2 = render_waterfall(result, has_retailer)
    st.plotly_chart(fig2, use_container_width=True)

    # 24 小时数据表
    with st.expander("24 小时数据明细"):
        rows = []
        for h in range(24):
            rows.append({
                "小时": h,
                "load_ESS": f"{result.load_ESS[h]:.0f}",
                "SOC": f"{result.SOC[h]:.3f}",
                "load_grid": f"{result.load_grid[h]:.0f}",
            })
        st.dataframe(pd.DataFrame(rows), hide_index=True)
