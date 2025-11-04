from datetime import datetime, timedelta
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from jose import JWTError, jwt
from passlib.hash import bcrypt
from sqlalchemy.orm import Session

from .config import get_settings
from .db import get_db
from .models import RefreshToken, User
from .schemas import LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


def _cookie_domain() -> str | None:
    return settings.COOKIE_DOMAIN or None


def _set_cookie(res: Response, name: str, value: str, max_age: int) -> None:
    res.set_cookie(
        name=name,
        value=value,
        max_age=max_age,
        httponly=True,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
        domain=_cookie_domain(),
        path="/",
    )


def _sign_access(uid: str) -> str:
    now = datetime.utcnow()
    exp = now + timedelta(minutes=settings.JWT_ACCESS_TTL_MIN)
    payload = {
        "sub": uid,
        "jti": str(uuid4()),
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
    }
    return jwt.encode(payload, settings.JWT_ACCESS_SECRET, algorithm="HS256")


def _sign_refresh(uid: str, db: Session, ip: str | None, ua: str | None) -> str:
    now = datetime.utcnow()
    exp = now + timedelta(days=settings.JWT_REFRESH_TTL_DAYS)
    jti = str(uuid4())
    payload = {
        "sub": uid,
        "jti": jti,
        "type": "refresh",
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
    }
    token = jwt.encode(payload, settings.JWT_REFRESH_SECRET, algorithm="HS256")
    try:
        user_id = int(uid)
    except (TypeError, ValueError):
        raise HTTPException(status_code=500, detail="Invalid user identifier")
    db.add(RefreshToken(user_id=user_id, jwt_id=jti, ip=ip, user_agent=ua))
    db.commit()
    return token


def _verify_access(token: str) -> dict:
    return jwt.decode(
        token,
        settings.JWT_ACCESS_SECRET,
        algorithms=["HS256"],
        audience=settings.JWT_AUDIENCE,
        issuer=settings.JWT_ISSUER,
    )


def _verify_refresh(token: str) -> dict:
    return jwt.decode(
        token,
        settings.JWT_REFRESH_SECRET,
        algorithms=["HS256"],
        audience=settings.JWT_AUDIENCE,
        issuer=settings.JWT_ISSUER,
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, response: Response, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.email == payload.email).one_or_none()
    if not user or not bcrypt.verify(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access = _sign_access(str(user.id))
    refresh = _sign_refresh(
        str(user.id),
        db,
        ip=request.client.host if request.client else None,
        ua=request.headers.get("user-agent"),
    )

    _set_cookie(response, "access_token", access, settings.JWT_ACCESS_TTL_MIN * 60)
    _set_cookie(response, "refresh_token", refresh, settings.JWT_REFRESH_TTL_DAYS * 24 * 3600)
    return TokenResponse()


@router.post("/refresh", response_model=TokenResponse)
def refresh(response: Response, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="Missing refresh token")

    try:
        payload = _verify_refresh(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    db_token = db.query(RefreshToken).filter(RefreshToken.jwt_id == payload.get("jti")).one_or_none()
    if not db_token or db_token.revoked:
        sub = payload.get("sub")
        try:
            user_id = int(sub) if sub is not None else None
        except (TypeError, ValueError):
            user_id = None
        if user_id is not None:
            db.query(RefreshToken).filter(RefreshToken.user_id == user_id).update({"revoked": True})
            db.commit()
        raise HTTPException(status_code=401, detail="Refresh reuse detected")

    db_token.revoked = True
    db.commit()

    sub = payload.get("sub")
    if sub is None:
        raise HTTPException(status_code=401, detail="Invalid refresh token payload")
    new_refresh = _sign_refresh(
        sub,
        db,
        ip=request.client.host if request.client else None,
        ua=request.headers.get("user-agent"),
    )
    new_access = _sign_access(sub)

    _set_cookie(response, "access_token", new_access, settings.JWT_ACCESS_TTL_MIN * 60)
    _set_cookie(response, "refresh_token", new_refresh, settings.JWT_REFRESH_TTL_DAYS * 24 * 3600)
    return TokenResponse()


@router.post("/logout", response_model=TokenResponse)
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> TokenResponse:
    token = request.cookies.get("access_token")
    if token:
        try:
            payload = _verify_access(token)
            sub = payload.get("sub")
            if sub is not None:
                try:
                    user_id = int(sub)
                except (TypeError, ValueError):
                    user_id = None
                if user_id is not None:
                    db.query(RefreshToken).filter(RefreshToken.user_id == user_id).update({"revoked": True})
                    db.commit()
        except JWTError:
            pass

    response.delete_cookie("access_token", path="/", domain=_cookie_domain())
    response.delete_cookie("refresh_token", path="/", domain=_cookie_domain())
    return TokenResponse()


def require_user(
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> str:
    token: str | None = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
    else:
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        payload = _verify_access(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Unauthorized")

    sub = payload.get("sub")
    if sub is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return sub
