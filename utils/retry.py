from functools import wraps
from time import sleep
from typing import Type, Tuple, Callable, Any
import structlog

logger = structlog.get_logger(__name__)


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
) -> Callable:
    """
    Retry decorator with exponential backoff

    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay in seconds
        backoff: Backoff multiplier (delay *= backoff after each retry)
        exceptions: Tuple of exception types to catch and retry

    Usage:
        @retry(max_attempts=3, delay=1.0, backoff=2.0, exceptions=(requests.RequestException,))
        def my_function():
            ...
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            attempt = 1
            current_delay = delay

            while attempt <= max_attempts:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts:
                        logger.error(
                            "Max retries reached",
                            function=func.__name__,
                            attempt=attempt,
                            error=str(e)
                        )
                        raise

                    logger.warning(
                        "Retry attempt",
                        function=func.__name__,
                        attempt=attempt,
                        max_attempts=max_attempts,
                        delay=current_delay,
                        error=str(e)
                    )

                    sleep(current_delay)
                    current_delay *= backoff
                    attempt += 1

        return wrapper
    return decorator
