"""多方案对比页面。"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from src.data.scenario import ScenarioManager
from src.core.calculator import calculate
from src.ui.state import AppState


def show():
    st.title("多方案对比")
    AppState.init()

    mgr = ScenarioManager()
    items = mgr.list_all()

    if len(items) < 2:
        st.info("需要至少 2 个方案才能对比，请先在方案管理中创建。")
        return

    scenario_labels = {f"{it['name']}": it['id'] for it in items}
    selected = st.multiselect("选择要对比的方案 (2-4个)", list(scenario_labels.keys()),
                               default=list(scenario_labels.keys())[:min(2, len(scenario_labels))])

    if len(selected) < 2:
        st.warning("请至少选择 2 个方案")
        return

    sids = [scenario_labels[s] for s in selected[:4]]
    configs = [mgr.load(sid) for sid in sids]
    results = []

    for config in configs:
        sid = config.id
        r = AppState.get_result(sid)
        if r is None:
            with st.spinner(f"计算 {config.name} ..."):
                r = calculate(config)
                AppState.cache_result(sid, r)
        results.append(r)

    # 投资指标对比
    st.subheader("投资指标对比")
    rows = []
    for i, cfg in enumerate(configs):
        r = results[i]
        rows.append({
            "方案": cfg.name,
            "IRR": f"{r.irr*100:.1f}%" if r.irr != float("inf") else "N/A",
            "NPV (万元)": f"{r.npv/10000:.1f}",
            "回收期 (年)": f"{r.payback_years:.1f}" if r.payback_years < 99 else "无法回收",
            "年等效循环": f"{r.equivalent_cycles * 365:.0f}",
            "日套利 (元)": f"{r.daily_arbitrage:.1f}",
            "用户节省 (元)": f"{r.user_savings:.1f}",
        })
    st.dataframe(pd.DataFrame(rows), hide_index=True)

    # SOC 曲线叠加
    st.subheader("SOC 曲线叠加")
    fig_soc = go.Figure()
    for i, cfg in enumerate(configs):
        fig_soc.add_trace(go.Scatter(
            x=list(range(24)), y=list(results[i].SOC),
            mode="lines+markers", name=cfg.name,
        ))
    fig_soc.update_layout(xaxis_title="小时", yaxis_title="SOC", yaxis_range=[0, 1])
    st.plotly_chart(fig_soc, use_container_width=True)

    # 收益对比柱状图
    st.subheader("收益分解对比")
    metrics = ["user_savings", "user_net", "ess_revenue"]
    metric_labels = ["用户节省", "用户净得", "运营商收入"]
    for j, mk in enumerate(metrics):
        if all(getattr(r, mk, 0) != 0 for r in results):
            break
    fig_bar = go.Figure()
    for mkey, mlabel in zip(["user_savings", "ess_revenue", "user_net", "daily_arbitrage"],
                             ["用户节省", "运营商收入", "用户净得", "日套利"]):
        vals = [getattr(r, mkey, 0) for r in results]
        if any(v != 0 for v in vals):
            fig_bar.add_trace(go.Bar(name=mlabel, x=[c.name for c in configs], y=vals))
    fig_bar.update_layout(barmode="group")
    st.plotly_chart(fig_bar, use_container_width=True)

    # 差异分析
    st.subheader("差异分析")
    if len(results) >= 2:
        best = max(range(len(results)), key=lambda i: results[i].irr if results[i].irr != float("inf") else -999)
        worst = min(range(len(results)), key=lambda i: results[i].irr if results[i].irr != float("inf") else 999)
        r_best = results[best]
        r_worst = results[worst]
        st.markdown(f"""
        - **{configs[best].name}** IRR 最高 ({r_best.irr*100:.1f}%)：日套利 {r_best.daily_arbitrage:.0f} 元，等效 {r_best.equivalent_cycles:.2f} 次循环/天
        - **{configs[worst].name}** IRR 最低 ({r_worst.irr*100:.1f}%)：用户节省 {r_worst.user_savings:.0f} 元，等效 {r_worst.equivalent_cycles:.2f} 次循环/天
        - 主要差异来源：优化目标不同导致的调度策略差异（充放电时序和小时数）
        """)
