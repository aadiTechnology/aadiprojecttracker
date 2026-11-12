"""Turns docs/Aadi Technology Matrix_V4.xlsx (sheet BusinessView) into backend/app/seed_data/aadi_matrix.json, the data behind the Aadi-Test seed.
Run only when the workbook changes:  python backend/tools/build_matrix_seed.py     (needs openpyxl; the seed itself reads the JSON, not the workbook)

Layout of the sheet: row 2 department per person, row 3 person, row 4 monthly salary, then for every project three rows (Allocation = share of the
month, Efforts = hours, Budget = rupees) with the tag in column C, cost in D and revenue in E of the Budget row. People are columns F.. until the first empty one."""
import json
import re
import sys
from pathlib import Path

import openpyxl

HERE = Path(__file__).resolve().parent
SRC = HERE.parents[1] / "docs" / "Aadi Technology Matrix_V4.xlsx"
OUT = HERE.parent / "app" / "seed_data" / "aadi_matrix.json"

SPLIT = re.compile(r"(?<=[a-z])(?=[A-Z])|&|/")


def pretty(s: str) -> str:
    """SoftwareDevelopment -> Software Development; Marketing&Sales -> Marketing & Sales; Education/Software -> Education / Software."""
    s = (s or "").strip().replace("&", " & ").replace("/", " / ")
    s = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", s)
    return re.sub(r"\s+", " ", s)


TYPOS = {"Dogital Product": "Digital Product", "Intrenship": "Internship"}  # obvious spelling slips in the workbook, corrected in the seed


def tags_of(s: str) -> list[str]:
    """'Education/Software Services' -> ['Education', 'Software Services']: one project carries several tags."""
    return [TYPOS.get(t, t) for t in (x.strip() for x in pretty(s).split("/")) if t]


def main() -> None:
    wb = openpyxl.load_workbook(SRC, data_only=True)
    ws = wb["BusinessView"]
    rows = list(ws.iter_rows(values_only=True))
    month = str(rows[0][4]).strip()  # "November"
    hours = float(rows[1][1])  # monthly hours (160)
    rate = float(rows[2][4])  # hourly rate (250)
    cols = []
    c = 5
    while c < len(rows[2]) and rows[2][c]:
        cols.append(c)
        c += 1
    people = [{"name": str(rows[2][i]).strip(), "department": pretty(rows[1][i]), "salary": float(rows[3][i])} for i in cols]
    projects = []
    r = 4
    while r + 2 < len(rows) and rows[r][0] == "Allocation":
        alloc, eff, bud = rows[r], rows[r + 1], rows[r + 2]
        projects.append({
            "name": TYPOS.get(str(alloc[1]).strip(), str(alloc[1]).strip()), "tags": tags_of(str(alloc[2])), "cost": float(bud[3] or 0), "revenue": float(bud[4] or 0),
            "allocation": {people[k]["name"]: round(float(alloc[i] or 0) * 100) for k, i in enumerate(cols) if float(alloc[i] or 0) > 0},
            "hours": {people[k]["name"]: round(float(eff[i] or 0), 1) for k, i in enumerate(cols) if float(eff[i] or 0) > 0},
            "cost_by_person": {people[k]["name"]: round(float(bud[i] or 0)) for k, i in enumerate(cols) if float(bud[i] or 0) > 0},
        })
        r += 3
    data = {"source": "Aadi Technology Matrix_V4.xlsx / BusinessView", "month": month, "monthly_hours": hours, "hourly_rate": rate,
            "departments": sorted({p["department"] for p in people}), "people": people, "tags": sorted({t for p in projects for t in p["tags"]}), "projects": projects}
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    print("wrote", OUT, "-", len(people), "people,", len(projects), "projects,", len(data["tags"]), "tags")


if __name__ == "__main__":
    sys.exit(main())
