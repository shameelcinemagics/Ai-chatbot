from fastapi import APIRouter, Depends, HTTPException, Request, Response, Header
from sqlalchemy.orm import Session
from passlib.hash import bcrypt
from jose import jwt, JWTError
from datetime import datetime, timedelta
from uuid import uuid4

from .schemas import LoginRequest, TokenResponse
from .db import get_db
from .models import User, RefreshToken
from .config import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()

def _set_cookie(res: Response, name: str, value: str, max_age: int):
    res.set_cookie(
        name=name,
        value=value,
        max_age=max_age,
        httponly=True,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
        domain=settings.COOKIE_DOMAIN,
        path="/",
    )

def _sign_access(uid: str) -> str:
    now = datetime.utcnow()
    exp = now + timedelta(minutes=settings.JWT_ACCESS_TTL_MIN)
    payload = {"sub": uid, "jti": str(uuid4()), "type": "access", "iat": int(now.timestamp()), "exp": int(exp.timestamp()),
               "iss": settings.JWT_ISSUER, "aud": settings.JWT_AUDIENCE}
    return jwt.encode(payload, settings.JWT_ACCESS_SECRET, algorithm="HS256")

def _sign_refresh(uid: str, db: Session, ip: str | None, ua: str | None) -> str:
    now = datetime.utcnow()
    exp = now + timedelta(days=settings.JWT_REFRESH_TTL_DAYS)
    jti = str(uuid4())
    token = jwt.encode(
        {"sub": uid, "jti": jti, "type": "refresh", "iat": int(now.timestamp()), "exp": int(exp.timestamp()),
         "iss": settings.JWT_ISSUER, "aud": settings.JWT_AUDIENCE},
        settings.JWT_REFRESH_SECRET, algorithm="HS256"
    )
    db.add(RefreshToken(user_id=uid, jwt_id=jti, ip=ip, user_agent=ua))
    db.commit()
    return token

def _verify_access(token: str) -> dict:
    return jwt.decode(token, settings.JWT_ACCESS_SECRET, algorithms=["HS256"],
                      audience=settings.JWT_AUDIENCE, issuer=settings.JWT_ISSUER)

def _verify_refresh(token: str) -> dict:
    return jwt.decode(token, settings.JWT_REFRESH_SECRET, algorithms=["HS256"],
                      audience=settings.JWT_AUDIENCE, issuer=settings.JWT_ISSUER)

@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, response: Response, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).one_or_none()
    if not user or not bcrypt.verify(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access = _sign_access(str(user.id))
    refresh = _sign_refresh(str(user.id), db, ip=request.client.host if request.client else None, ua=request.headers.get("user-agent"))

    _set_cookie(response, "access_token", access, settings.JWT_ACCESS_TTL_MIN * 60)
    _set_cookie(response, "refresh_token", refresh, settings.JWT_REFRESH_TTL_DAYS * 24 * 3600)
    return TokenResponse()

@router.post("/refresh", response_model=TokenResponse)
def refresh(response: Response, request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="Missing refresh token")

    try:
        payload = _verify_refresh(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    db_token = db.query(RefreshToken).filter(RefreshToken.jwt_id == payload.get("jti")).one_or_none()
    if not db_token or db_token.revoked:
        # revoke all tokens for user if reuse detected
        db.query(RefreshToken).filter(RefreshToken.user_id == payload.get("sub")).update({"revoked": True})
        db.commit()
        raise HTTPException(status_code=401, detail="Refresh reuse detected")

    # rotate: revoke old, issue new
    db_token.revoked = True
    db.commit()

    new_refresh = _sign_refresh(payload["sub"], db, ip=request.client.host if request.client else None, ua=request.headers.get("user-agent"))
    new_access = _sign_access(payload["sub"])

    _set_cookie(response, "access_token", new_access, settings.JWT_ACCESS_TTL_MIN * 60)
    _set_cookie(response, "refresh_token", new_refresh, settings.JWT_REFRESH_TTL_DAYS * 24 * 3600)
    return TokenResponse()

@router.post("/logout", response_model=TokenResponse)
def logout(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if token:
        try:
            payload = _verify_access(token)
            db.query(RefreshToken).filter(RefreshToken.user_id == payload["sub"]).update({"revoked": True})
            db.commit()
        except JWTError:
            pass
    res = Response()
    res.delete_cookie("access_token", path="/", domain=settings.COOKIE_DOMAIN)
    res.delete_cookie("refresh_token", path="/", domain=settings.COOKIE_DOMAIN)
    return TokenResponse()


def require_user(access_token: str | None = Header(default=None, alias="Authorization")) -> str:
    # Accept "Bearer xxx" header or cookie
    from fastapi import Request
    # This helper is simpler: read from cookie if header is absent
    import contextvars
    req_var: contextvars.ContextVar[Request] = contextvars.ContextVar("req")
    try:
        req = req_var.get()
    except LookupError:
        req = None
    token = None
    if access_token and access_token.startswith("Bearer "):
        token = access_token[7:]
    elif req:
        token = req.cookies.get("access_token")  # type: ignore
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        payload = _verify_access(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return payload["sub"]
