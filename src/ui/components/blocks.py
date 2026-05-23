"""UI 渲染小工具：卡片、键值行、分组标题、指标条、表格等。

仅产 HTML / Streamlit 组件，无业务依赖；通过 `unsafe_allow_html` 与 `style.py` 配合呈现。
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterable, Optional

import streamlit as st


# ---- 顶栏 ---------------------------------------------------------------

def topbar(title: str) -> None:
    """渲染顶栏的标题区（按钮在 app.py 中以 columns 渲染并叠加在右侧）。"""
    st.markdown(
        f'<div class="app-topbar"><div class="title">{title}</div></div>',
        unsafe_allow_html=True,
    )


# ---- 卡片 ---------------------------------------------------------------

@contextmanager
def card(title: Optional[str] = None, sub: Optional[str] = None, right: Optional[str] = None):
    """卡片容器：用 with card("xxx", sub="...") as _: 包裹一段内容。

    Args:
        title: 卡片标题；None 时不渲染标题条。
        sub: 标题旁紧跟的灰色小字（说明性副标题）。
        right: 标题右端的小字。
    """
    st.markdown('<div class="card">', unsafe_allow_html=True)
    if title is not None:
        sub_html = f'<span class="sub">　{sub}</span>' if sub else ""
        right_html = f'<span class="right">{right}</span>' if right else ""
        st.markdown(
            f'<div class="card-title"><span>{title}{sub_html}</span>{right_html}</div>',
            unsafe_allow_html=True,
        )
    try:
        yield
    finally:
        st.markdown("</div>", unsafe_allow_html=True)


# ---- 分组标题 -----------------------------------------------------------

def section_title(text: str, right: Optional[str] = None) -> None:
    right_html = f'<span style="float:right;font-size:12px;color:#8C8C8C;font-weight:400;">{right}</span>' if right else ""
    st.markdown(
        f'<div class="section-title">{text}{right_html}</div>',
        unsafe_allow_html=True,
    )


# ---- 键值行 -------------------------------------------------------------

def kv_row(label: str, value: str, unit: Optional[str] = None) -> None:
    unit_html = f'<span class="u">{unit}</span>' if unit else ""
    st.markdown(
        f'<div class="kv-row"><span class="k">{label}</span>'
        f'<span class="v">{value}{unit_html}</span></div>',
        unsafe_allow_html=True,
    )


def kv_block(pairs: Iterable[tuple[str, str]]) -> None:
    """一次性渲染多对键值（同一卡片内的小区域）。"""
    lines = "".join(
        f'<div class="kv-row"><span class="k">{k}</span><span class="v">{v}</span></div>'
        for k, v in pairs
    )
    st.markdown(lines, unsafe_allow_html=True)


def pl_row(label: str, value: str) -> None:
    """带左侧圆点的收益行。"""
    st.markdown(
        f'<div class="pl-row"><span class="k">{label}</span>'
        f'<span class="v">{value}</span></div>',
        unsafe_allow_html=True,
    )


# ---- 指标条 -------------------------------------------------------------

def metric_strip(items: Iterable[tuple[str, str]]) -> None:
    """渲染 N 个 (label, value) 的横向指标条。"""
    cells = "".join(
        f'<div class="cell"><div class="v">{v}</div><div class="k">{k}</div></div>'
        for k, v in items
    )
    st.markdown(f'<div class="metric-strip">{cells}</div>', unsafe_allow_html=True)


def fin_strip(items: Iterable[tuple[str, str]]) -> None:
    """渲染财务指标条（每项 label 在上，value 主色高亮在下）。"""
    cells = "".join(
        f'<div class="cell"><div class="k">{k}</div><div class="v">{v}</div></div>'
        for k, v in items
    )
    st.markdown(f'<div class="fin-strip">{cells}</div>', unsafe_allow_html=True)


# ---- 简易表格 -----------------------------------------------------------

def simple_table(headers: list[str], rows: list[list[str]]) -> None:
    """渲染一个紧凑的 HTML 表格（首列为 .k 样式）。"""
    head = "".join(f"<th>{h}</th>" for h in headers)
    body_rows = []
    for r in rows:
        cells = [f'<td class="k">{r[0]}</td>'] + [f"<td>{c}</td>" for c in r[1:]]
        body_rows.append("<tr>" + "".join(cells) + "</tr>")
    body = "".join(body_rows)
    st.markdown(
        f'<table class="tbl"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>',
        unsafe_allow_html=True,
    )


# ---- "查看" 链式按钮 ----------------------------------------------------

def view_button(key: str, label: str = "查看") -> bool:
    """渲染一个链式风格按钮，返回是否被点击。"""
    st.markdown('<div class="view-link">', unsafe_allow_html=True)
    clicked = st.button(label, key=key)
    st.markdown("</div>", unsafe_allow_html=True)
    return clicked


# ---- 加号按钮 ------------------------------------------------------------

def plus_button(key: str, label: str = "自定义参数  ＋") -> bool:
    st.markdown('<div class="plus-btn">', unsafe_allow_html=True)
    clicked = st.button(label, key=key, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)
    return clicked
