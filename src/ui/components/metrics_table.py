"""投资指标表组件。"""
import streamlit as st


def render_metrics_table(result, ess_params: dict):
    """显示关键投资指标。"""
    cols = st.columns(4)
    irr_val = result.irr if result.irr != float("inf") else None
    cols[0].metric("IRR", f"{irr_val*100:.1f}%" if irr_val else "N/A")
    cols[1].metric("NPV", f"{result.npv:,.0f} 元")
    cols[2].metric("回收期",
                   f"{result.payback_years:.1f} 年" if result.payback_years < 99 else "无法回收")
    cols[3].metric("年等效循环", f"{result.equivalent_cycles * 365:.0f} 次")

    st.divider()
    detail = {
        "总投资 (元)": f"{ess_params.get('cap_rated', 0) * ess_params.get('unit_cost', 0) * 1000:,.0f}",
        "日套利 (元)": f"{result.daily_arbitrage:,.1f}",
        "用户电费节省 (元)": f"{result.user_savings:,.1f}",
        "运营商注入收入 (元)": f"{result.ess_revenue:,.1f}",
        "用户净收益 (元)": f"{result.user_net:,.1f}",
        "日等效循环 (次)": f"{result.equivalent_cycles:.2f}",
        "日放电量 (kWh)": f"{sum(max(0, v) for v in result.load_ESS):,.0f}",
    }
    if result.retail_profit != 0:
        detail["售电利润 (元)"] = f"{result.retail_profit:,.1f}"
        detail["购电成本 (元)"] = f"{result.purchase_cost:,.1f}"
        detail["组合利润 (元)"] = f"{result.combined_profit:,.1f}"

    detail["社会总福利 (元)"] = f"{result.total_welfare:,.1f}"

    for k, v in detail.items():
        c1, c2 = st.columns([3, 2])
        c1.caption(k)
        c2.caption(v)
