import math
import time
from collections import deque
from collections.abc import Callable

from supportflow.errors import RequestError


class RateLimiter:
    """Ventana deslizante para un único proceso; usa el reloj monotónico."""

    def __init__(
        self, limit: int, window_seconds: float, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self.clock = clock
        self._requests: dict[str, deque[float]] = {}
        self._last_cleanup = clock()

    def check(self, client_ip: str) -> None:
        # No hay awaits: la comprobación y reserva son atómicas en el bucle ASGI.
        now = self.clock()
        cutoff = now - self.window_seconds
        if now - self._last_cleanup >= self.window_seconds:
            self._requests = {
                key: times for key, times in self._requests.items() if times[-1] > cutoff
            }
            self._last_cleanup = now

        times = self._requests.setdefault(client_ip, deque())
        while times and times[0] <= cutoff:
            times.popleft()
        if len(times) >= self.limit:
            retry_after = max(1, math.ceil(times[0] + self.window_seconds - now))
            raise RequestError(
                429,
                "RATE_LIMITED",
                "Has enviado demasiados mensajes. Espera antes de intentarlo de nuevo.",
                retryable=True,
                headers={"Retry-After": str(retry_after)},
            )
        times.append(now)
