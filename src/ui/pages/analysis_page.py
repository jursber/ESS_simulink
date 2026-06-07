"""单方案分析页面 — PRD/ui_spec_v1.md 2×2 栅格 + 右栏参数区。

布局（中部 Center）：
  Row1：方案概览 | 多方收益分析
  Row2：储能本体建设收益分析 | 典型日调度曲线
  Right：参数调节区（批发 / 零售 / 储能合作 / 自定义参数）

保留接口：try_header_save、_init_analysis_session、_build_work_config、
        _build_wholesale_from_session、_build_save_dict 与各 session key 命名规则。
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.core.calculator import calculate, effective_wholesale_for_scenario
from src.core.dispatch import compute_effective_price
from src.core.pricing import compute_user_price
from src.data.config import ConfigLoader
from src.data.loader import DataLoader
from src.data.scenario import ScenarioConfig, ScenarioManager
from src.models.dispatch import BusinessModel, PricingMode
from src.models.wholesale import UI_OPTION_LISTS, WholesaleSettlementConfig
from src.ui.components.blocks import (
    card,
    fin_strip,
    kv_row,
    metric_strip,
    panel_title,
    pl_row,
    plus_button,
    section_title,
    simple_table,
    view_button,
)
from src.ui.components.dispatch_chart import render_dispatch_chart
from src.ui.components.topology import render_topology
from src.ui.state import AppState

ROOT = Path(__file__).resolve().parents[3]

PM_OPTIONS = ["M1", "M2", "M3", "M4", "M5"]
PM_LABELS = {
    "M1": "行政分时",
    "M2": "江苏模式",
    "M3": "合同分时",
    "M4": "现货联动",
    "M5": "一口价",
}
BM_OPTIONS = ["B1", "B2a", "B2b", "B2c", "B3a", "B3b", "B4"]
BM_LABELS = {
    "B1": "用户+储能",
    "B2a": "售电公司最优",
    "B2b": "储能运营商最优",
    "B2c": "用户最优",
    "B3a": "储售一体最优",
    "B3b": "用户最优(储售一体)",
    "B4": "总社会福利最高",
}

USER_PROFILES = ["XX大工业", "一般工商业", "居民"]
COOP_MODES = ["收益分成", "容量租赁", "固定补贴"]


def try_header_save() -> None:
    """由 app 顶栏「保存」触发：将 `analysis_save_snapshot` 写入方案 JSON。"""
    snap = st.session_state.get("analysis_save_snapshot")
    if not snap or not snap.get("config_dict"):
        st.warning("请先在单方案分析中加载方案并完成一次展示后再保存。")
        return
    mgr = ScenarioManager()
    cfg = ScenarioConfig.from_dict(snap["config_dict"])
    mgr.save(cfg)
    st.session_state.pop("analysis_last_initialized_sid", None)
    st.success(f"已保存：{cfg.name}")


def _day_production_load_mwh(region: str, date: str) -> float:
    load_dir = ROOT / "data" / "load"
    ym = date[:4] + date[5:7]
    path = load_dir / f"{ym}.csv"
    if not path.exists():
        files = sorted(load_dir.glob("*.csv"))
        if not files:
            return 0.0
        path = files[0]
    df = pd.read_csv(path, dtype={"date": str}, comment='#')
    day = df[df["date"] == str(date)]
    if day.empty:
        return 0.0
    return float(day["Load_real"].sum()) / 1000.0


def _init_analysis_session(config: ScenarioConfig, sid: str) -> None:
    eff = effective_wholesale_for_scenario(config)
    for k, v in eff.to_flat_dict().items():
        st.session_state[f"wui_{sid}_{k}"] = v
    st.session_state[f"analy_{sid}_pricing_mode"] = config.pricing_mode
    st.session_state[f"analy_{sid}_business_model"] = config.business_model
    st.session_state[f"analy_{sid}_region"] = config.region
    st.session_state[f"analy_{sid}_selected_date"] = config.selected_date
    st.session_state[f"analy_{sid}_user_profile"] = USER_PROFILES[0]
    st.session_state[f"analy_{sid}_coop_mode"] = COOP_MODES[0]
    st.session_state[f"analy_{sid}_share_ratio"] = 20.0
    st.session_state["analysis_last_initialized_sid"] = sid


def _build_work_config(config: ScenarioConfig, sid: str) -> ScenarioConfig:
    d = config.to_dict()
    d["pricing_mode"] = st.session_state[f"analy_{sid}_pricing_mode"]
    d["business_model"] = st.session_state[f"analy_{sid}_business_model"]
    d["region"] = st.session_state[f"analy_{sid}_region"]
    d["selected_date"] = st.session_state[f"analy_{sid}_selected_date"]
    return ScenarioConfig.from_dict(d)


def _build_wholesale_from_session(sid: str) -> WholesaleSettlementConfig:
    tmpl = WholesaleSettlementConfig()
    flat: dict[str, str | float] = {}
    for k in tmpl.to_flat_dict():
        flat[k] = st.session_state[f"wui_{sid}_{k}"]
    return WholesaleSettlementConfig.from_flat_dict(flat)


def _build_save_dict(config: ScenarioConfig, sid: str) -> dict:
    work = _build_work_config(config, sid)
    d = work.to_dict()
    po = deepcopy(d.get("private_overrides") or {})
    tmpl = WholesaleSettlementConfig()
    for k in tmpl.to_flat_dict():
        po[f"wholesale.{k}"] = st.session_state[f"wui_{sid}_{k}"]
    d["private_overrides"] = po
    return d


def _wh_select(label: str, field_key: str, sid: str) -> None:
    """渲染批发结算下拉 + 右侧查看按钮。"""
    opts = UI_OPTION_LISTS[field_key]
    labels = [o[1] for o in opts]
    codes = [o[0] for o in opts]
    cur = st.session_state.get(f"wui_{sid}_{field_key}", codes[0])
    if cur not in codes:
        cur = codes[0]
        st.session_state[f"wui_{sid}_{field_key}"] = cur
    c_sel, c_view = st.columns([1, 0.22], gap="small")
    with c_sel:
        st.selectbox(
            label,
            options=codes,
            index=codes.index(cur),
            format_func=lambda c: labels[codes.index(c)],
            key=f"wui_{sid}_{field_key}",
        )
    with c_view:
        if view_button(f"view_{sid}_{field_key}"):
            st.toast(f"{label}：当前选项 {labels[codes.index(cur)]}")


def _simple_select_with_view(label: str, options: list[str], key: str, sid: str) -> None:
    if key not in st.session_state:
        st.session_state[key] = options[0]
    cur = st.session_state[key]
    if cur not in options:
        st.session_state[key] = options[0]
    c_sel, c_view = st.columns([1, 0.22], gap="small")
    with c_sel:
        st.selectbox(label, options, index=options.index(st.session_state[key]), key=key)
    with c_view:
        if view_button(f"vb_{key}"):
            st.toast(f"{label}：{st.session_state[key]}")


def _mini_bar(values: list[float], labels: list[str], color: str) -> go.Figure:
    fig = go.Figure(
        go.Bar(
            x=labels,
            y=values,
            marker_color=color,
            text=[f"{v:.1f}" for v in values],
            textposition="outside",
            textfont=dict(size=10, color="#595959"),
            width=0.55,
            hovertemplate="%{x}: %{y:.2f} 万元<extra></extra>",
        )
    )
    ymax = max(values + [0.1]) * 1.25
    fig.update_layout(
        height=140,
        margin=dict(l=8, r=8, t=8, b=24),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        font=dict(size=10, color="#595959"),
        xaxis=dict(tickfont=dict(size=10), showgrid=False, automargin=True),
        yaxis=dict(
            showgrid=True, gridcolor="#F0F0F0", zeroline=False,
            tickfont=dict(size=9), range=[0, ymax], title=dict(text="万元", font=dict(size=9), standoff=0),
        ),
    )
    return fig


def show() -> None:
    AppState.init()
    mgr = ScenarioManager()
    items = mgr.list_all()

    if not items:
        st.info("暂无方案，请先在「方案管理器」中创建。")
        return

    scenario_labels = {f"{it['name']}": it["id"] for it in items}
    scenario_names = list(scenario_labels.keys())
    selected_name = st.session_state.get("analysis_scheme_pick", scenario_names[0])
    if selected_name not in scenario_names:
        selected_name = scenario_names[0]
    sid = scenario_labels[selected_name]
    config = mgr.load(sid)

    if st.session_state.get("analysis_last_initialized_sid") != sid:
        _init_analysis_session(config, sid)
        st.session_state["analysis_scheme_pick"] = selected_name

    work = _build_work_config(config, sid)
    wholesale_ui = _build_wholesale_from_session(sid)

    result = AppState.get_result(sid)
    if result is None:
        try:
            result = calculate(work, wholesale_cfg=wholesale_ui)
            AppState.cache_result(sid, result)
        except Exception as e:
            st.error(f"计算失败：{e}")
            return

    st.session_state["analysis_save_snapshot"] = {
        "id": sid,
        "config_dict": _build_save_dict(config, sid),
    }

    ess = ConfigLoader.load_ess_defaults(work.region)
    initial_invest_yuan = ess.cap_rated * ess.unit_cost * 1000
    prod_mwh = _day_production_load_mwh(work.region, work.selected_date)
    ess_mwh = ess.cap_rated / 1000.0
    share_ratio = st.session_state.get(f"analy_{sid}_share_ratio", 20.0)

    with st.container(key="analysis_page"):
        center_col, right_col = st.columns([1, 0.22], gap="small")

        with center_col:
            with st.container(key="analysis_center"):
                with st.container(key="analysis_row1"):
                    r1_overview, r1_welfare = st.columns(2, gap="small")
                    with r1_overview:
                        with card(title="方案概览", fill=True):
                            new_name = st.selectbox(
                                "方案",
                                scenario_names,
                                index=scenario_names.index(selected_name),
                                key="analysis_scheme_pick",
                                label_visibility="collapsed",
                            )
                            if new_name != selected_name:
                                st.rerun()
                            render_topology()
                            metric_strip(
                                [
                                    ("储能", f"{ess_mwh:.2f}MWh"),
                                    ("光伏", "0"),
                                    ("可调负荷", "0"),
                                    ("生产负荷", f"{prod_mwh:.2f}MWh"),
                                ]
                            )

                    with r1_welfare:
                        with card(
                            title="多方收益分析",
                            right=f"总社会福利：{result.total_welfare / 10000:,.1f} 万元",
                            fill=True,
                        ):
                            section_title("终端用户")
                            user_bill_no = result.user_bill_no_ess / 10000
                            user_bill_with = result.user_bill_with_ess / 10000
                            user_savings = result.user_savings / 10000
                            user_return = (result.user_savings - result.user_net) / 10000
                            user_total = result.user_bill_with_ess / 10000
                            u_left, u_right = st.columns([1.05, 1], gap="small")
                            with u_left:
                                pl_row("应缴电网电费", f"{user_bill_no:,.1f} 万元")
                                pl_row("实缴电网电费", f"{user_bill_with:,.1f} 万元")
                                pl_row("用户节约电费", f"{user_savings:,.1f} 万元")
                                pl_row("返还储能费用", f"{user_return:,.1f} 万元")
                                pl_row("用户总电费", f"{user_total:,.1f} 万元")
                            with u_right:
                                st.plotly_chart(
                                    _mini_bar(
                                        [user_bill_no, user_bill_with, user_savings, user_return, user_total],
                                        ["应缴", "实缴", "节约", "返还", "总计"],
                                        "#1677FF",
                                    ),
                                    use_container_width=True,
                                    config={"displayModeBar": False},
                                )

                            section_title("储售一体用户")
                            cb_bill_no = result.user_bill_no_ess / 10000
                            cb_bill_with = result.user_bill_with_ess / 10000
                            cb_savings = result.user_savings / 10000
                            cb_return = (result.user_savings - result.user_net) / 10000
                            cb_total = (result.user_bill_with_ess + (result.user_savings - result.user_net)) / 10000
                            c_left, c_right = st.columns([1.05, 1], gap="small")
                            with c_left:
                                pl_row("应缴电网电费", f"{cb_bill_no:,.1f} 万元")
                                pl_row("实缴电网电费", f"{cb_bill_with:,.1f} 万元")
                                pl_row("用户节约电费", f"{cb_savings:,.1f} 万元")
                                pl_row("返还储能费用", f"{cb_return:,.1f} 万元")
                                pl_row("用户总电费", f"{cb_total:,.1f} 万元")
                            with c_right:
                                st.plotly_chart(
                                    _mini_bar(
                                        [cb_bill_no, cb_bill_with, cb_savings, cb_return, cb_total],
                                        ["应缴", "实缴", "节约", "返还", "总计"],
                                        "#52C41A",
                                    ),
                                    use_container_width=True,
                                    config={"displayModeBar": False},
                                )

                irr_val = result.irr if result.irr != float("inf") else None
                roi_years = (
                    initial_invest_yuan / (result.daily_arbitrage * 365)
                    if result.daily_arbitrage > 0
                    else float("inf")
                )
                roi_str = f"{roi_years:.2f} 年" if roi_years != float("inf") else "N/A"
                irr_str = f"{irr_val * 100:.2f}%" if irr_val else "N/A"
                cum_cf = result.daily_arbitrage * 365 * ess.design_life / 10000

                with st.container(key="analysis_row2"):
                    r2_ess, r2_dispatch = st.columns(2, gap="small")
                    with r2_ess:
                        with card(
                            title="储能本体建设收益分析",
                            sub="固化版本，不可点编辑，不可触动态投资",
                            fill=True,
                        ):
                            section_title("基本参数")
                            bp_l, bp_r = st.columns(2, gap="small")
                            with bp_l:
                                kv_row("储能容量", f"{ess_mwh:.2f}", "MWh")
                                kv_row("总投资", f"{initial_invest_yuan / 10000:,.1f}", "万元")
                                kv_row("储能效率", f"{ess.eta_roundtrip * 100:.0f}", "%")
                                kv_row("商业模式", BM_LABELS.get(work.business_model, work.business_model))
                                kv_row("用户分成比例", f"{share_ratio:.0f}", "%")
                            with bp_r:
                                kv_row("建设单价", f"{ess.unit_cost:.2f}", "元/Wh")
                                kv_row("运维成本", f"{ess.r_om * 100:.1f}", "%建设成本/年")
                                kv_row("项目寿命", f"{ess.design_life}", "年")
                                kv_row("调度目标", BM_LABELS.get(work.business_model, work.business_model))
                                kv_row("电价模式", PM_LABELS.get(work.pricing_mode, work.pricing_mode))

                            section_title("财务数据")
                            fin_strip(
                                [
                                    ("静态投资回收期 (ROI)", roi_str),
                                    ("全投资内部收益率 (IRR)", irr_str),
                                    (f"{ess.design_life} 年累计现金流", f"{cum_cf:,.1f} 万元"),
                                ]
                            )

                            section_title("经营数据")
                            total_charge = sum(min(0, v) for v in result.load_ESS) * -1
                            total_discharge = sum(max(0, v) for v in result.load_ESS)
                            simple_table(
                                ["指标", "典型日", "全年"],
                                [
                                    ["套利收入", f"{result.daily_arbitrage:,.0f} 元", f"{result.daily_arbitrage * 365 / 10000:,.1f} 万元"],
                                    ["总充电量", f"{total_charge:,.0f} kWh", f"{total_charge * 365 / 1000:,.0f} MWh"],
                                    ["总放电量", f"{total_discharge:,.0f} kWh", f"{total_discharge * 365 / 1000:,.0f} MWh"],
                                    ["等效循环次数", f"{result.equivalent_cycles:.2f} 次", f"{result.equivalent_cycles * 365:,.0f} 次"],
                                ],
                            )

                    with r2_dispatch:
                        with card(title="典型日调度曲线", sub="负荷 / 储能 / SOC / P_eff", fill=True):
                            P_da, P_rt = DataLoader.load_spot_prices(work.region, work.selected_date)
                            tariffs = {
                                "admin": ConfigLoader.load_tariff(work.region, "admin"),
                                "jiangsu": ConfigLoader.load_tariff(work.region, "jiangsu"),
                                "contract": ConfigLoader.load_tariff(work.region, "contract"),
                                "flat_price": 0.55,
                            }
                            P_user = compute_user_price(
                                PricingMode(work.pricing_mode),
                                tariffs,
                                DataLoader.get_monthly_pda(work.region),
                            )
                            fin_defaults = ConfigLoader.load_financial_defaults(work.region)
                            r_user_map = {
                                "B1": float(fin_defaults["r_user_b1"]),
                                "B2": float(fin_defaults["r_user_b2"]),
                                "B3": float(fin_defaults.get("r_user_b2", 0.5)),
                            }
                            bm_code = work.business_model
                            bm_prefix = (
                                "B1"
                                if bm_code == "B1"
                                else ("B2" if bm_code.startswith("B2") else ("B3" if bm_code.startswith("B3") else "B2"))
                            )
                            r_user = r_user_map.get(bm_prefix, 0.30)
                            P_eff = compute_effective_price(
                                BusinessModel(work.business_model), P_user, P_user, P_rt, r_user,
                            )
                            fig1 = render_dispatch_chart(result, P_eff)
                            fig1.update_layout(
                                height=320,
                                margin=dict(l=8, r=8, t=24, b=24),
                                paper_bgcolor="rgba(0,0,0,0)",
                                plot_bgcolor="rgba(0,0,0,0)",
                            )
                            st.plotly_chart(fig1, use_container_width=True, config={"displayModeBar": False})

        with right_col:
            with st.container(key="param_panel"):
                with card(fill=True):
                    t_l, t_r = st.columns([1, 0.55])
                    with t_l:
                        panel_title("参数调节区")
                    with t_r:
                        if st.button("计算", type="primary", key=f"calc_{sid}", use_container_width=True):
                            AppState.invalidate(sid)
                            st.rerun()

                    section_title("批发市场")
                    _wh_select("批发购电规则", "settlement_mode", sid)
                    _wh_select("中长期合约曲线", "contract_curve_profile", sid)
                    _wh_select("日前报量曲线", "dayahead_curve_profile", sid)

                    cur_sp = (
                        f"{st.session_state[f'analy_{sid}_region']} · "
                        f"{st.session_state[f'analy_{sid}_selected_date']}（日前&实时）"
                    )
                    c_sp, c_spv = st.columns([1, 0.22], gap="small")
                    with c_sp:
                        st.text_input("现货电价曲线", value=cur_sp, disabled=True, key=f"sp_{sid}")
                    with c_spv:
                        if view_button(f"view_sp_{sid}"):
                            st.toast(f"现货电价：{cur_sp}")

                    section_title("零售")
                    c_pm, c_pmv = st.columns([1, 0.22], gap="small")
                    with c_pm:
                        st.selectbox(
                            "零售用户电价",
                            PM_OPTIONS,
                            index=PM_OPTIONS.index(st.session_state[f"analy_{sid}_pricing_mode"])
                            if st.session_state[f"analy_{sid}_pricing_mode"] in PM_OPTIONS
                            else 0,
                            format_func=lambda c: PM_LABELS.get(c, c),
                            key=f"analy_{sid}_pricing_mode",
                        )
                    with c_pmv:
                        if view_button(f"view_pm_{sid}"):
                            cur_pm = st.session_state[f"analy_{sid}_pricing_mode"]
                            st.toast(f"电价模式：{PM_LABELS.get(cur_pm, cur_pm)}")

                    cur_pm = st.session_state[f"analy_{sid}_pricing_mode"]
                    c_pc, c_pcv = st.columns([1, 0.22], gap="small")
                    with c_pc:
                        st.text_input(
                            "电价曲线",
                            value=PM_LABELS.get(cur_pm, cur_pm),
                            disabled=True,
                            key=f"pc_{sid}",
                        )
                    with c_pcv:
                        if view_button(f"view_pc_{sid}"):
                            st.toast(f"电价曲线：{PM_LABELS.get(cur_pm, cur_pm)}")

                    _simple_select_with_view(
                        "用户产负曲线", USER_PROFILES, f"analy_{sid}_user_profile", sid
                    )

                    section_title("储能合作")
                    st.selectbox(
                        "储能合作模式", COOP_MODES,
                        index=COOP_MODES.index(st.session_state[f"analy_{sid}_coop_mode"])
                        if st.session_state[f"analy_{sid}_coop_mode"] in COOP_MODES
                        else 0,
                        key=f"analy_{sid}_coop_mode",
                    )
                    st.number_input(
                        "用户分成比例 (%)",
                        min_value=0.0, max_value=100.0, step=1.0,
                        key=f"analy_{sid}_share_ratio",
                    )

                    if plus_button(f"add_param_{sid}", "自定义参数  ＋"):
                        st.toast("自定义参数：待实现")
