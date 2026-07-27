"""Shared rate limiter instance for the entire application."""
from slowapi import Limiter
from slowapi.util import get_remote_address

# Single shared limiter instance — both main.py and all routers import this.
limiter = Limiter(key_func=get_remote_address)