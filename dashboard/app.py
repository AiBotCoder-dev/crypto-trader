"""Read-only public dashboard for the crypto trader bot.

Proxies a small set of GET endpoints from the freqtrade REST API so the
freqtrade API itself (which also exposes trading controls) never has to be
reachable from the internet. This app has no write endpoints at all.
"""

import os

import requests
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

FT_API_URL = os.environ.get("FT_API_URL", "http://127.0.0.1:8080")
FT_AUTH = (
    os.environ.get("FT_USERNAME", "trader"),
    os.environ.get("FT_PASSWORD", "paper-trading-only"),
)

app = FastAPI(title="crypto-trader dashboard", docs_url=None, redoc_url=None)


def ft_get(path: str, params: dict | None = None):
    try:
        resp = requests.get(
            f"{FT_API_URL}/api/v1/{path}", auth=FT_AUTH, params=params, timeout=10
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"freqtrade API unreachable: {exc}") from exc
    return resp.json()


@app.get("/api/summary")
def summary():
    config = ft_get("show_config")
    profit = ft_get("profit")
    balance = ft_get("balance")
    daily = ft_get("daily", {"timescale": 30})
    open_trades = ft_get("status")
    closed = ft_get("trades", {"limit": 500})

    closed_trades = closed.get("trades", [])
    # API returns oldest-first; show the 10 most recent, newest on top.
    recent_closed = list(reversed(closed_trades[-10:]))

    return {
        "bot_name": config.get("bot_name"),
        "strategy": config.get("strategy"),
        "dry_run": config.get("dry_run"),
        "state": config.get("state"),
        "exchange": config.get("exchange"),
        "stake_currency": config.get("stake_currency"),
        "balance_total": balance.get("total"),
        "profit": profit,
        "daily": daily.get("data", []),
        "open_trades": open_trades,
        "closed_trades": recent_closed,
    }


app.mount(
    "/",
    StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static"), html=True),
    name="static",
)
