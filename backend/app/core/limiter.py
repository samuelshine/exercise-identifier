"""
slowapi rate-limit singleton.

Routers import `limiter` and decorate endpoints. The limiter instance is
attached to `app.state.limiter` in main.py so slowapi's middleware finds it.

Behind a load balancer, X-Forwarded-For is the real client IP — slowapi's
default key function honors it when the header is present, so no custom
key resolver is needed for the typical deployment.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
