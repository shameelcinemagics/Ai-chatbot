from pydantic import BaseModel, EmailStr

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    ok: bool = True

class AskRequest(BaseModel):
    question: str

class AskResponse(BaseModel):
    sql: str
    rows: list[dict]
    summary: str
