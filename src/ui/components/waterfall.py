"""收益分解瀑布图组件。"""
import plotly.graph_objects as go


def render_waterfall(result, has_retailer: bool = True) -> go.Figure:
    """绘制收益分解瀑布图。"""
    labels = []
    values = []
    types = []

    # 用户侧
    labels.append("无储能电费")
    values.append(result.user_bill_no_ess)
    types.append("absolute")

    labels.append("电费节省")
    values.append(-result.user_savings)  # 负值表示减少
    types.append("relative")

    labels.append("有储能电费")
    values.append(result.user_bill_with_ess)
    types.append("total")

    labels.append("运营商收入")
    values.append(-result.ess_revenue)
    types.append("relative")

    labels.append("用户净收益")
    values.append(result.user_net)
    types.append("total")

    if has_retailer:
        labels.append("售电收入")
        values.append(result.retail_revenue)
        types.append("absolute")

        labels.append("购电成本")
        values.append(-result.purchase_cost)
        types.append("relative")

        labels.append("售电利润")
        values.append(result.retail_profit)
        types.append("total")

        labels.append("组合利润")
        values.append(result.combined_profit)
        types.append("total")

    labels.append("社会总福利")
    values.append(result.total_welfare)
    types.append("total")

    fig = go.Figure(go.Waterfall(
        name="收益分解",
        orientation="v",
        measure=[{"absolute": "absolute", "relative": "relative", "total": "total"}[t] for t in types],
        x=labels,
        y=values,
        decreasing={"marker": {"color": "#d62728"}},
        increasing={"marker": {"color": "#2ca02c"}},
        totals={"marker": {"color": "#1f77b4"}},
        text=[f"{v:,.0f}" for v in values],
        textposition="outside",
    ))
    fig.update_layout(
        yaxis_title="金额 (元)",
        showlegend=False,
        margin=dict(t=30),
    )
    return fig
