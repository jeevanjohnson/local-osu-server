import functools
import inspect
from datetime import datetime

from colorama import Fore, Style

success = lambda m: print(f"{Fore.GREEN}{m}{Style.RESET_ALL}")
error = lambda m: print(f"{Fore.RED}{m}{Style.RESET_ALL}")
warning = lambda m: print(f"{Fore.YELLOW}{m}{Style.RESET_ALL}")
info = lambda m: print(f"{Fore.CYAN}{m}{Style.RESET_ALL}")


def log_time(func):
    if inspect.iscoroutinefunction(func):

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):  # type: ignore
            start_time = datetime.now()
            result = await func(*args, **kwargs)
            end_time = datetime.now()

            try:
                func.call_count += 1
            except AttributeError:
                func.call_count = 1

            delta = end_time - start_time
            duration = delta.total_seconds()
            mins = duration // 60
            secs = duration % 60
            ms = delta.microseconds // 1000

            msg = (
                f"[{func.__qualname__}] took {mins:.0f}m {secs:.0f}s {ms:.1f}ms to execute "
                f"on call #{func.call_count}"
            )

            success(msg)

            return result

        return wrapper
    else:

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = datetime.now()
            result = func(*args, **kwargs)
            end_time = datetime.now()

            try:
                func.call_count += 1
            except AttributeError:
                func.call_count = 1

            delta = end_time - start_time
            duration = delta.total_seconds()
            mins = duration // 60
            secs = duration % 60
            ms = delta.microseconds // 1000

            msg = (
                f"[{func.__qualname__}] took {mins:.0f}m {secs:.0f}s {ms:.2f}ms to execute "
                f"on call #{func.call_count}"
            )

            success(msg)

            return result

        return wrapper
