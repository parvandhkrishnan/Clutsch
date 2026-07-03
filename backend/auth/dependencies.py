from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from .jwt_handler import decode_access_token
from .models import get_user_by_username, User, get_users_db
from utils.cache import config_cache

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    user_id: str = payload.get("user_id")
    if user_id is None:
        raise credentials_exception
    
    # Check cache for user object
    cache_key = f"user_{user_id}"
    cached_user = config_cache.get(cache_key)
    if cached_user:
        return cached_user

    # In a real app, you'd fetch from DB. Here we search get_users_db().
    for user in get_users_db():
        if user.id == user_id:
            # Cache the user object for 10 minutes (defined in config_cache)
            config_cache.set(cache_key, user)
            return user
            
    raise credentials_exception

async def get_current_active_user(current_user: User = Depends(get_current_user)):
    # You can add more checks here (e.g. is_active)
    return current_user

async def get_admin_user(current_user: User = Depends(get_current_active_user)):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation not permitted"
        )
    return current_user
