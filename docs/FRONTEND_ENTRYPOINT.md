# 当前前端入口

> 最后更新：2026-06-07

本项目当前唯一可运行前端是 `frontend/` 下的纯 HTML/CSS/JS SPA，由 FastAPI 静态托管。

## 启动方式

```bash
python run.py
```

浏览器访问：

```text
http://127.0.0.1:8000/
```

API 文档访问：

```text
http://127.0.0.1:8000/docs
```

## 当前有效文件

- `run.py`：FastAPI 启动脚本。
- `api/main.py`：FastAPI 应用入口，挂载静态前端。
- `api/routes.py`：业务 API。
- `frontend/index.html`：SPA HTML 骨架。
- `frontend/css/`：前端样式。
- `frontend/js/`：前端交互与图表模块。

## 已废弃并删除的旧入口

以下旧 Streamlit demo 已删除，不再作为开发、调试或验收入口：

- `app.py`
- `src/ui/`
- `scripts/run_streamlit.ps1`
- `scripts/run_streamlit.bat`
- `.streamlit/`

如果历史 PRD、Design 或日志中仍出现 Streamlit、Plotly、`app.py`、`src/ui/`、`8501` 等内容，应按历史记录理解，不代表当前运行架构。
