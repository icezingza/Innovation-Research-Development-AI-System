"""
Resilience & Advanced Fault-Tolerance Infrastructure (NRE v5.0.0 Sovereign Edition)
Includes: Circuit Breaker Pattern, Exponential Backoff + Jitter Retry, and Fallback Mechanics.
"""

import asyncio
import inspect
import logging
import random
import traceback
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from functools import wraps
from typing import Any

logger = logging.getLogger(__name__)

# =====================================================================
# Error Architecture & Domains
# =====================================================================


class ErrorSeverity(str, Enum):
    """Sovereign error severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorType(str, Enum):
    """Common enterprise error domains."""

    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    NOT_FOUND = "not_found"
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    EXTERNAL_API = "external_api"
    DATABASE = "database"
    CACHE = "cache"
    INTERNAL = "internal"


@dataclass
class NamoError(Exception):
    """Canonical base error class for NamoNexus systems."""

    message: str
    error_type: ErrorType
    severity: ErrorSeverity
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    traceback: str | None = None

    def __post_init__(self) -> None:
        """Capture standard traceback if not explicitly provided."""
        if not self.traceback:
            self.traceback = traceback.format_exc()

    def __str__(self) -> str:
        """Override to ensure dataclass-based exceptions yield string values."""
        return self.message

    def to_dict(self) -> dict[str, Any]:
        """Convert standard error attributes to serializeable dictionary."""
        return {
            "message": self.message,
            "error_type": self.error_type.value,
            "severity": self.severity.value,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "traceback": self.traceback
            if self.severity == ErrorSeverity.CRITICAL
            else None,
        }


class ValidationError(NamoError):
    """Validation exception triggered by client data inputs."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message=message,
            error_type=ErrorType.VALIDATION,
            severity=ErrorSeverity.LOW,
            details=details or {},
        )


class RateLimitError(NamoError):
    """Exception raised when API access speed threshold is breached."""

    def __init__(self, message: str, retry_after: int = 60) -> None:
        super().__init__(
            message=message,
            error_type=ErrorType.RATE_LIMIT,
            severity=ErrorSeverity.MEDIUM,
            details={"retry_after": retry_after},
        )


class ExternalAPIError(NamoError):
    """Exception raised during LLM or external microservice communications."""

    def __init__(
        self, message: str, api_name: str, status_code: int | None = None
    ) -> None:
        super().__init__(
            message=message,
            error_type=ErrorType.EXTERNAL_API,
            severity=ErrorSeverity.HIGH,
            details={"api_name": api_name, "status_code": status_code},
        )


class DatabaseError(NamoError):
    """Exception raised during relational, graph, or vector database calls."""

    def __init__(self, message: str, operation: str) -> None:
        super().__init__(
            message=message,
            error_type=ErrorType.DATABASE,
            severity=ErrorSeverity.CRITICAL,
            details={"operation": operation},
        )


# =====================================================================
# Circuit Breaker System (Prevent Cascading Failures)
# =====================================================================


class CircuitState(str, Enum):
    """Standard lifecycle states of the Circuit Breaker."""

    CLOSED = "closed"  # Normal operational state
    OPEN = "open"  # Failing state: instantly reject requests
    HALF_OPEN = "half_open"  # Recovery testing state


@dataclass
class CircuitBreakerConfig:
    """Settings dictating the threshold transitions of a Circuit Breaker."""

    failure_threshold: int = 5  # Sequential failures before tripping
    recovery_timeout: float = 30.0  # Seconds in OPEN state before testing recovery
    success_threshold: int = 2  # Consecutive successes in HALF_OPEN to close
    timeout: float = 10.0  # Maximum duration (seconds) allowed for execution


