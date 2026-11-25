"""
Trim — Limite de tentativas de login (SPEC/2026-11-25-auth-admin-usuarios.md, #35).

A spec da AP1 (SPEC/2026-09-29-autenticacao.md) pede 5 tentativas por IP e e-mail em 15 minutos,
depois 429. As falhas ficam em memória, por processo: o deploy roda um processo só (Procfile), e um
reinício só zera a contagem, sem liberar nada que já tenha passado do limite por mais de 15 minutos.
Um login certo zera a contagem daquele IP e e-mail.
"""

import math
import time
from collections import deque
from collections.abc import Callable
from threading import Lock

MAX_FAILURES = 5
WINDOW_SECONDS = 15 * 60


class LoginRateLimiter:
    def __init__(
        self, max_failures: int = MAX_FAILURES, window: float = WINDOW_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.max_failures = max_failures
        self.window = window
        self.clock = clock
        self._failures: dict[tuple[str, str], deque[float]] = {}
        self._lock = Lock()

    @staticmethod
    def key(ip: str | None, email: str) -> tuple[str, str]:
        return (ip or "?", email.strip().lower())

    def _recent(self, key: tuple[str, str]) -> deque[float]:
        now = self.clock()
        attempts = self._failures.setdefault(key, deque())
        while attempts and now - attempts[0] >= self.window:
            attempts.popleft()
        return attempts

    def retry_after(self, key: tuple[str, str]) -> int:
        """Segundos até poder tentar de novo; 0 se ainda pode."""
        with self._lock:
            attempts = self._recent(key)
            if len(attempts) < self.max_failures:
                return 0
            return max(1, math.ceil(self.window - (self.clock() - attempts[0])))

    def record_failure(self, key: tuple[str, str]) -> None:
        with self._lock:
            self._recent(key).append(self.clock())

    def reset(self, key: tuple[str, str]) -> None:
        with self._lock:
            self._failures.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._failures.clear()


login_limiter = LoginRateLimiter()
