"""系统拓扑示意图（占位）。

当前实现：使用纯 HTML/SVG 绘制 "电网 → 售电公司 → 用户 / 储能" 的简化能量流图，
便于一屏内紧凑展示且无 plotly 依赖。后续可替换为 Sankey/交互式图表。
"""
from __future__ import annotations

import streamlit as st


def render_topology() -> None:
    """渲染拓扑示意（占位 SVG），自适应卡片宽度，高度紧凑。"""
    svg = """
<svg viewBox="0 0 520 200" preserveAspectRatio="xMidYMid meet"
     xmlns="http://www.w3.org/2000/svg" style="width:100%;height:100%;max-height:200px;">
  <defs>
    <marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth">
      <path d="M0,0 L0,6 L9,3 z" fill="#1677FF"/>
    </marker>
  </defs>

  <!-- 电网 -->
  <rect x="20" y="80" width="80" height="40" rx="4" fill="#FFFFFF" stroke="#1677FF" stroke-width="1.5"/>
  <text x="60" y="105" text-anchor="middle" font-size="13" fill="#1F1F1F" font-weight="600">电网</text>

  <!-- 售电公司 -->
  <rect x="200" y="80" width="100" height="40" rx="4" fill="#FFFFFF" stroke="#1677FF" stroke-width="1.5"/>
  <text x="250" y="105" text-anchor="middle" font-size="13" fill="#1F1F1F" font-weight="600">售电公司</text>

  <!-- 用户 -->
  <rect x="400" y="30" width="100" height="40" rx="4" fill="#FFFFFF" stroke="#52C41A" stroke-width="1.5"/>
  <text x="450" y="55" text-anchor="middle" font-size="13" fill="#1F1F1F" font-weight="600">终端用户</text>

  <!-- 储能 -->
  <rect x="400" y="130" width="100" height="40" rx="4" fill="#FFFFFF" stroke="#FAAD14" stroke-width="1.5"/>
  <text x="450" y="155" text-anchor="middle" font-size="13" fill="#1F1F1F" font-weight="600">储能</text>

  <!-- 电网 -> 售电公司 -->
  <line x1="100" y1="100" x2="195" y2="100" stroke="#1677FF" stroke-width="1.5" marker-end="url(#arrow)"/>

  <!-- 售电公司 -> 用户 -->
  <path d="M300,95 Q350,95 350,50 L395,50" fill="none" stroke="#1677FF" stroke-width="1.5" marker-end="url(#arrow)"/>

  <!-- 售电公司 -> 储能 / 储能 -> 用户（双向） -->
  <path d="M300,105 Q350,105 350,150 L395,150" fill="none" stroke="#1677FF" stroke-width="1.5" marker-end="url(#arrow)"/>
  <path d="M400,140 Q360,140 360,75 L400,55" fill="none" stroke="#8C8C8C" stroke-width="1" stroke-dasharray="3 3"/>

  <!-- 关口表标识 -->
  <circle cx="150" cy="100" r="5" fill="#FFFFFF" stroke="#1677FF" stroke-width="1"/>
  <text x="150" y="82" text-anchor="middle" font-size="10" fill="#8C8C8C">关口</text>
</svg>
"""
    st.markdown(
        f'<div style="width:100%;display:flex;justify-content:center;align-items:center;'
        f'background:#FAFAFA;border:1px dashed #D9D9D9;border-radius:6px;padding:6px;">'
        f'{svg}</div>',
        unsafe_allow_html=True,
    )
