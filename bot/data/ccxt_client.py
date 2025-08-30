from typing import Optional
import ccxt


def make_exchange(exchange_id: str, api_key: Optional[str] = None, secret: Optional[str] = None, password: Optional[str] = None, enable_rate_limit: bool = True):
    klass = getattr(ccxt, exchange_id)
    params = {"enableRateLimit": enable_rate_limit}
    if api_key:
        params["apiKey"] = api_key
    if secret:
        params["secret"] = secret
    if password:
        params["password"] = password
    return klass(params)