class CircuitBreaker:
    """Stateful sentinel shielding services from cascading failures."""

    def __init__(self, name: str, config: CircuitBreakerConfig | None = None) -> None:
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: datetime | None = None
        self.last_state_change: datetime = datetime.now(UTC)

    def __call__(self, func: Callable[..., Any]) -> Callable[..., Any]:
        """Wrap designated function as a decorator."""

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await self.call(func, *args, **kwargs)

        return wrapper

    async def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute the target callable while managing circuit transitions."""
        # 1. State Reconciliation
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._half_open()
            else:
                remaining = self._time_until_retry()
                raise NamoError(
                    message=f"Circuit breaker '{self.name}' is OPEN. Blocking execution.",
                    error_type=ErrorType.TIMEOUT,
                    severity=ErrorSeverity.HIGH,
                    details={"circuit": self.name, "retry_after_seconds": remaining},
                )

        # 2. Execution with Timeout
        try:
            result = await asyncio.wait_for(
                func(*args, **kwargs), timeout=self.config.timeout
            )
            self._on_success()
            return result

        except asyncio.TimeoutError:
            self._on_failure()
            raise NamoError(
                message=f"Operation timed out in circuit '{self.name}' (limit: {self.config.timeout}s)",
                error_type=ErrorType.TIMEOUT,
                severity=ErrorSeverity.HIGH,
                details={"circuit": self.name, "timeout": self.config.timeout},
            )

        except Exception as e:
            self._on_failure()
            # Preserve NamoError hierarchy, wrap others
            if isinstance(e, NamoError):
                raise
            raise DatabaseError(
                message=f"Error in circuit '{self.name}': {str(e)}",
                operation=func.__name__,
            ) from e

    def _on_success(self) -> None:
        """Process successful execution and clear failures."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self._close()
        else:
            self.failure_count = 0

    def _on_failure(self) -> None:
        """Register failure and evaluate transition to OPEN."""
        self.failure_count += 1
        self.last_failure_time = datetime.now(UTC)

        if self.state == CircuitState.HALF_OPEN:
            self._open()
        elif self.failure_count >= self.config.failure_threshold:
            self._open()

    def _open(self) -> None:
        """Trip the circuit breaker to OPEN state."""
        self.state = CircuitState.OPEN
        self.last_state_change = datetime.now(UTC)
        logger.warning(f"[CIRCUIT BREAKER] '{self.name}' TRIPPED (State: OPEN)")

    def _close(self) -> None:
        """Close the circuit breaker back to normal."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_state_change = datetime.now(UTC)
        logger.info(f"[CIRCUIT BREAKER] '{self.name}' RESET (State: CLOSED)")

    def _half_open(self) -> None:
        """Transitions circuit to HALF-OPEN for validation sweeps."""
        self.state = CircuitState.HALF_OPEN
        self.success_count = 0
        self.last_state_change = datetime.now(UTC)
        logger.info(
            f"[CIRCUIT BREAKER] '{self.name}' TESTING RECOVERY (State: HALF-OPEN)"
        )

    def _should_attempt_reset(self) -> bool:
        """Assess if recovery timeout interval has elapsed."""
        if not self.last_failure_time:
            return False
        elapsed = (datetime.now(UTC) - self.last_failure_time).total_seconds()
        return elapsed >= self.config.recovery_timeout

    def _time_until_retry(self) -> int:
        """Calculate remaining cooling down seconds."""
        if not self.last_failure_time:
            return 0
        elapsed = (datetime.now(UTC) - self.last_failure_time).total_seconds()
        remaining = max(0.0, self.config.recovery_timeout - elapsed)
        return int(remaining)


# =====================================================================
# Retry System (Exponential Backoff + Jitter)
# =====================================================================


@dataclass
class RetryConfig:
    """Config specifications for Retry strategies."""

    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    jitter: bool = True


class RetryHandler:
    """Executes target operations with Exponential Backoff + Jitter policies."""

    def __init__(self, config: RetryConfig | None = None) -> None:
        self.config = config or RetryConfig()

    def __call__(
        self,
        exceptions: tuple[type[Exception], ...] = (Exception,),
        on_retry: Callable[[int, Exception], Any] | None = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Decorator binding retry wrapper to targets."""

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            @wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> Any:
                last_exception = None

                for attempt in range(self.config.max_attempts):
                    try:
                        return await func(*args, **kwargs)

                    except exceptions as e:
                        last_exception = e
                        if attempt < self.config.max_attempts - 1:
                            delay = self._calculate_delay(attempt)
                            logger.warning(
                                f"[RETRY] Attempt {attempt + 1} failed for {func.__name__}. "
                                f"Retrying in {delay:.2f}s due to error: {str(e)}"
                            )
                            if on_retry:
                                if inspect.iscoroutinefunction(on_retry):
                                    await on_retry(attempt, e)
                                else:
                                    on_retry(attempt, e)
                            await asyncio.sleep(delay)
                        else:
                            logger.error(
                                f"[RETRY] Exhausted all {self.config.max_attempts} attempts "
                                f"for {func.__name__}. Final Failure."
                            )

                if last_exception:
                    raise last_exception

            return wrapper

        return decorator

    def _calculate_delay(self, attempt: int) -> float:
        """Compute wait interval utilizing backoff and uniform jitter logic."""
        delay = min(
            self.config.initial_delay * (self.config.exponential_base**attempt),
            self.config.max_delay,
        )
        if self.config.jitter:
            # Add uniform jitter between 50% and 150% of raw delay
            delay *= random.uniform(0.5, 1.5)
        return delay


