"""
Janela do limite de tentativas de login, sem banco (#35).

Spec: SPEC/2026-11-25-auth-admin-usuarios.md
"""

from src.backend.modules.auth.rate_limit import LoginRateLimiter


def test_window_expires_after_15_minutes():
    now = [1000.0]
    limiter = LoginRateLimiter(clock=lambda: now[0])
    key = limiter.key("1.2.3.4", "ana@teste.com")
    for _ in range(5):
        limiter.record_failure(key)
    assert limiter.retry_after(key) == 15 * 60
    now[0] += 15 * 60 - 1
    assert limiter.retry_after(key) == 1
    now[0] += 1
    assert limiter.retry_after(key) == 0


def test_limit_is_per_ip():
    limiter = LoginRateLimiter()
    for _ in range(5):
        limiter.record_failure(limiter.key("1.1.1.1", "ana@teste.com"))
    assert limiter.retry_after(limiter.key("1.1.1.1", "ana@teste.com")) > 0
    assert limiter.retry_after(limiter.key("2.2.2.2", "ana@teste.com")) == 0
