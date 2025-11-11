#!/usr/bin/env python3
"""
Custom exporter that scrapes CoinGecko public API and exposes metrics via prometheus_client.
Update interval defaults to 20 seconds (can be overridden with env var).
Exposed on 0.0.0.0:8000 by default.
"""

import time
import os
import logging
import requests
from datetime import datetime
from prometheus_client import start_http_server, Gauge

# Configuration
UPDATE_INTERVAL = int(os.getenv("UPDATE_INTERVAL", "20"))  # seconds
PORT = int(os.getenv("EXPORTER_PORT", "8000"))

COINS = os.getenv("COINS", "bitcoin,ethereum,dogecoin,cardano,litecoin").split(",")
COINGECKO_URL = "https://api.coingecko.com/api/v3/coins/markets"

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("custom_exporter")

# Prometheus metrics (all with coin & symbol labels)
price_usd = Gauge("external_coin_price_usd", "Current coin price in USD", ["coin", "symbol"])
price_change_24h = Gauge("external_coin_price_change_24h_percent", "Price change in last 24h (percent)", ["coin", "symbol"])
price_change_7d = Gauge("external_coin_price_change_7d_percent", "Price change in last 7d (percent)", ["coin", "symbol"])
market_cap_usd = Gauge("external_coin_market_cap_usd", "Coin market cap in USD", ["coin", "symbol"])
total_volume_usd = Gauge("external_coin_total_volume_usd", "24h total volume in USD", ["coin", "symbol"])
circulating_supply = Gauge("external_coin_circulating_supply", "Circulating supply", ["coin", "symbol"])
total_supply = Gauge("external_coin_total_supply", "Total supply (CoinGecko)", ["coin", "symbol"])
market_cap_rank = Gauge("external_coin_market_cap_rank", "Market cap rank", ["coin", "symbol"])
high_24h = Gauge("external_coin_high_24h_usd", "24h high price in USD", ["coin", "symbol"])
low_24h = Gauge("external_coin_low_24h_usd", "24h low price in USD", ["coin", "symbol"])
ath_usd = Gauge("external_coin_ath_usd", "All-time high price in USD", ["coin", "symbol"])
ath_change_percent = Gauge("external_coin_ath_change_percent", "ATH change percent", ["coin", "symbol"])
last_updated_timestamp = Gauge("external_coin_last_updated_timestamp", "Last updated timestamp (Unix)", ["coin", "symbol"])

# Derived/computed metrics
price_to_mcap_ratio = Gauge("external_coin_price_to_market_cap_ratio", "Price / MarketCap ratio", ["coin", "symbol"])
volume_to_mcap_ratio = Gauge("external_coin_volume_to_market_cap_ratio", "Volume / MarketCap ratio", ["coin", "symbol"])

# Exporter metadata
exporter_up = Gauge("custom_exporter_up", "1 if the last scrape succeeded", [])
request_duration_seconds = Gauge("custom_exporter_request_duration_seconds", "Duration of last external API request in seconds", ["endpoint"])
coins_scraped_total = Gauge("custom_exporter_coins_scraped_total", "Number of coins scraped during last update", [])


def fetch_coingecko():
    params = {
        "vs_currency": "usd",
        "ids": ",".join(COINS),
        "order": "market_cap_desc",
        "per_page": len(COINS),
        "page": 1,
        "sparkline": "false",
        "price_change_percentage": "24h,7d",
    }

    try:
        start = time.time()
        r = requests.get(COINGECKO_URL, params=params, timeout=10)
        duration = time.time() - start
        request_duration_seconds.labels(endpoint="coingecko").set(duration)

        r.raise_for_status()
        data = r.json()
        exporter_up.set(1)
        logger.debug("CoinGecko response length: %d", len(data))
        return data
    except Exception as e:
        exporter_up.set(0)
        logger.error("Error fetching CoinGecko: %s", str(e))
        return None