# =====================================================================
# Fallback Cache System (Graceful Degradation)
# =====================================================================


class FallbackHandler:
    """Manages system fallback pathways when primary endpoints completely fail."""

    def __init__(self) -> None:
        self.fallback_cache: dict[str, dict[str, Any]] = {}

    def __call__(
        self, fallback_func: Callable[..., Any] | None = None
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Decorator wrapper registering optional backup functions."""

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            @wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> Any:
                try:
                    result = await func(*args, **kwargs)
                    # Sync to degradation cache on successful primary responses
                    cache_key = self._get_cache_key(func, args, kwargs)
                    self.fallback_cache[cache_key] = {
                        "result": result,
                        "timestamp": datetime.now(UTC),
                    }
                    return result

                except Exception as e:
                    logger.warning(
                        f"[FALLBACK] Primary endpoint '{func.__name__}' failed. "
                        f"Attempting graceful degradation path due to error: {str(e)}"
                    )

                    # 1. Custom programmatic fallback callable
                    if fallback_func:
                        try:
                            if inspect.iscoroutinefunction(fallback_func):
                                return await fallback_func(*args, **kwargs)
                            return fallback_func(*args, **kwargs)
                        except Exception as fallback_error:
                            logger.error(
                                f"[FALLBACK] Custom fallback function crashed: {str(fallback_error)}"
                            )

                    # 2. Local memory buffer fallback
                    cache_key = self._get_cache_key(func, args, kwargs)
                    cached = self.fallback_cache.get(cache_key)
                    if cached:
                        age = (datetime.now(UTC) - cached["timestamp"]).total_seconds()
                        if age < 3600.0:  # 1 hour maximum freshness threshold
                            logger.info(
                                f"[FALLBACK] serving stale cached response (Age: {age:.0f}s)"
                            )
                            return cached["result"]

                    # 3. Exhausted: propagate the original error
                    if isinstance(e, NamoError):
                        raise
                    raise NamoError(
                        message="All recovery fallbacks and cached models exhausted.",
                        error_type=ErrorType.INTERNAL,
                        severity=ErrorSeverity.CRITICAL,
                        details={"original_error": str(e)},
                    ) from e

            return wrapper

        return decorator

    def _get_cache_key(
        self, func: Callable[..., Any], args: tuple[Any, ...], kwargs: dict[str, Any]
    ) -> str:
        """Hash invocation arguments to generate unique cache key strings."""
        import hashlib

        key_str = f"{func.__name__}:{args}:{sorted(kwargs.items())}"
        return hashlib.md5(key_str.encode()).hexdigest()


# =====================================================================
# Centralized HTTP/API Error Handler
# =====================================================================


class ErrorHandler:
    """Orchestrates structured mapping and dynamic error responses."""

    def __init__(self) -> None:
        self.error_handlers: dict[ErrorType, Callable[[NamoError], Any]] = {}

    def register_handler(
        self, error_type: ErrorType, handler: Callable[[NamoError], Any]
    ) -> None:
        """Bind customized callback handlers to designated Error types."""
        self.error_handlers[error_type] = handler

    async def handle_error(self, error: Exception) -> dict[str, Any]:
        """Convert standard exception to structured enterprise JSON payload."""
        if not isinstance(error, NamoError):
            error = NamoError(
                message=str(error),
                error_type=ErrorType.INTERNAL,
                severity=ErrorSeverity.HIGH,
                details={"original_class": type(error).__name__},
            )

        log_level = self._get_log_level(error.severity)
        logger.log(
            log_level,
            f"[EXCEPTION GATE] Error caught: {error.message}",
            extra=error.to_dict(),
        )

        if error.error_type in self.error_handlers:
            try:
                handler = self.error_handlers[error.error_type]
                if inspect.iscoroutinefunction(handler):
                    await handler(error)
                else:
                    handler(error)
            except Exception as handler_err:
                logger.critical(
                    f"Secondary failure inside custom error handler: {str(handler_err)}"
                )

        return {
            "error": True,
            "message": error.message,
            "type": error.error_type.value,
            "severity": error.severity.value,
            "details": error.details,
            "timestamp": error.timestamp.isoformat(),
        }

    def _get_log_level(self, severity: ErrorSeverity) -> int:
        """Translate error severity levels to system logger values."""
        mapping = {
            ErrorSeverity.LOW: logging.INFO,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL,
        }
        return mapping.get(severity, logging.ERROR)
