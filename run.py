"""一键启动：python run.py → http://localhost:8000"""
import uvicorn

from scripts.ensure_seed_data import ensure_seed_data

if __name__ == "__main__":
    ensure_seed_data()
    uvicorn.run("api.main:app", host="127.0.0.1", port=8000, reload=True)
