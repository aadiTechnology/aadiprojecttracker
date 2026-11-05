"""Demo mode only: lists the sample sign-ins shown below the login button. Not mounted in production."""
from fastapi import APIRouter

from .. import seed, seed_matrix
from ..perms import ROLE_DEFAULTS

router = APIRouter(prefix="/api/demo", tags=["demo"])


@router.get("/accounts")
def accounts():
    rows = [{"name": n, "role": ROLE_DEFAULTS[r][0], "title": t, "email": f"{k}@{seed.DOMAIN}", "hint": h}
            for k, n, r, t, _, _, h in seed.USERS]
    rows += [{"name": n, "role": ROLE_DEFAULTS[r][0], "title": f"{t} - {dept}", "email": f"{k}@{seed_matrix.DOMAIN}", "hint": h, "org": "matrix"}
             for k, n, r, t, dept, _, _, h in seed_matrix.PEOPLE if r != "employee" or k in ("ishaan.dixit",)]
    rows.append({"name": seed.PLATFORM[1], "role": "SaaS Platform Administrator", "title": "Platform", "email": f"{seed.PLATFORM[0]}@{seed.DOMAIN}", "hint": seed.PLATFORM[2]})
    return {"password": seed.DEMO_PASSWORD, "accounts": rows,
            "notice": "Illustrative demo data only. Never enter real data in a demo environment."}
