"""Async wrappers for CPU-bound operations (bcrypt) to keep them off the event loop."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from passlib.context import CryptContext

# Shared thread pool for CPU-bound tasks (bcrypt hashing, etc.)
_bcrypt_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="bcrypt")

# Shared context — same as auth/models.py
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def hash_password(password: str) -> str:
    """Hash a password in a thread pool to avoid blocking the event loop."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_bcrypt_pool, pwd_context.hash, password)


async def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password in a thread pool to avoid blocking the event loop."""
    if not hashed_password:
        return False
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_bcrypt_pool, pwd_context.verify, plain_password, hashed_password)