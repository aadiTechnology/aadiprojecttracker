"""Reads docs/Aadi Technology Matrix_V4.xlsx and writes videos/live/.data.json (git-ignored). The figures stay in the workbook and this local file; no script copies them."""
import json, pathlib, sys
import openpyxl
root = pathlib.Path(__file__).resolve().parents[2]
ws = openpyxl.load_workbook(root / "docs" / "Aadi Technology Matrix_V4.xlsx", data_only=True).worksheets[0]
DEPT = {"Management": "Management", "SoftwareDevelopment": "Software Development", "Marketing&Sales": "Marketing & Sales"}
TAG = {"Education": "Education", "SoftwareServices": "Software Services", "Marketing": "Marketing", "Sales": "Sales", "DogitalProduct": "Digital Product", "DigitalProduct": "Digital Product",
       "SecuritySolution": "Security Solution", "InteriorDesign": "Interior Design", "BusinessConsulting": "Business Consulting", "Ecommerce": "E-commerce"}
FIX = {"Intrenship": "Internship"}
cols = [c for c in range(6, ws.max_column + 1) if ws.cell(3, c).value]
people = [{"name": str(ws.cell(3, c).value).strip(), "department": DEPT[str(ws.cell(2, c).value).strip()], "salary": int(ws.cell(4, c).value)} for c in cols]
hours = int(ws["B2"].value); rate = int(ws["E3"].value)
projects, r = [], 5
while ws.cell(r, 2).value and ws.cell(r, 1).value == "Allocation":
    name = FIX.get(str(ws.cell(r, 2).value).strip(), str(ws.cell(r, 2).value).strip())
    tags = [TAG[t] for t in str(ws.cell(r, 3).value).strip().split("/")]
    alloc = {people[i]["name"]: round(float(ws.cell(r, c).value or 0) * 100) for i, c in enumerate(cols) if (ws.cell(r, c).value or 0) > 0}
    projects.append({"name": name, "tags": tags, "alloc": alloc, "revenue": int(ws.cell(r + 2, 5).value), "cost": int(ws.cell(r + 2, 4).value)})
    r += 3
out = {"hours": hours, "rate": rate, "people": people, "projects": projects, "totals": {"cost": int(ws["D44"].value), "bench": int(ws["D49"].value), "pool": int(ws["D47"].value)}}
(root / "videos" / "live" / ".data.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print(len(people), "people,", len(projects), "projects,", sorted({d['department'] for d in people}), "tags:", sorted({t for p in projects for t in p['tags']}))