def _parse_timestamp_iso8601(ts_str):
    if not ts_str:
        return None
    # Accept various ISO formats returned by CoinGecko (with or without fractional seconds)
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            dt = datetime.strptime(ts_str, fmt)
            return int(dt.timestamp())
        except Exception:
            continue
    # Last resort: try dateutil if available
    try:
        from dateutil import parser
        dt = parser.isoparse(ts_str)
        return int(dt.timestamp())
    except Exception:
        return None


def update_metrics(data):
    if not data:
        coins_scraped_total.set(0)
        return

    coins_scraped_total.set(len(data))

    for coin in data:
        coin_id = coin.get("id", "")
        symbol = coin.get("symbol", "")
        # metrics present in CoinGecko /coins/markets response
        price = coin.get("current_price")
        change_24h = coin.get("price_change_percentage_24h")
        change_7d = coin.get("price_change_percentage_7d_in_currency") or coin.get("price_change_percentage_7d")
        mcap = coin.get("market_cap")
        volume = coin.get("total_volume")
        supply = coin.get("circulating_supply")
        t_supply = coin.get("total_supply")
        rank = coin.get("market_cap_rank")
        high = coin.get("high_24h")
        low = coin.get("low_24h")
        ath = coin.get("ath")
        ath_chg = coin.get("ath_change_percentage")
        last_updated = coin.get("last_updated")

        # Sanity checks and set metrics if available
        if price is not None:
            price_usd.labels(coin=coin_id, symbol=symbol).set(float(price))
        if change_24h is not None:
            price_change_24h.labels(coin=coin_id, symbol=symbol).set(float(change_24h))
        if change_7d is not None:
            price_change_7d.labels(coin=coin_id, symbol=symbol).set(float(change_7d))
        if mcap is not None:
            market_cap_usd.labels(coin=coin_id, symbol=symbol).set(float(mcap))
        if volume is not None:
            total_volume_usd.labels(coin=coin_id, symbol=symbol).set(float(volume))
        if supply is not None:
            circulating_supply.labels(coin=coin_id, symbol=symbol).set(float(supply))
        if t_supply is not None:
            total_supply.labels(coin=coin_id, symbol=symbol).set(float(t_supply))
        if rank is not None:
            try:
                market_cap_rank.labels(coin=coin_id, symbol=symbol).set(float(rank))
            except Exception:
                pass
        if high is not None:
            high_24h.labels(coin=coin_id, symbol=symbol).set(float(high))
        if low is not None:
            low_24h.labels(coin=coin_id, symbol=symbol).set(float(low))
        if ath is not None:
            ath_usd.labels(coin=coin_id, symbol=symbol).set(float(ath))
        if ath_chg is not None:
            ath_change_percent.labels(coin=coin_id, symbol=symbol).set(float(ath_chg))

        # Derived metrics - be defensive about zeros/None
        try:
            if price is not None and mcap:
                price_to_mcap_ratio.labels(coin=coin_id, symbol=symbol).set(float(price) / float(mcap))
        except Exception:
            pass
        try:
            if volume is not None and mcap:
                volume_to_mcap_ratio.labels(coin=coin_id, symbol=symbol).set(float(volume) / float(mcap))
        except Exception:
            pass

        # last_updated -> convert to epoch if present
        if last_updated:
            ts = _parse_timestamp_iso8601(last_updated)
            if ts is not None:
                last_updated_timestamp.labels(coin=coin_id, symbol=symbol).set(ts)


def main():
    # Start Prometheus HTTP server
    start_http_server(PORT, addr="0.0.0.0")
    logger.info("Custom exporter started on port %s, updating every %s seconds", PORT, UPDATE_INTERVAL)
    # Initial run
    while True:
        data = fetch_coingecko()
        update_metrics(data)
        # sleep UPDATE_INTERVAL seconds
        time.sleep(UPDATE_INTERVAL)


if __name__ == "__main__":
    main()