from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["Auth"])

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/login")
def login(request: LoginRequest):
    """
    Demo login endpoint.
    Accepts any email/password.
    """
    if request.email and request.password:
        return {"success": True, "token": "demo-token-123"}
    
    return {"success": False, "error": "Invalid credentials"}
