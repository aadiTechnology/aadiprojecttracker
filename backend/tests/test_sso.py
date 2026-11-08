"""Sign-in through Aadi Identity. Identity itself is replaced by a local key pair and canned answers."""
import time
import uuid
from urllib.parse import parse_qs, urlparse

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwk, jwt
from sqlalchemy import select

from app import core, models as m
from app.routers import sso

ISS = "https://id.test.example"
SLUG = "aadi-technology-illustrative-demo"
TID = "11111111-1111-4111-8111-111111111111"  # the company as Identity knows it


def sub_for(email):
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, email))  # each person keeps one Identity ID


@pytest.fixture(scope="module")
def keypair():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
    pub = jwk.construct(key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode(), "RS256").to_dict()
    pub.update({"kid": "test-key", "use": "sig", "alg": "RS256"})
    return pem, pub


@pytest.fixture()
def identity(monkeypatch, keypair):
    pem, pub = keypair
    monkeypatch.setattr(sso, "MODE", "both")
    monkeypatch.setattr(sso, "ISSUER", ISS)
    monkeypatch.setattr(sso, "BASE_URL", "http://testserver")
    monkeypatch.setattr(sso, "_jwks", {"at": time.time(), "keys": [pub]})
    sso._used_codes.clear()
    state = {"claims": {}}

    def make_tokens(code, verifier):
        c = state["claims"]
        now = int(time.time())
        base = {"iss": ISS, "iat": now, "exp": now + 900, "sub": c["sub"], "email": c["email"], "name": "x", "tid": c["tid"], "tenant_slug": c["slug"], "product": "tracker"}
        id_token = jwt.encode({**base, "aud": sso.CLIENT_ID, "nonce": state["nonce"]}, pem, algorithm="RS256", headers={"kid": "test-key"})
        access = jwt.encode({**base, "aud": "tracker"}, pem, algorithm="RS256", headers={"kid": "test-key"})
        return {"id_token": id_token, "access_token": access, "refresh_token": "r", "token_type": "Bearer"}

    monkeypatch.setattr(sso, "exchange_code", make_tokens)
    return state


def begin(client, identity, email, slug=SLUG, sub=None, tid=None):
    """Starts sign-in, then plays Identity's part: remembers the nonce and returns the state."""
    r = client.get("/api/auth/sso/start", follow_redirects=False)
    assert r.status_code == 303
    q = parse_qs(urlparse(r.headers["location"]).query)
    assert r.headers["location"].startswith(ISS + "/authorize?")
    assert q["code_challenge_method"] == ["S256"] and q["client_id"] == [sso.CLIENT_ID]
    identity["nonce"] = q["nonce"][0]
    identity["claims"] = {"sub": sub or sub_for(email), "email": email, "tid": tid or TID, "slug": slug}
    return q["state"][0]


def finish(client, state, code="abc"):
    return client.get("/api/auth/sso/callback", params={"code": code, "state": state}, follow_redirects=False)


def test_local_mode_changes_nothing(client, monkeypatch):
    monkeypatch.setattr(sso, "MODE", "local")
    cfg = client.get("/api/auth/config").json()
    assert cfg["sso"] is False and cfg["local"] is True and cfg["logout_url"] is None
    assert client.get("/api/auth/sso/start", follow_redirects=False).status_code == 404


def test_happy_path_links_accounts_and_signs_in(client, identity):
    cfg = client.get("/api/auth/config").json()
    assert cfg["sso"] is True and cfg["local"] is True and cfg["mode"] == "both"
    sub, tid = sub_for("priya.rao@aadi.demo.test"), TID
    state = begin(client, identity, "priya.rao@aadi.demo.test")
    r = finish(client, state)
    assert r.status_code == 303 and "?sso=" in r.headers["location"]
    code = parse_qs(urlparse(r.headers["location"]).query)["sso"][0]
    ex = client.post("/api/auth/sso/exchange", json={"code": code})
    assert ex.status_code == 200
    me = client.get("/api/me", headers={"Authorization": "Bearer " + ex.json()["token"]})
    assert me.status_code == 200 and me.json()["user"]["name"] == "Priya Rao"
    # the first sign-in linked both sides
    with core.SessionLocal() as db:
        u = db.execute(select(m.User).where(m.User.email == "priya.rao@aadi.demo.test")).scalar_one()
        t = db.execute(select(m.Tenant).where(m.Tenant.slug == SLUG)).scalar_one()
        assert u.identity_id == sub and t.identity_tenant_id == tid
    # next time the match is by Identity ID, not e-mail
    state = begin(client, identity, "different-address@example.com", sub=sub, tid=tid)
    assert "?sso=" in finish(client, state).headers["location"]


