"""Tells Aadi Identity about people added to or removed from Project Tracker through the organisation kit, so they can sign in and switch products.

Off unless a secret is set: IDENTITY_PRODUCT_SECRET, or else the IDENTITY_WEBHOOK_SECRET Tracker already uses to verify Identity's webhooks (it is the same product secret). A failure never undoes the
change in Tracker: the person is still added, and the message says what Identity answered."""
import logging
import os

import httpx

log = logging.getLogger("tracker.identity")


class IdentityClient:
    def __init__(self, base: str, secret: str, http: httpx.Client | None = None):
        self.base, self.secret = base.rstrip("/"), secret
        self.http = http or httpx.Client(timeout=10.0)

    @property
    def enabled(self) -> bool:
        return bool(self.base and self.secret)

    def _post(self, path: str, body: dict) -> dict:
        try:
            r = self.http.post(f"{self.base}{path}", json=body, headers={"Authorization": f"Bearer {self.secret}"})
        except httpx.HTTPError:
            log.exception("identity unreachable")
            return {"ok": False, "message": "Aadi Identity could not be reached. The person was added here; try again later."}
        if r.status_code >= 400:
            try:
                detail = r.json().get("detail", "")
            except ValueError:
                detail = ""
            return {"ok": False, "message": detail if isinstance(detail, str) and detail else f"Aadi Identity refused ({r.status_code})."}
        return {"ok": True, **r.json()}

    def enrol(self, tenant_id: str, email: str, name: str, actor: str) -> dict:
        out = self._post("/api/products/enrol", {"tenant_id": tenant_id, "email": email, "name": name, "actor": actor})
        if out["ok"]:
            out["message"] = "An invitation was sent by email." if out.get("invited") else "Added; they can sign in with their existing account."
        return out

    def remove(self, tenant_id: str, email: str, actor: str) -> dict:
        return self._post("/api/products/remove", {"tenant_id": tenant_id, "email": email, "actor": actor})


def _make() -> IdentityClient:
    return IdentityClient(os.environ.get("IDENTITY_ISSUER") or "https://id.aadiprojecttracker.aaditechnology.com", (os.environ.get("IDENTITY_PRODUCT_SECRET") or os.environ.get("IDENTITY_WEBHOOK_SECRET") or "").strip())  # one shared secret per product: the webhook secret doubles as the Bearer


CLIENT = _make()  # tests replace CLIENT.http / CLIENT.secret
