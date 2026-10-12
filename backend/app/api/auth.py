from fastapi import APIRouter, HTTPException, status, Depends
from datetime import datetime, timezone
from app.models.user import LoginRequest, TokenResponse, UserResponse
from app.repositories.user_repo import user_repo
from app.core.security import verify_password, create_access_token
from app.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    user = await user_repo.get_by_username(req.username)
    if not user or not verify_password(req.password, user.get("hashed_password", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated"
        )
    
    token = create_access_token({"sub": str(user["_id"]), "role": user.get("role")})
    user_resp = UserResponse(
        id=str(user["_id"]),
        username=user["username"],
        email=user["email"],
        role=user["role"],
        full_name=user.get("full_name", user["username"]),
        is_active=user.get("is_active", True),
        created_at=user.get("created_at") or user.get("createdAt") or datetime.now(timezone.utc)
    )
    return TokenResponse(access_token=token, user=user_resp)

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    return UserResponse(
        id=str(current_user["_id"]),
        username=current_user["username"],
        email=current_user["email"],
        role=current_user["role"],
        full_name=current_user.get("full_name", current_user["username"]),
        is_active=current_user.get("is_active", True),
        created_at=current_user.get("created_at") or current_user.get("createdAt") or datetime.now(timezone.utc)
    )
