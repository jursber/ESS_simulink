"""调度曲线图组件。Plotly 双 Y 轴：电量面积图 + SOC 折线。"""
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def render_dispatch_chart(result, P_eff=None) -> go.Figure:
    """绘制 24 小时调度曲线。"""
    hours = list(range(24))
    load_ESS = list(result.load_ESS)
    load_grid = list(result.load_grid)
    SOC = list(result.SOC)

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # 堆叠面积图：load_grid 和 load_ESS
    fig.add_trace(go.Bar(
        name="关口负荷", x=hours, y=load_grid,
        marker_color="#7f7f7f", opacity=0.7,
    ), secondary_y=False)

    # 充电/放电分开
    charge = [min(0, v) for v in load_ESS]
    discharge = [max(0, v) for v in load_ESS]
    fig.add_trace(go.Bar(
        name="充电", x=hours, y=charge,
        marker_color="#1f77b4",
    ), secondary_y=False)
    fig.add_trace(go.Bar(
        name="放电", x=hours, y=discharge,
        marker_color="#ff7f0e",
    ), secondary_y=False)

    # SOC 折线
    fig.add_trace(go.Scatter(
        name="SOC", x=hours, y=SOC,
        mode="lines+markers", line=dict(color="#2ca02c", width=2),
        yaxis="y2",
    ), secondary_y=True)

    # P_eff 虚线
    if P_eff is not None:
        fig.add_trace(go.Scatter(
            name="P_eff", x=hours, y=list(P_eff),
            mode="lines", line=dict(color="#d62728", width=1.5, dash="dot"),
            yaxis="y2",
        ), secondary_y=True)

    fig.update_layout(
        barmode="relative",
        xaxis_title="小时",
        hovermode="x unified",
        legend=dict(orientation="h", y=1.12),
        margin=dict(l=8, r=8, t=24, b=24),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=10, color="#595959"),
    )
    fig.update_xaxes(showgrid=True, gridcolor="#F0F0F0")
    fig.update_yaxes(title_text="电量 (kWh)", showgrid=True, gridcolor="#F0F0F0", secondary_y=False)
    fig.update_yaxes(title_text="SOC / P_eff", range=[0, 1.0], secondary_y=True)

    return fig
