import time
import random
import functools
from typing import Callable, Any

def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 10.0):
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries >= max_retries:
                        print(f"Max retries reached for {func.__name__}. Error: {e}")
                        raise
                    
                    delay = min(base_delay * (2 ** (retries - 1)) + random.uniform(0, 1), max_delay)
                    print(f"Retry {retries}/{max_retries} for {func.__name__} after {delay:.2f}s due to error: {e}")
                    time.sleep(delay)
            return func(*args, **kwargs)
        return wrapper
    return decorator

def async_retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 10.0):
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries >= max_retries:
                        print(f"Max retries reached for {func.__name__}. Error: {e}")
                        raise
                    
                    delay = min(base_delay * (2 ** (retries - 1)) + random.uniform(0, 1), max_delay)
                    print(f"Retry {retries}/{max_retries} for {func.__name__} after {delay:.2f}s due to error: {e}")
                    import asyncio
                    await asyncio.sleep(delay)
            return await func(*args, **kwargs)
        return wrapper
    return decorator