def test_one_time_code_cannot_be_reused(client, identity):
    state = begin(client, identity, "dev.patel@aadi.demo.test")
    code = parse_qs(urlparse(finish(client, state).headers["location"]).query)["sso"][0]
    assert client.post("/api/auth/sso/exchange", json={"code": code}).status_code == 200
    assert client.post("/api/auth/sso/exchange", json={"code": code}).status_code == 401


def test_unknown_person_is_refused_not_created(client, identity):
    state = begin(client, identity, "stranger@example.com")
    assert finish(client, state).headers["location"].endswith("sso_error=no_account")
    with core.SessionLocal() as db:
        assert db.execute(select(m.User).where(m.User.email == "stranger@example.com")).first() is None


def test_person_without_membership_in_company_gets_no_role(client, identity):
    # Anil belongs to the matrix organization only
    state = begin(client, identity, "anil.deshpande@matrix.demo.test", slug=SLUG)
    assert finish(client, state).headers["location"].endswith("sso_error=no_access")


def test_unknown_company_is_refused(client, identity):
    state = begin(client, identity, "priya.rao@aadi.demo.test", slug="no-such-company", tid=str(uuid.uuid4()))
    assert finish(client, state).headers["location"].endswith("sso_error=no_company")


def test_wrong_state_and_missing_cookie(client, identity):
    begin(client, identity, "priya.rao@aadi.demo.test")
    assert finish(client, "forged").headers["location"].endswith("sso_error=state")
    client.cookies.clear()
    assert finish(client, "anything").headers["location"].endswith("sso_error=expired")


def test_token_signed_by_another_key_is_rejected(client, identity, monkeypatch):
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048).private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
    state = begin(client, identity, "priya.rao@aadi.demo.test")
    now = int(time.time())
    forged = jwt.encode({"iss": ISS, "aud": sso.CLIENT_ID, "sub": "x", "exp": now + 900, "nonce": identity["nonce"]}, other, algorithm="RS256", headers={"kid": "test-key"})
    monkeypatch.setattr(sso, "exchange_code", lambda c, v: {"id_token": forged, "access_token": forged})
    assert finish(client, state).headers["location"].endswith("sso_error=exchange")


def test_platform_mode_disables_password_endpoints(client, identity, monkeypatch):
    monkeypatch.setattr(sso, "MODE", "platform")
    assert client.get("/api/auth/config").json()["local"] is False
    r = client.post("/api/auth/login", json={"email": "priya.rao@aadi.demo.test", "password": "Tracker@Demo26"})
    assert r.status_code == 403 and r.json()["detail"]["code"] == "SSO_ONLY"
    assert client.post("/api/auth/forgot", json={"email": "a@b.co"}).status_code == 403
    assert client.post("/api/auth/reset", json={"token": "x", "password": "Aaaaaaaa1x"}).status_code == 403


def test_sso_session_is_shorter_than_local(client, identity):
    state = begin(client, identity, "isha.kapoor@aadi.demo.test")
    code = parse_qs(urlparse(finish(client, state).headers["location"]).query)["sso"][0]
    tok = client.post("/api/auth/sso/exchange", json={"code": code}).json()["token"]
    claims = jwt.decode(tok, core.SECRET, algorithms=["HS256"])
    assert claims["exp"] - time.time() <= sso.SSO_SESSION_MINUTES * 60 + 5


def test_a_rotated_signing_key_is_picked_up_without_a_restart(client, identity, monkeypatch, keypair):
    """Identity rotates its key: tokens signed with the new key must verify after one refresh of the cached key list."""
    old_pem, old_pub = keypair
    new = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    new_pem = new.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
    new_pub = jwk.construct(new.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode(), "RS256").to_dict()
    new_pub.update({"kid": "rotated-key", "use": "sig", "alg": "RS256"})
    fetched = []
    monkeypatch.setattr(sso, "_get_json", lambda url, *a, **k: fetched.append(url) or {"keys": [old_pub, new_pub]})  # what Identity now publishes
    now = int(time.time())
    token = jwt.encode({"iss": ISS, "aud": "tracker", "sub": "x", "exp": now + 900}, new_pem, algorithm="RS256", headers={"kid": "rotated-key"})
    assert sso.verify_identity_token(token, "tracker")["sub"] == "x"  # the cache only knew the old key, so it refreshed once
    assert len(fetched) == 1
    sso.verify_identity_token(token, "tracker")
    assert len(fetched) == 1  # and now it is cached
    # a token with a key nobody published is still refused (after one refresh, not a loop)
    other = jwt.encode({"iss": ISS, "aud": "tracker", "sub": "x", "exp": now + 900}, old_pem, algorithm="RS256", headers={"kid": "never-published"})
    with pytest.raises(Exception):
        sso.verify_identity_token(other, "tracker")
    assert len(fetched) == 2
