# -*- coding: utf-8 -*-
"""精准定位五省+全国售电购电结算核心政策并抽取公式段落"""
import re
from pathlib import Path

root = Path(r"D:\Documents\policy_data\policy_data")
TARGET = {
    "全国": ["电力市场运营基本规则", "现货市场结算", "现货市场结算实施细则", "中长期交易规则", "售电公司"],
    "广东": ["广东电力市场", "现货", "结算", "售电", "中长期"],
    "广西": ["广西电力", "现货", "结算", "售电", "中长期"],
    "山东": ["山东电力", "现货", "结算", "售电", "中长期"],
    "山西": ["山西电力", "现货", "结算", "售电", "中长期"],
}

FORMULA_KW = [
    "电费", "结算", "合约", "日前", "实时", "偏差", "购电", "售电公司",
    "统一结算", "中长期", "现货", "电量×", "×", "计算公式", "公式",
    "市场电量", "申报电量", "净合约",
]

def region_match(path: Path, reg: str) -> bool:
    s = path.stem
    if reg == "全国":
        return "_全国_" in s or s.endswith("_全国") or "国家发展改革委" in s and "省" not in s[:20]
    return f"_{reg}_" in s or s.endswith(f"_{reg}")

def score_file(path: Path, reg: str) -> int:
    name = path.stem
    sc = 0
    for kw in TARGET[reg]:
        if kw in name:
            sc += 10
    if "实施细则" in name or "结算" in name:
        sc += 5
    if "现货" in name:
        sc += 8
    if "售电" in name:
        sc += 6
    if "V" in name or "版" in name:
        sc += 2
    # 年份优先 2026
    if "2026" in name:
        sc += 15
    elif "2025" in name:
        sc += 8
    dates = re.findall(r"(\d{4}-\d{2}-\d{2})", name)
    if dates:
        sc += int(dates[-1].replace("-", "")) // 10000
    return sc

def pick_best(reg: str, limit=15) -> list[Path]:
    cands = []
    for p in root.rglob("*.txt"):
        if not region_match(p, reg):
            continue
        yr = re.search(r"20(2[5-9]|3\d)", p.stem)
        date = re.findall(r"(\d{4}-\d{2}-\d{2})", p.stem)
        if date and int(date[-1][:4]) < 2025:
            continue
        if not any(k in p.stem for k in ["现货", "结算", "交易规则", "运营规则", "售电", "中长期"]):
            continue
        cands.append((score_file(p, reg), p))
    cands.sort(key=lambda x: -x[0])
    seen_titles = set()
    out = []
    for sc, p in cands:
        key = re.sub(r"_\d{4}-\d{2}-\d{2}.*", "", p.stem)[:40]
        if key in seen_titles:
            continue
        seen_titles.add(key)
        out.append(p)
        if len(out) >= limit:
            break
    return out

def extract_snippets(path: Path, max_snippets=30) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []
    lines = text.splitlines()
    snippets = []
    for i, line in enumerate(lines):
        if any(k in line for k in FORMULA_KW):
            if len(line.strip()) < 8:
                continue
            # 取上下文
            ctx_start = max(0, i - 1)
            ctx_end = min(len(lines), i + 3)
            block = "\n".join(lines[ctx_start:ctx_end]).strip()
            if len(block) > 20:
                snippets.append(block)
    # 去重
    uniq = []
    for s in snippets:
        if s not in uniq:
            uniq.append(s)
    return uniq[:max_snippets]

def main():
    out_path = Path(r"d:\Cursor\ESS_simulink\docs\policy_extract_raw.md")
    lines = ["# 政策原文公式摘录（自动抽取）\n"]
    for reg in TARGET:
        lines.append(f"\n## {reg}\n")
        files = pick_best(reg)
        lines.append(f"共选取 {len(files)} 份核心文件\n")
        for p in files:
            lines.append(f"\n### {p.name}\n")
            lines.append(f"路径: `{p}`\n")
            snips = extract_snippets(p)
            if not snips:
                lines.append("（未抽取到公式相关段落，可能需全文阅读）\n")
            else:
                for j, s in enumerate(snips[:15], 1):
                    lines.append(f"\n**摘录{j}:**\n```\n{s[:800]}\n```\n")
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out_path}")

if __name__ == "__main__":
    main()
