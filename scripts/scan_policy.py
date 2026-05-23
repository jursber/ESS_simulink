# -*- coding: utf-8 -*-
"""扫描政策库，筛选售电公司购电成本相关文件"""
import re
from pathlib import Path
from collections import defaultdict

root = Path(r"D:\Documents\policy_data\policy_data")
REGIONS = {"全国", "广东", "广西", "山东", "山西", "国家"}
KEYWORDS = {
    "现货": ["现货", "日前", "实时", "偏差"],
    "中长期": ["中长期", "年度", "月度", "合约", "转让"],
    "结算": ["结算", "电费", "购电", "售电"],
    "交易规则": ["交易规则", "实施细则", "基本规则", "运营规则", "结算细则"],
}
YEAR_RE = re.compile(r"(20(?:2[5-9]|3\d))")
DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")

def region_of(path: Path) -> str | None:
    s = path.stem + str(path.parent)
    for r in REGIONS:
        if r in s:
            if r == "国家":
                return "全国"
            return r
    return None

def classify(path: Path) -> set[str]:
    name = path.stem
    cats = set()
    for cat, kws in KEYWORDS.items():
        if any(k in name for k in kws):
            cats.add(cat)
    return cats

def file_year(path: Path) -> int | None:
    m = YEAR_RE.search(path.stem)
    if m:
        return int(m.group(1))
    dates = DATE_RE.findall(path.stem)
    if dates:
        return int(dates[-1][:4])
    return None

def file_date(path: Path) -> str:
    dates = DATE_RE.findall(path.stem)
    return dates[-1] if dates else "0000-00-00"

def main():
    by_key: dict[tuple, list[Path]] = defaultdict(list)
    all_hits = []

    for p in root.rglob("*.txt"):
        reg = region_of(p)
        if not reg:
            continue
        yr = file_year(p)
        if yr is None or yr < 2025:
            continue
        cats = classify(p)
        if not cats:
            continue
        if not (cats & {"现货", "中长期", "结算"} or "交易规则" in cats):
            continue
        all_hits.append((reg, p, cats, yr, file_date(p)))
        # 按区域+主题关键词去重，保留最新日期
        topic = "交易规则" if "交易规则" in cats else (
            "现货" if "现货" in cats else ("结算" if "结算" in cats else "中长期")
        )
        key = (reg, topic, _normalize_title(p.stem))
        by_key[key].append(p)

    print(f"总命中: {len(all_hits)}")
    print("\n=== 去重后核心文件（每类取最新）===\n")
    selected = []
    for key, paths in sorted(by_key.items()):
        best = max(paths, key=lambda x: (file_date(x), file_year(x) or 0))
        selected.append((key, best, file_date(best)))

    for (reg, topic, title), path, dt in sorted(selected, key=lambda x: (x[0][0], x[0][1])):
        print(f"[{reg}][{topic}] {dt} | {path.name[:80]}")

    # 输出路径列表供读取
    out = Path(r"d:\Cursor\ESS_simulink\docs\policy_scan_list.txt")
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        for (_, _, _), path, dt in sorted(selected, key=lambda x: (x[0][0], x[0][1])):
            f.write(f"{dt}\t{path}\n")
    print(f"\n列表已写入 {out}")

def _normalize_title(stem: str) -> str:
    """粗粒度标题归一化用于去重"""
    s = stem
    for pat in [
        r"_\d{4}-\d{2}-\d{2}.*",
        r"_\d+",
        r"（.*?）",
        r"\(.*?\)",
        r"关于印发",
        r"关于发布",
        r"关于印发",
        r"的通知",
    ]:
        s = re.sub(pat, "", s)
    return s[:60]

if __name__ == "__main__":
    main()
