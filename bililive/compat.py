from collections.abc import Mapping
from typing import Any

import httpx
import httpx._types as httpx_types


def _normalize_proxy_value(proxies: Any):
    if proxies is None:
        return None
    if isinstance(proxies, Mapping):
        if "all://" in proxies:
            return proxies["all://"]
        for value in proxies.values():
            if value is not None:
                return value
        return None
    return proxies


def patch_httpx_compat():
    if not hasattr(httpx_types, "ProxiesTypes") and hasattr(httpx_types, "ProxyTypes"):
        httpx_types.ProxiesTypes = httpx_types.ProxyTypes

    if getattr(httpx.AsyncClient, "__bililive_compat_patch__", False):
        return

    original_async_client = httpx.AsyncClient

    class CompatAsyncClient(original_async_client):
        __bililive_compat_patch__ = True

        def __init__(self, *args, proxies=Ellipsis, **kwargs):
            if proxies is not Ellipsis and "proxy" not in kwargs:
                kwargs["proxy"] = _normalize_proxy_value(proxies)
            super().__init__(*args, **kwargs)

    CompatAsyncClient.__name__ = original_async_client.__name__
    CompatAsyncClient.__qualname__ = original_async_client.__qualname__
    CompatAsyncClient.__module__ = original_async_client.__module__

    httpx.AsyncClient = CompatAsyncClient
