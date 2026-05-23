"""Streamlit 会话状态管理。"""
from dataclasses import dataclass, field
from typing import Optional
import streamlit as st


@dataclass
class AppState:
    """管理 st.session_state 中的全局状态。"""

    @staticmethod
    def init():
        defaults = {
            "global_ess": None,       # dict
            "global_fin": None,       # dict
            "scenarios": {},          # {id: ScenarioConfig}
            "results_cache": {},      # {id: DispatchResult}
            "selected_scenario": None,
            "compare_selection": [],
        }
        for k, v in defaults.items():
            if k not in st.session_state:
                st.session_state[k] = v

    @staticmethod
    def cache_result(sid: str, result):
        st.session_state.results_cache[sid] = result

    @staticmethod
    def get_result(sid: str):
        return st.session_state.results_cache.get(sid)

    @staticmethod
    def invalidate(sid: str = None):
        if sid:
            st.session_state.results_cache.pop(sid, None)
        else:
            st.session_state.results_cache.clear()
