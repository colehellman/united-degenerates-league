from datetime import datetime, timedelta
from typing import Dict, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Circuit tripped, rejecting requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for API failover.

    Prevents cascading failures by stopping requests to failing services.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        timeout_seconds: int = 60,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.last_success_time: Optional[datetime] = None

    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                logger.info(f"Circuit breaker '{self.name}': Attempting reset (half-open)")
                self.state = CircuitState.HALF_OPEN
            else:
                time_remaining = self._time_until_reset()
                logger.warning(
                    f"Circuit breaker '{self.name}': OPEN - rejecting request. "
                    f"Retry in {time_remaining}s"
                )
                raise CircuitBreakerOpenError(
                    f"Circuit breaker '{self.name}' is OPEN. Retry in {time_remaining}s"
                )

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e

    def _on_success(self):
        """Record successful call"""
        self.failure_count = 0
        self.last_success_time = datetime.utcnow()

        if self.state == CircuitState.HALF_OPEN:
            logger.info(f"Circuit breaker '{self.name}': Test successful - CLOSING circuit")
            self.state = CircuitState.CLOSED

    def _on_failure(self):
        """Record failed call"""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()

        logger.warning(
            f"Circuit breaker '{self.name}': Failure {self.failure_count}/{self.failure_threshold}"
        )

        if self.failure_count >= self.failure_threshold:
            self._trip()

    def _trip(self):
        """Trip the circuit breaker (open it)"""
        self.state = CircuitState.OPEN
        logger.error(
            f"Circuit breaker '{self.name}': TRIPPED - threshold reached "
            f"({self.failure_count} failures). Circuit will remain open for {self.timeout_seconds}s"
        )

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if self.last_failure_time is None:
            return True

        time_since_failure = datetime.utcnow() - self.last_failure_time
        return time_since_failure.total_seconds() >= self.timeout_seconds

    def _time_until_reset(self) -> int:
        """Calculate seconds until circuit can be reset"""
        if self.last_failure_time is None:
            return 0

        time_since_failure = datetime.utcnow() - self.last_failure_time
        time_remaining = self.timeout_seconds - time_since_failure.total_seconds()
        return max(0, int(time_remaining))

    def reset(self):
        """Manually reset the circuit breaker"""
        logger.info(f"Circuit breaker '{self.name}': Manual reset")
        self.state = CircuitState.CLOSED
        self.failure_count = 0

    def get_status(self) -> Dict:
        """Get current circuit breaker status"""
        return {
            "name": self.name,
            "state": self.state,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "last_success_time": self.last_success_time.isoformat() if self.last_success_time else None,
            "time_until_reset": self._time_until_reset() if self.state == CircuitState.OPEN else 0,
        }


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open"""
    pass


class CircuitBreakerManager:
    """Manages multiple circuit breakers for different APIs"""

    def __init__(self):
        self.breakers: Dict[str, CircuitBreaker] = {}

    def get_breaker(
        self,
        name: str,
        failure_threshold: int = 5,
        timeout_seconds: int = 60,
    ) -> CircuitBreaker:
        """Get or create a circuit breaker"""
        if name not in self.breakers:
            self.breakers[name] = CircuitBreaker(
                name=name,
                failure_threshold=failure_threshold,
                timeout_seconds=timeout_seconds,
            )
        return self.breakers[name]

    def reset_all(self):
        """Reset all circuit breakers"""
        for breaker in self.breakers.values():
            breaker.reset()

    def get_all_status(self) -> Dict[str, Dict]:
        """Get status of all circuit breakers"""
        return {name: breaker.get_status() for name, breaker in self.breakers.items()}


# Global circuit breaker manager
circuit_breaker_manager = CircuitBreakerManager()
