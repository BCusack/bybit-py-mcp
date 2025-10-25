"""Bybit MCP Server - Model Context Protocol implementation for Bybit trading API.

This server provides access to Bybit's v5 Market API endpoints through the MCP protocol,
enabling AI assistants to fetch real-time market data, instrument information, and
trading statistics.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List

from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.lowlevel import NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    TextContent,
    Tool,
)
from pydantic import AnyUrl

# Import market functions
from .market import (
    get_funding_rate_history,
    get_index_price_kline,
    get_instruments_info,
    get_insurance,
    get_kline,
    get_long_short_ratio,
    get_mark_price_kline,
    get_open_interest,
    get_order_book,
    get_premium_index_price_kline,
    get_recent_trades,
    get_risk_limit,
    get_server_time,
    get_tickers,
)
from .position import (
    get_closed_pnl,
    get_position_info,
    modify_position_margin,
    set_auto_add_margin,
    set_leverage,
    set_trading_stop,
    switch_cross_isolated_margin,
    switch_position_mode,
)

# Import trade functions and TRADING_ENABLED flag
from .trade import (
    TRADING_ENABLED,  # Import the flag
    amend_order,
    batch_amend_order,
    batch_cancel_order,
    batch_place_order,
    cancel_all_orders,
    cancel_order,
    get_account_info,
    get_open_closed_orders,
    get_order_history,
    get_single_coin_balance,
    get_trade_history,
    get_wallet_balance,
    place_order,
    place_trigger_order,
)

# Load environment variables from .env file for local development
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bybit-mcp")

# Create the MCP server instance
server = Server("bybit-mcp")


@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """List all available Bybit market data and trading tools."""
    market_tools = [
        Tool(
            name="get_server_time",
            description="Get the current Bybit server time",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="get_tickers",
            description="Get real-time ticker information including current prices, 24h volume, and price changes for trading symbols. Use this to get current market data for any cryptocurrency pair.",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Product type: 'linear' for USDT perpetuals (most common), 'inverse' for coin-margined futures, 'option' for options, 'spot' for spot trading",
                        "enum": ["linear", "inverse", "option", "spot"],
                        "default": "linear",
                    },
                    "symbol": {
                        "type": "string",
                        "description": "Trading pair symbol. Examples: 'BTCUSDT' (Bitcoin), 'ETHUSDT' (Ethereum), 'SOLUSDT' (Solana). Leave empty to get all symbols.",
                        "examples": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT"]
                    },
                    "baseCoin": {
                        "type": "string",
                        "description": "Base coin for options only. Examples: 'BTC', 'ETH'",
                        "examples": ["BTC", "ETH"]
                    },
                    "expDate": {
                        "type": "string",
                        "description": "Expiry date for options only. Format: DDMMMYY (e.g., '25DEC21', '30JUN22')",
                        "pattern": "^[0-9]{2}[A-Z]{3}[0-9]{2}$",
                        "examples": ["25DEC21", "30JUN22", "31MAR23"]
                    }, },
                "required": []
            },
        ),
        Tool(
            name="get_order_book",
            description="Get order book depth for a trading symbol",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Product type",
                        "enum": ["linear", "inverse", "option", "spot"],
                        "default": "linear",
                    },
                    "symbol": {
                        "type": "string",
                        "description": "Symbol name (e.g., BTCUSDT)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Limit for data size per page (1-500)",
                        "minimum": 1,
                        "maximum": 500,
                        "default": 25,
                    },
                },
                "required": ["symbol"],
            },
        ),
        Tool(
            name="get_recent_trades",
            description="Get recent trades for a symbol",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Product type",
                        "enum": ["linear", "inverse", "option", "spot"],
                        "default": "linear",
                    },
                    "symbol": {
                        "type": "string",
                        "description": "Symbol name (e.g., BTCUSDT)",
                    },
                    "baseCoin": {
                        "type": "string",
                        "description": "Base coin (for option only)",
                    },
                    "optionType": {
                        "type": "string",
                        "description": "Option type (Call or Put, for option only)",
                        "enum": ["Call", "Put"],
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Limit for data size per page (1-1000)",
                        "minimum": 1,
                        "maximum": 1000,
                        "default": 500,
                    }, },
                "required": ["symbol"],
            },
        ),
        Tool(
            name="get_kline",
            description="Get historical candlestick/OHLC data for technical analysis. Returns open, high, low, close prices and volume data. If no time range specified, returns recent data ending at current time.",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Product type: 'linear' for USDT perpetuals (most common), 'inverse' for coin-margined futures, 'option' for options, 'spot' for spot trading",
                        "enum": ["linear", "inverse", "option", "spot"],
                        "default": "linear",
                    },
                    "symbol": {
                        "type": "string",
                        "description": "Trading pair symbol. Examples: 'BTCUSDT', 'ETHUSDT', 'SOLUSDT'",
                        "examples": ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
                    },
                    "interval": {
                        "type": "string",
                        "description": "Time interval for each candlestick. Minutes: '1', '3', '5', '15', '30', '60' (1h), '120' (2h), '240' (4h), '360' (6h), '720' (12h). Periods: 'D' (daily), 'W' (weekly), 'M' (monthly)",
                        "enum": ["1", "3", "5", "15", "30", "60", "120", "240", "360", "720", "D", "M", "W"],
                        "default": "D",
                    },
                    "start": {
                        "type": "integer",
                        "description": "Start time in milliseconds timestamp (OPTIONAL). If not provided, returns recent data. This is the OLDEST time point you want (furthest back in time). Example: 1640995200000 for Jan 1, 2022",
                    },
                    "end": {
                        "type": "integer",
                        "description": "End time in milliseconds timestamp (OPTIONAL). If not provided, defaults to current time. This is the NEWEST time point you want (most recent). Must be after start time.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of candlesticks to return (OPTIONAL). Range: 1-1000. If not specified, API will use a reasonable default based on the interval.",
                        "minimum": 1,
                        "maximum": 1000,
                    }, },
                "required": ["symbol"],
            },
        ),
        Tool(
            name="get_mark_price_kline",
            description="Get mark price candlestick data for derivatives trading. Mark price is used for liquidation calculations and PnL. Available for linear and inverse perpetual contracts only.",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Product type: 'linear' for USDT perpetuals, 'inverse' for coin-margined futures",
                        "enum": ["linear", "inverse"],
                        "default": "linear",
                    },
                    "symbol": {
                        "type": "string",
                        "description": "Trading pair symbol. Examples: 'BTCUSDT', 'ETHUSDT'",
                        "examples": ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
                    },
                    "interval": {
                        "type": "string",
                        "description": "Time interval for each candlestick. Minutes: '1', '3', '5', '15', '30', '60' (1h), '120' (2h), '240' (4h), '360' (6h), '720' (12h). Periods: 'D' (daily), 'W' (weekly), 'M' (monthly)",
                        "enum": ["1", "3", "5", "15", "30", "60", "120", "240", "360", "720", "D", "M", "W"],
                        "default": "D",
                    },
                    "start": {
                        "type": "integer",
                        "description": "Start time in milliseconds timestamp (OPTIONAL). The OLDEST time point (furthest back). If not provided, returns recent data.",
                    },
                    "end": {
                        "type": "integer",
                        "description": "End time in milliseconds timestamp (OPTIONAL). The NEWEST time point (most recent). If not provided, defaults to current time.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of candlesticks to return (OPTIONAL). Range: 1-1000.",
                        "minimum": 1,
                        "maximum": 1000,
                    }, },
                "required": ["symbol"],
            },
        ),
        Tool(
            name="get_index_price_kline",
            description="Get index price candlestick data for derivatives. Index price is the fair value price based on major spot exchanges, used as reference for mark price calculation.",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Product type: 'linear' for USDT perpetuals, 'inverse' for coin-margined futures",
                        "enum": ["linear", "inverse"],
                        "default": "linear",
                    },
                    "symbol": {
                        "type": "string",
                        "description": "Trading pair symbol. Examples: 'BTCUSDT', 'ETHUSDT'",
                        "examples": ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
                    },
                    "interval": {
                        "type": "string",
                        "description": "Time interval for each candlestick. Minutes: '1', '3', '5', '15', '30', '60' (1h), '120' (2h), '240' (4h), '360' (6h), '720' (12h). Periods: 'D' (daily), 'W' (weekly), 'M' (monthly)",
                        "enum": ["1", "3", "5", "15", "30", "60", "120", "240", "360", "720", "D", "M", "W"],
                        "default": "D",
                    },
                    "start": {
                        "type": "integer",
                        "description": "Start time in milliseconds timestamp (OPTIONAL). The OLDEST time point (furthest back). If not provided, returns recent data.",
                    },
                    "end": {
                        "type": "integer",
                        "description": "End time in milliseconds timestamp (OPTIONAL). The NEWEST time point (most recent). If not provided, defaults to current time.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of candlesticks to return (OPTIONAL). Range: 1-1000.",
                        "minimum": 1,
                        "maximum": 1000,
                    }, },
                "required": ["symbol"],
            },
        ),
        Tool(
            name="get_premium_index_price_kline",
            description="Get premium index price candlestick data for linear perpetuals. Premium index shows the funding rate basis and is used to calculate funding payments.",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Product type: only 'linear' (USDT perpetuals) supported",
                        "enum": ["linear"],
                        "default": "linear",
                    },
                    "symbol": {
                        "type": "string",
                        "description": "Trading pair symbol. Examples: 'BTCUSDT', 'ETHUSDT'",
                        "examples": ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
                    },
                    "interval": {
                        "type": "string",
                        "description": "Time interval for each candlestick. Minutes: '1', '3', '5', '15', '30', '60' (1h), '120' (2h), '240' (4h), '360' (6h), '720' (12h). Periods: 'D' (daily), 'W' (weekly), 'M' (monthly)",
                        "enum": ["1", "3", "5", "15", "30", "60", "120", "240", "360", "720", "D", "M", "W"],
                        "default": "D",
                    },
                    "start": {
                        "type": "integer",
                        "description": "Start time in milliseconds timestamp (OPTIONAL). The OLDEST time point (furthest back). If not provided, returns recent data.",
                    },
                    "end": {
                        "type": "integer",
                        "description": "End time in milliseconds timestamp (OPTIONAL). The NEWEST time point (most recent). If not provided, defaults to current time.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of candlesticks to return (OPTIONAL). Range: 1-1000.",
                        "minimum": 1,
                        "maximum": 1000,
                    },
                },
                "required": ["symbol"],
            },
        ),
        Tool(
            name="get_instruments_info",
            description="Get trading instruments information",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Product type",
                        "enum": ["linear", "inverse", "option", "spot"],
                        "default": "linear",
                    },
                    "symbol": {
                        "type": "string",
                        "description": "Symbol name (e.g., BTCUSDT)",
                    },
                    "baseCoin": {
                        "type": "string",
                        "description": "Base coin",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Limit for data size per page (1-1000)",
                        "minimum": 1,
                        "maximum": 1000,
                        "default": 500,
                    },
                    "cursor": {
                        "type": "string",
                        "description": "Cursor for pagination",
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="get_funding_rate_history",
            description="Get funding rate history",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Product type",
                        "enum": ["linear", "inverse"],
                        "default": "linear",
                    },
                    "symbol": {
                        "type": "string",
                        "description": "Symbol name (e.g., BTCUSDT)",
                    },
                    "startTime": {
                        "type": "integer",
                        "description": "Start timestamp (ms)",
                    },
                    "endTime": {
                        "type": "integer",
                        "description": "End timestamp (ms)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Limit for data size per page (1-200)",
                        "minimum": 1,
                        "maximum": 200,
                        "default": 200,
                    },
                },
                "required": ["symbol"],
            },
        ),
        Tool(
            name="get_open_interest",
            description="Get open interest data",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Product type",
                        "enum": ["linear", "inverse"],
                        "default": "linear",
                    },
                    "symbol": {
                        "type": "string",
                        "description": "Symbol name (e.g., BTCUSDT)",
                    },
                    "interval": {
                        "type": "string",
                        "description": "Interval time",
                        "enum": ["5min", "15min", "30min", "1h", "4h", "1d"],
                        "default": "5min",
                    },
                    "startTime": {
                        "type": "integer",
                        "description": "Start timestamp (ms)",
                    },
                    "endTime": {
                        "type": "integer",
                        "description": "End timestamp (ms)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Limit for data size per page (1-200)",
                        "minimum": 1,
                        "maximum": 200,
                        "default": 50,
                    },
                    "cursor": {
                        "type": "string",
                        "description": "Cursor for pagination"
                    }
                },
                "required": ["symbol"],
            },
        ),
        Tool(
            name="get_insurance",
            description="Get insurance fund data",
            inputSchema={
                "type": "object",
                "properties": {
                    "coin": {
                        "type": "string",
                        "description": "Coin name (e.g., BTC, ETH, USDT)",
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="get_risk_limit",
            description="Get risk limit information",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Product type",
                        "enum": ["linear", "inverse"],
                        "default": "linear",
                    },
                    "symbol": {
                        "type": "string",
                        "description": "Symbol name (e.g., BTCUSDT)",
                    },
                },
            },
        ),
        Tool(
            name="get_long_short_ratio",
            description="Get long/short ratio data",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Product type",
                        "enum": ["linear", "inverse"],
                        "default": "linear",
                    },
                    "symbol": {
                        "type": "string",
                        "description": "Symbol name (e.g., BTCUSDT)",
                    },
                    "interval": {
                        "type": "string",
                        "description": "Data recording interval",
                        "enum": ["5min", "15min", "30min", "1h", "4h", "1d"],
                        "default": "5min",
                    },
                    "startTime": {
                        "type": "integer",
                        "description": "Start timestamp (ms)",
                    },
                    "endTime": {
                        "type": "integer",
                        "description": "End timestamp (ms)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Limit for data size per page (1-500)",
                        "minimum": 1,
                        "maximum": 500,
                        "default": 50,
                    },
                },
                "required": ["symbol"],
            },
        ),
    ]

    active_trade_tools = []
    if TRADING_ENABLED:
        active_trade_tools.extend(
            [Tool(
                name="place_order",
                description="Place a new trading order on Bybit. ⚠️ EXECUTES REAL TRADES WITH REAL MONEY when trading is enabled. This is the primary tool for buying and selling cryptocurrencies. Always confirm symbol, side, quantity, and price before executing. Market orders execute immediately at current price, Limit orders wait for your specified price.",
                inputSchema={
                    "type": "object",
                    "properties": {
                            "category": {
                                "type": "string",
                                "description": "Product category: 'linear' for USDT perpetuals (most common), 'spot' for spot trading, 'option' for options, 'inverse' for coin-margined futures",
                                "enum": ["linear", "spot", "option", "inverse"],
                                "default": "linear"
                            },
                        "symbol": {
                                "type": "string",
                                "description": "Trading pair symbol. Examples: 'BTCUSDT', 'ETHUSDT', 'SOLUSDT'",
                                "examples": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT"]
                            },
                        "side": {
                                "type": "string",
                                "description": "Order side: 'Buy' to purchase, 'Sell' to sell",
                                "enum": ["Buy", "Sell"]
                            },
                        "orderType": {
                                "type": "string",
                                "description": "Order type: 'Market' executes immediately at current price, 'Limit' waits for specific price",
                                "enum": ["Market", "Limit"]
                            },
                        "qty": {
                                "type": "string",
                                "description": "Order quantity. For spot: coin amount (e.g., '0.001' BTC). For derivatives: contract size (e.g., '100' USDT)",
                                "examples": ["0.001", "100", "1.5", "0.1"]
                            },
                        "price": {
                                "type": "string",
                                "description": "Order price. Required for Limit orders, ignored for Market orders. Examples: '50000', '3000.5'",
                                "examples": ["50000", "3000.5", "0.001", "100.25"]
                            },
                        "isLeverage": {
                                "type": "integer",
                                "description": "Use leverage for spot margin trading: 0 = normal spot, 1 = use leverage (spot margin only)"
                            },
                        "orderLinkId": {
                                "type": "string",
                                "description": "Custom order ID for tracking. Must be unique. Use for order management and identification",
                                "examples": ["myorder123", "trade_2024_001", "bot_order_456"]
                            }
                    },
                    "required": ["category", "symbol", "side", "orderType", "qty"]
                }
            ),                Tool(
                name="amend_order",
                description="Modify an existing pending order's price or quantity. ⚠️ Only works on orders that haven't been filled yet. Use this to adjust your order without canceling and re-placing it, which saves on fees and maintains your position in the order queue. You must provide either orderId or orderLinkId to identify the order.",
                inputSchema={
                    "type": "object",
                    "properties": {
                            "category": {
                                "type": "string",
                                "description": "Product category where the order exists",
                                "enum": ["linear", "spot", "option", "inverse"]
                            },
                        "symbol": {
                                "type": "string",
                                "description": "Trading pair symbol of the order to amend. Examples: 'BTCUSDT', 'ETHUSDT'",
                                "examples": ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
                                },
                        "orderId": {
                                "type": "string",
                                "description": "Bybit's order ID. Either orderId or orderLinkId must be provided. Get this from order placement response or order history",
                                "examples": ["1234567890123456", "9876543210987654"]
                                },
                        "orderLinkId": {
                                "type": "string",
                                "description": "Your custom order ID. Either orderId or orderLinkId must be provided. This is what you set when placing the order",
                                "examples": ["myorder123", "trade_2024_001", "bot_order_456"]
                                },
                        "qty": {
                                "type": "string",
                                "description": "New order quantity. Leave empty if only changing price. Examples: '0.002', '150'",
                                "examples": ["0.002", "150", "1.5", "0.5"]
                                },
                        "price": {
                                "type": "string",
                                "description": "New order price. Leave empty if only changing quantity. Examples: '51000', '3100.5'",
                                "examples": ["51000", "3100.5", "0.002", "105.75"]
                                }
                    },
                    "required": ["category", "symbol"]
                }
            ),                Tool(
                name="cancel_order",
                description="Cancel a single pending order immediately. ⚠️ Only works on orders that haven't been filled yet. Once an order is filled/executed, it cannot be cancelled. Use this to remove unwanted pending orders from the order book. You must provide either orderId or orderLinkId to identify the specific order to cancel.",
                inputSchema={
                    "type": "object",
                    "properties": {
                            "category": {
                                "type": "string",
                                "description": "Product category where the order exists",
                                "enum": ["linear", "spot", "option", "inverse"]
                            },
                        "symbol": {
                                "type": "string",
                                "description": "Trading pair symbol of the order to cancel. Examples: 'BTCUSDT', 'ETHUSDT'",
                                "examples": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT"]
                            },
                        "orderId": {
                                "type": "string",
                                "description": "Bybit's order ID. Either orderId or orderLinkId must be provided. Get this from order placement response or order history",
                                "examples": ["1234567890123456", "9876543210987654"]
                            },
                        "orderLinkId": {
                                "type": "string",
                                "description": "Your custom order ID. Either orderId or orderLinkId must be provided. This is what you set when placing the order",
                                "examples": ["myorder123", "trade_2024_001", "bot_order_456"]
                            }
                    },
                    "required": ["category", "symbol"]
                }
            ),
                Tool(
                    name="cancel_all_orders",
                    description="Cancel all pending orders for a category or specific symbol. Use with caution as this cancels ALL open orders matching the criteria.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "category": {
                                "type": "string",
                                "description": "Product category to cancel orders in",
                                "enum": ["linear", "spot", "option", "inverse"]
                            },
                            "symbol": {
                                "type": "string",
                                "description": "Specific trading pair to cancel orders for. Leave empty to cancel ALL orders in the category",
                                "examples": ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
                            },
                            "baseCoin": {
                                "type": "string",
                                "description": "Base coin filter for options and derivatives. Examples: 'BTC', 'ETH'",
                                "examples": ["BTC", "ETH", "SOL"]
                            },
                            "settleCoin": {
                                "type": "string",
                                "description": "Settlement coin filter. Examples: 'USDT', 'BTC', 'ETH'",
                                "examples": ["USDT", "BTC", "ETH"]
                            },
                            "orderFilter": {
                                "type": "string",
                                "description": "Order type filter: 'Order' for normal orders, 'StopOrder' for conditional orders",
                                "enum": ["Order", "StopOrder"]
                            }
                        },
                        "required": ["category"]
                    }
            ),                Tool(
                    name="batch_place_order",
                    description="Place multiple orders in a single request. More efficient than placing orders individually. All orders must be in the same category.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "category": {
                                "type": "string",
                                "description": "Product category for all orders in the batch",
                                "enum": ["linear", "spot", "option", "inverse"]
                            },
                            "request": {
                                "type": "array",
                                "description": "Array of order objects to place. Maximum 20 orders per batch",
                                "maxItems": 20,
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "symbol": {
                                            "type": "string",
                                            "description": "Trading pair symbol",
                                            "examples": ["BTCUSDT", "ETHUSDT"]
                                        },
                                        "side": {
                                            "type": "string",
                                            "description": "Order side",
                                            "enum": ["Buy", "Sell"]
                                        },
                                        "orderType": {
                                            "type": "string",
                                            "description": "Order type",
                                            "enum": ["Market", "Limit"]
                                        },
                                        "qty": {
                                            "type": "string",
                                            "description": "Order quantity",
                                            "examples": ["0.001", "100"]
                                        },
                                        "price": {
                                            "type": "string",
                                            "description": "Order price (required for Limit orders)",
                                            "examples": ["50000", "3000.5"]
                                        },
                                        "orderLinkId": {
                                            "type": "string",
                                            "description": "Custom order ID for tracking",
                                            "examples": ["batch_order_1", "trade_001"]
                                        }
                                    },
                                    "required": ["symbol", "side", "orderType", "qty"]
                                }
                            }
                        },
                        "required": ["category", "request"]
                    }
            ),                Tool(
                    name="batch_amend_order",
                    description="Modify multiple existing orders in a single request. More efficient than amending orders individually. All orders must be in the same category.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "category": {
                                "type": "string",
                                "description": "Product category for all orders in the batch",
                                "enum": ["linear", "spot", "option", "inverse"]
                            },
                            "request": {
                                "type": "array",
                                "description": "Array of order amendment objects. Maximum 20 orders per batch",
                                "maxItems": 20,
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "symbol": {
                                            "type": "string",
                                            "description": "Trading pair symbol",
                                            "examples": ["BTCUSDT", "ETHUSDT"]
                                        },
                                        "orderId": {
                                            "type": "string",
                                            "description": "Bybit's order ID (use either orderId or orderLinkId)",
                                            "examples": ["1234567890123456"]
                                        },
                                        "orderLinkId": {
                                            "type": "string",
                                            "description": "Your custom order ID (use either orderId or orderLinkId)",
                                            "examples": ["myorder123", "trade_001"]
                                        },
                                        "qty": {
                                            "type": "string",
                                            "description": "New order quantity (optional)",
                                            "examples": ["0.002", "150"]
                                        },
                                        "price": {
                                            "type": "string",
                                            "description": "New order price (optional)",
                                            "examples": ["51000", "3100.5"]
                                        }
                                    },
                                    "required": ["symbol"]
                                }
                            }
                        },
                        "required": ["category", "request"]
                    }
            ),                Tool(
                    name="batch_cancel_order",
                    description="Cancel multiple existing orders in a single request. More efficient than canceling orders individually. All orders must be in the same category.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "category": {
                                "type": "string",
                                "description": "Product category for all orders in the batch",
                                "enum": ["linear", "spot", "option", "inverse"]
                            },
                            "request": {
                                "type": "array",
                                "description": "Array of order cancellation objects. Maximum 20 orders per batch",
                                "maxItems": 20,
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "symbol": {
                                            "type": "string",
                                            "description": "Trading pair symbol for the order to cancel",
                                            "examples": ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
                                        },
                                        "orderId": {
                                            "type": "string",
                                            "description": "Bybit's order ID (use either orderId or orderLinkId)",
                                            "examples": ["1234567890123456", "9876543210987654"]
                                        },
                                        "orderLinkId": {
                                            "type": "string",
                                            "description": "Your custom order ID (use either orderId or orderLinkId)",
                                            "examples": ["myorder123", "trade_2024_001", "bot_order_456"]
                                        }
                                    },
                                    "required": ["symbol"]
                                }
                            }
                        },
                        "required": ["category", "request"]
                    }
            ),
                Tool(
                    name="place_trigger_order",
                    description="Place a conditional/trigger order that executes only when market price reaches your trigger condition. ⚠️ EXECUTES REAL TRADES WITH REAL MONEY when triggered. These orders wait for a specific price level before becoming active. The order doesn't occupy margin until triggered. Perfect for stop-loss, take-profit, and breakout strategies.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "category": {
                                "type": "string",
                                "description": "Product category: 'linear' for USDT perpetuals, 'spot' for spot trading, 'inverse' for coin-margined futures. Options not supported for trigger orders",
                                "enum": ["linear", "spot", "inverse"]
                            },
                            "symbol": {
                                "type": "string",
                                "description": "Trading pair symbol. Examples: 'BTCUSDT', 'ETHUSDT', 'SOLUSDT'",
                                "examples": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT"]
                            },
                            "side": {
                                "type": "string",
                                "description": "Order side: 'Buy' to purchase when triggered, 'Sell' to sell when triggered",
                                "enum": ["Buy", "Sell"]
                            },
                            "orderType": {
                                "type": "string",
                                "description": "Order type after trigger: 'Market' executes at market price when triggered, 'Limit' waits for your limit price after trigger",
                                "enum": ["Market", "Limit"]
                            },
                            "qty": {
                                "type": "string",
                                "description": "Order quantity when triggered. For spot: coin amount (e.g., '0.001' BTC). For derivatives: contract size (e.g., '100' USDT)",
                                "examples": ["0.001", "100", "1.5", "0.1"]
                            },
                            "triggerPrice": {
                                "type": "string",
                                "description": "Price that triggers the conditional order. When market hits this price, your order becomes active. Examples: '52000', '2900'",
                                "examples": ["52000", "2900", "0.002", "105.50"]
                            },
                            "triggerDirection": {
                                "type": "integer",
                                "description": "Trigger direction: 1 = triggered when price RISES to triggerPrice (for buy-stop/sell-limit breakouts), 2 = triggered when price FALLS to triggerPrice (for stop-loss/buy-limit dips)"
                            },
                            "triggerBy": {
                                "type": "string",
                                "description": "Price type for trigger: 'LastPrice' = last traded price (default), 'MarkPrice' = mark price (recommended for derivatives), 'IndexPrice' = index price",
                                "enum": ["LastPrice", "MarkPrice", "IndexPrice"],
                                "default": "LastPrice"
                            },
                            "price": {
                                "type": "string",
                                "description": "Order price after trigger (for Limit orders only). Leave empty for Market orders. Examples: '52500', '2950'",
                                "examples": ["52500", "2950", "0.0021", "106.25"]
                            },
                            "orderFilter": {
                                "type": "string",
                                "description": "Order filter for spot: 'Order' = normal conditional order, 'StopOrder' = stop order (assets not reserved until trigger), 'tpslOrder' = TP/SL order (assets reserved)",
                                "enum": ["Order", "StopOrder", "tpslOrder"],
                                "default": "StopOrder"
                            },
                            "timeInForce": {
                                "type": "string",
                                "description": "Time in force after trigger: 'GTC' = Good Till Cancelled, 'IOC' = Immediate or Cancel, 'FOK' = Fill or Kill, 'PostOnly' = Post Only",
                                "enum": ["GTC", "IOC", "FOK", "PostOnly"],
                                "default": "GTC"
                            },
                            "reduceOnly": {
                                "type": "boolean",
                                "description": "Reduce only flag: true = can only reduce position size (for closing positions), false = can increase position. Use true for stop-loss orders"
                            },
                            "closeOnTrigger": {
                                "type": "boolean",
                                "description": "Close on trigger: true = ensures order executes even with insufficient margin by canceling other orders if needed. Useful for guaranteed stop-losses"
                            },
                            "positionIdx": {
                                "type": "integer",
                                "description": "Position index for hedge mode: 0 = one-way mode, 1 = hedge-mode Buy side, 2 = hedge-mode Sell side"
                            },
                            "orderLinkId": {
                                "type": "string",
                                "description": "Custom order ID for tracking. Must be unique. Use for order management and identification",
                                "examples": ["trigger_stop_123", "breakout_order_001", "sl_order_456"]
                            }
                        },
                        "required": ["category", "symbol", "side", "orderType", "qty", "triggerPrice", "triggerDirection"]
                    }
            ),
            ]
        )    # These are read-only and can always be listed
    trade_info_tools = [
        Tool(
            name="get_open_closed_orders",
            description="Get both open (pending) and recently closed orders. Essential for monitoring order status and trading activity. Use this to check if orders are filled, cancelled, or still pending.",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Product category to query orders for",
                        "enum": ["linear", "spot", "option", "inverse"]
                    },
                    "symbol": {
                        "type": "string",
                        "description": "Specific trading pair to get orders for. Leave empty to get all orders in category",
                        "examples": ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
                    },
                    "baseCoin": {
                        "type": "string",
                        "description": "Base coin filter for derivatives and options",
                        "examples": ["BTC", "ETH", "SOL"]
                    },
                    "orderId": {
                        "type": "string",
                        "description": "Specific order ID to query",
                        "examples": ["1234567890123456"]
                    },
                    "orderLinkId": {
                        "type": "string",
                        "description": "Specific custom order ID to query",
                        "examples": ["myorder123", "trade_2024_001"]
                    },
                    "openOnly": {
                        "type": "integer",
                        "description": "Filter by open orders only: 0 = all orders, 1 = open orders only, 2 = closed orders only"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of records to return (1-50)",
                        "minimum": 1,
                        "maximum": 50,
                        "default": 20
                    },
                    "cursor": {
                        "type": "string",
                        "description": "Pagination cursor for next page of results"
                    }
                },
                "required": ["category"]
            }
        ),
        Tool(
            name="get_order_history",
            description="Get comprehensive order history with detailed information about past orders including execution details, timestamps, and status changes. Useful for trade analysis and record keeping.",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Product category to query order history for",
                        "enum": ["linear", "spot", "option", "inverse"]
                    },
                    "symbol": {
                        "type": "string",
                        "description": "Specific trading pair to get order history for. Leave empty to get all orders in category",
                        "examples": ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
                    },
                    "baseCoin": {
                        "type": "string",
                        "description": "Base coin filter for derivatives and options",
                        "examples": ["BTC", "ETH", "SOL"]
                    },
                    "orderId": {
                        "type": "string",
                        "description": "Specific order ID to query",
                        "examples": ["1234567890123456"]
                    },
                    "orderLinkId": {
                        "type": "string",
                        "description": "Specific custom order ID to query",
                        "examples": ["myorder123", "trade_2024_001"]
                    },
                    "orderStatus": {
                        "type": "string",
                        "description": "Filter by order status",
                        "enum": ["New", "PartiallyFilled", "Filled", "Cancelled", "Rejected", "PartiallyFilledCanceled", "Deactivated"]
                    },
                    "orderFilter": {
                        "type": "string",
                        "description": "Order type filter",
                        "enum": ["Order", "StopOrder", "tpslOrder", "OcoOrder", "BidirectionalTpslOrder"]
                    },
                    "startTime": {
                        "type": "integer",
                        "description": "Start timestamp in milliseconds for history query",
                        "examples": [1640995200000, 1672531200000]
                    },
                    "endTime": {
                        "type": "integer",
                        "description": "End timestamp in milliseconds for history query",
                        "examples": [1640995200000, 1672531200000]
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of records to return (1-50)",
                        "minimum": 1,
                        "maximum": 50,
                        "default": 20
                    },
                    "cursor": {
                        "type": "string",
                        "description": "Pagination cursor for next page of results"
                    }
                },
                "required": ["category"]
            }
        ),
        Tool(
            name="get_trade_history",
            description="Get detailed execution history showing actual trades (fills) with execution prices, quantities, fees, and timestamps. Essential for performance analysis and tax reporting.",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Product category to query trade executions for",
                        "enum": ["linear", "spot", "option", "inverse"]
                    },
                    "symbol": {
                        "type": "string",
                        "description": "Specific trading pair to get trade history for. Leave empty to get all trades in category",
                        "examples": ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
                    },
                    "baseCoin": {
                        "type": "string",
                        "description": "Base coin filter for derivatives and options",
                        "examples": ["BTC", "ETH", "SOL"]
                    },
                    "orderId": {
                        "type": "string",
                        "description": "Get trades for specific order ID",
                        "examples": ["1234567890123456"]
                    },
                    "orderLinkId": {
                        "type": "string",
                        "description": "Get trades for specific custom order ID",
                        "examples": ["myorder123", "trade_2024_001"]
                    },
                    "execType": {
                        "type": "string",
                        "description": "Execution type filter",
                        "enum": ["Trade", "AdlTrade", "Funding", "BustTrade", "Settle"]
                    },
                    "startTime": {
                        "type": "integer",
                        "description": "Start timestamp in milliseconds for trade history query",
                        "examples": [1640995200000, 1672531200000]
                    },
                    "endTime": {
                        "type": "integer",
                        "description": "End timestamp in milliseconds for trade history query",
                        "examples": [1640995200000, 1672531200000]
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of records to return (1-100)",
                        "minimum": 1,
                        "maximum": 100,
                        "default": 50
                    },
                    "cursor": {
                        "type": "string",
                        "description": "Pagination cursor for next page of results"
                    }
                },
                "required": ["category"]
            }
        ),
        Tool(
            name="get_wallet_balance",
            description="Get detailed wallet balance information including available balance, locked balance, and total equity across different account types. Essential for portfolio monitoring and risk management.",
            inputSchema={
                "type": "object",
                "properties": {
                    "accountType": {
                        "type": "string",
                        "description": "Account type to query balance for. UNIFIED is most common for modern trading",
                        "enum": ["UNIFIED", "CONTRACT", "SPOT", "INVESTMENT", "OPTION", "FUND", "COPYTRADING"],
                        "examples": ["UNIFIED", "SPOT", "CONTRACT"]
                    },
                    "coin": {
                        "type": "string",
                        "description": "Specific coin to get balance for. Leave empty to get all coin balances",
                        "examples": ["BTC", "ETH", "USDT", "SOL", "ADA"]
                    }
                },
                "required": ["accountType"]
            }
        ),
        Tool(
            name="get_single_coin_balance",
            description="Get balance information for a specific coin with additional details like transferable amounts and account relationships. More detailed than wallet balance for single coin queries.",
            inputSchema={
                "type": "object",
                "properties": {
                    "accountType": {
                        "type": "string",
                        "description": "Account type to query coin balance for",
                        "enum": ["UNIFIED", "CONTRACT", "SPOT"],
                        "examples": ["UNIFIED", "SPOT", "CONTRACT"]
                    },
                    "coin": {
                        "type": "string",
                        "description": "Specific coin to get detailed balance for",
                        "examples": ["BTC", "ETH", "USDT", "SOL", "ADA"]
                    },
                    "memberId": {
                        "type": "string",
                        "description": "Member ID for institutional accounts (optional)"
                    },
                    "toAccountType": {
                        "type": "string",
                        "description": "Target account type for transfer queries (optional)",
                        "enum": ["UNIFIED", "CONTRACT", "SPOT"]
                    },
                    "toMemberId": {
                        "type": "string",
                        "description": "Target member ID for institutional transfers (optional)"
                    },
                    "withBonus": {
                        "type": "integer",
                        "description": "Include bonus balance in results: 0 = exclude bonus, 1 = include bonus",
                        "enum": ["0", "1"],
                        "default": 0
                    }
                },
                "required": ["accountType", "coin"]
            }
        ),
        Tool(
            name="get_account_info",
            description="Get comprehensive account information including margin ratios, account status, upgrade status, and overall account health metrics. Essential for risk monitoring.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    ]  # Position Management Tools (read-only position info is always available)
    position_tools = [
        Tool(
            name="get_position_info",
            description="Get detailed position information including size, value, PnL, and margin for your trading positions. Essential for portfolio monitoring and risk management.",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Product category to query positions for",
                        "enum": ["linear", "spot", "option", "inverse"]
                    },
                    "symbol": {
                        "type": "string",
                        "description": "Specific trading pair to get position for. Leave empty to get all positions in category",
                        "examples": ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
                    },
                    "baseCoin": {
                        "type": "string",
                        "description": "Base coin filter for derivatives and options",
                        "examples": ["BTC", "ETH", "SOL"]
                    },
                    "settleCoin": {
                        "type": "string",
                        "description": "Settlement coin filter",
                        "examples": ["USDT", "BTC", "ETH"]
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of records to return (1-200)",
                        "minimum": 1,
                        "maximum": 200,
                        "default": 20
                    },
                    "cursor": {
                        "type": "string",
                        "description": "Pagination cursor for next page of results"
                    }
                },
                "required": ["category"]
            }
        ),
        Tool(
            name="get_closed_pnl",
            description="Get historical profit and loss data for closed positions. Useful for performance analysis and tax reporting.",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Product category to query closed PnL for",
                        "enum": ["linear", "spot", "option", "inverse"]
                    },
                    "symbol": {
                        "type": "string",
                        "description": "Specific trading pair to get PnL for. Leave empty to get all closed PnL in category",
                        "examples": ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
                    },
                    "startTime": {
                        "type": "integer",
                        "description": "Start timestamp in milliseconds for PnL query",
                        "examples": [1640995200000, 1672531200000]
                    },
                    "endTime": {
                        "type": "integer",
                        "description": "End timestamp in milliseconds for PnL query",
                        "examples": [1640995200000, 1672531200000]
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of records to return (1-100)",
                        "minimum": 1,
                        "maximum": 100,
                        "default": 20
                    },
                    "cursor": {
                        "type": "string",
                        "description": "Pagination cursor for next page of results"
                    }
                },
                "required": ["category"]
            }
        )
    ]    # Position management tools that require trading to be enabled
    active_position_tools = []
    if TRADING_ENABLED:
        active_position_tools.extend(
            [
                Tool(
                    name="set_leverage",
                    description="Set leverage for a trading position. Higher leverage amplifies both profits and losses. Use with caution as it increases risk significantly.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "category": {
                                "type": "string",
                                "description": "Product category to set leverage for",
                                "enum": ["linear", "inverse", "option"]
                            },
                            "symbol": {
                                "type": "string",
                                "description": "Trading pair symbol to set leverage for",
                                "examples": ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
                            },
                            "buyLeverage": {
                                "type": "string",
                                "description": "Leverage for long positions. Range depends on symbol (e.g., 1-100x)",
                                "examples": ["1", "5", "10", "25", "50", "100"]
                            },
                            "sellLeverage": {
                                "type": "string",
                                "description": "Leverage for short positions. Range depends on symbol (e.g., 1-100x)",
                                "examples": ["1", "5", "10", "25", "50", "100"]
                            }
                        },
                        "required": ["category", "symbol", "buyLeverage", "sellLeverage"]
                    }
                ),
                Tool(
                    name="switch_cross_isolated_margin",
                    description="Switch between cross margin (uses entire account balance as collateral) and isolated margin (uses only position margin). Cross margin has lower liquidation risk but affects entire account.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "category": {
                                "type": "string",
                                "description": "Product category to change margin mode for",
                                "enum": ["linear", "inverse"]
                            },
                            "symbol": {
                                "type": "string",
                                "description": "Trading pair symbol to change margin mode for",
                                "examples": ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
                            },
                            "tradeMode": {
                                "type": "integer",
                                "description": "Margin mode: 0 = cross margin (shared account balance), 1 = isolated margin (separate position margin)",
                                "enum": ["0", "1"]
                            },
                            "buyLeverage": {
                                "type": "string",
                                "description": "Leverage for long positions after mode switch",
                                "examples": ["1", "5", "10", "25", "50"]
                            },
                            "sellLeverage": {
                                "type": "string",
                                "description": "Leverage for short positions after mode switch",
                                "examples": ["1", "5", "10", "25", "50"]
                            }
                        },
                        "required": ["category", "symbol", "tradeMode", "buyLeverage", "sellLeverage"]
                    }
                ),
                Tool(
                    name="switch_position_mode",
                    description="Switch between one-way mode (net position) and hedge mode (separate long/short positions). Hedge mode allows simultaneous long and short positions on the same symbol.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "category": {
                                "type": "string",
                                "description": "Product category to change position mode for",
                                "enum": ["linear", "inverse", "option"]
                            },
                            "symbol": {
                                "type": "string",
                                "description": "Trading pair symbol (optional for some categories, required for linear/inverse)",
                                "examples": ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
                            },
                            "coin": {
                                "type": "string",
                                "description": "Base coin for options category",
                                "examples": ["BTC", "ETH", "SOL"]
                            },
                            "mode": {
                                "type": "integer",
                                "description": "Position mode: 0 = One-Way Mode (net position), 3 = Hedge Mode (separate buy/sell positions)",
                                "enum": ["0", "3"]
                            }
                        },
                        "required": ["category", "mode"]
                    }
                ),
                Tool(
                    name="set_trading_stop",
                    description="Set take profit and stop loss orders for an existing position. These orders automatically close your position at specified profit or loss levels to manage risk.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "category": {
                                "type": "string",
                                "description": "Product category for the position",
                                "enum": ["linear", "inverse", "option"]
                            },
                            "symbol": {
                                "type": "string",
                                "description": "Trading pair symbol for the position",
                                "examples": ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
                            },
                            "positionIdx": {
                                "type": "integer",
                                "description": "Position index: 0 = one-way mode, 1 = hedge-mode Buy side, 2 = hedge-mode Sell side"
                            },
                            "takeProfit": {
                                "type": "string",
                                "description": "Take profit price to automatically close position at profit target",
                                "examples": ["52000", "3200", "150"]
                            },
                            "stopLoss": {
                                "type": "string",
                                "description": "Stop loss price to automatically close position to limit losses",
                                "examples": ["48000", "2800", "90"]
                            },
                            "tpTriggerBy": {
                                "type": "string",
                                "description": "Take profit trigger price type",
                                "enum": ["LastPrice", "IndexPrice", "MarkPrice"]
                            },
                            "slTriggerBy": {
                                "type": "string",
                                "description": "Stop loss trigger price type",
                                "enum": ["LastPrice", "IndexPrice", "MarkPrice"]
                            },
                            "tpslMode": {
                                "type": "string",
                                "description": "TP/SL mode for partial position closure",
                                "enum": ["Full", "Partial"]
                            },
                            "tpOrderType": {
                                "type": "string",
                                "description": "Take profit order type when triggered",
                                "enum": ["Market", "Limit"]
                            },
                            "slOrderType": {
                                "type": "string",
                                "description": "Stop loss order type when triggered",
                                "enum": ["Market", "Limit"]
                            },
                            "tpSize": {
                                "type": "string",
                                "description": "Take profit size for partial closure",
                                "examples": ["0.5", "50", "100"]
                            },
                            "slSize": {
                                "type": "string",
                                "description": "Stop loss size for partial closure",
                                "examples": ["0.5", "50", "100"]
                            }
                        },
                        "required": ["category", "symbol", "positionIdx"]
                    }
                ),
                Tool(
                    name="set_auto_add_margin",
                    description="Enable or disable automatic margin addition for isolated margin positions. When enabled, margin is automatically added to prevent liquidation.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "category": {
                                "type": "string",
                                "description": "Product category for the position",
                                "enum": ["linear", "inverse"]
                            },
                            "symbol": {
                                "type": "string",
                                "description": "Trading pair symbol for the position",
                                "examples": ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
                            },
                            "autoAddMargin": {
                                "type": "integer",
                                "description": "Auto add margin setting: 0 = disabled, 1 = enabled",
                                "enum": ["0", "1"]
                            },
                            "positionIdx": {
                                "type": "integer",
                                "description": "Position index: 0 = one-way mode, 1 = hedge-mode Buy side, 2 = hedge-mode Sell side"
                            }
                        },
                        "required": ["category", "symbol", "autoAddMargin"]
                    }
                ),
                Tool(
                    name="modify_position_margin",
                    description="Manually add or reduce margin for an isolated margin position. Use positive values to add margin (reduce liquidation risk) or negative values to reduce margin.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "category": {
                                "type": "string",
                                "description": "Product category for the position",
                                "enum": ["linear", "inverse"]
                            },
                            "symbol": {
                                "type": "string",
                                "description": "Trading pair symbol for the position",
                                "examples": ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
                            },
                            "margin": {
                                "type": "string",
                                "description": "Margin amount to add (positive) or reduce (negative). In quote currency for linear, base currency for inverse",
                                "examples": ["100", "-50", "25.5", "-10.25"]
                            },
                            "positionIdx": {
                                "type": "integer",
                                "description": "Position index: 0 = one-way mode, 1 = hedge-mode Buy side, 2 = hedge-mode Sell side"
                            }
                        },
                        "required": ["category", "symbol", "margin"]
                    }
                )
            ]
        )

    # Combine all tools for final listing
    return market_tools + active_trade_tools + trade_info_tools + position_tools + active_position_tools


@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls for Bybit market data and trading endpoints."""
    try:
        # Market Data Tools
        if name == "get_server_time":
            result = get_server_time()
            return [
                TextContent(
                    type="text",
                    text=f"Bybit Server Time: {result.get('timeSecond', 'Unknown')}\nFull Response: {json.dumps(result, indent=2)}",
                )
            ]
        elif name == "get_tickers":
            result = get_tickers(**arguments)
            return [TextContent(type="text", text=f"Ticker data for {result.category}:\n{json.dumps(result.model_dump(), indent=2)}")]
        elif name == "get_order_book":
            result = get_order_book(**arguments)
            return [TextContent(type="text", text=f"Order book for {result.s}:\n{json.dumps(result.model_dump(), indent=2)}")]
        elif name == "get_recent_trades":
            result = get_recent_trades(**arguments)
            return [TextContent(type="text", text=f"Recent trades for {result.category}:\n{json.dumps(result.model_dump(), indent=2)}")]
        elif name == "get_kline":
            result = get_kline(**arguments)
            return [
                TextContent(
                    type="text", text=f"Kline data for {result.symbol} ({result.category}):\n{json.dumps(result.model_dump(), indent=2)}"
                )
            ]
        elif name == "get_mark_price_kline":
            result = get_mark_price_kline(**arguments)
            return [
                TextContent(
                    type="text",
                    text=f"Mark price kline data for {result.symbol} ({result.category}):\n{json.dumps(result.model_dump(), indent=2)}",
                )
            ]
        elif name == "get_index_price_kline":
            result = get_index_price_kline(**arguments)
            return [
                TextContent(
                    type="text",
                    text=f"Index price kline data for {result.symbol} ({result.category}):\n{json.dumps(result.model_dump(), indent=2)}",
                )
            ]
        elif name == "get_premium_index_price_kline":
            result = get_premium_index_price_kline(**arguments)
            return [
                TextContent(
                    type="text",
                    text=f"Premium index price kline data for {result.symbol} ({result.category}):\n"
                    f"{json.dumps(result.model_dump(), indent=2)}",
                )
            ]
        elif name == "get_instruments_info":
            result = get_instruments_info(**arguments)
            return [TextContent(type="text", text=f"Instruments info for {result.category}:\n{json.dumps(result.model_dump(), indent=2)}")]
        elif name == "get_funding_rate_history":
            result = get_funding_rate_history(**arguments)
            return [
                TextContent(type="text", text=f"Funding rate history for {result.category}:\n{json.dumps(result.model_dump(), indent=2)}")
            ]
        elif name == "get_open_interest":
            result = get_open_interest(**arguments)
            return [
                TextContent(
                    type="text",
                    text=f"Open interest data for {result.symbol} ({result.category}):\n{json.dumps(result.model_dump(), indent=2)}",
                )
            ]
        elif name == "get_insurance":
            result = get_insurance(**arguments)
            return [
                TextContent(
                    type="text", text=f"Insurance fund data (updated: {result.updatedTime}):\n{json.dumps(result.model_dump(), indent=2)}"
                )
            ]
        elif name == "get_risk_limit":
            result = get_risk_limit(**arguments)
            return [TextContent(type="text", text=f"Risk limit data for {result.category}:\n{json.dumps(result.model_dump(), indent=2)}")]
        elif name == "get_long_short_ratio":
            result = get_long_short_ratio(**arguments)
            return [TextContent(type="text", text=f"Long/short ratio data:\n{json.dumps(result.model_dump(), indent=2)}")]

        # Trading Tools (TRADING_ENABLED check is now primarily within trade.py functions)
        # The tools are only listed if TRADING_ENABLED is true,
        # but the functions in trade.py provide a secondary check.
        elif name == "place_order":
            result = place_order(**arguments)
            return [TextContent(type="text", text=f"Place Order Response:\n{json.dumps(result.model_dump(), indent=2)}")]
        elif name == "amend_order":
            result = amend_order(**arguments)
            return [TextContent(type="text", text=f"Amend Order Response:\n{json.dumps(result.model_dump(), indent=2)}")]
        elif name == "cancel_order":
            result = cancel_order(**arguments)
            return [TextContent(type="text", text=f"Cancel Order Response:\n{json.dumps(result.model_dump(), indent=2)}")]
        elif name == "get_open_closed_orders":  # Read-only
            result = get_open_closed_orders(**arguments)
            return [TextContent(type="text", text=f"Open/Closed Orders:\n{json.dumps(result.model_dump(), indent=2)}")]
        elif name == "cancel_all_orders":
            result = cancel_all_orders(**arguments)
            return [TextContent(type="text", text=f"Cancel All Orders Response:\n{json.dumps(result.model_dump(), indent=2)}")]
        elif name == "get_order_history":  # Read-only
            result = get_order_history(**arguments)
            return [TextContent(type="text", text=f"Order History:\n{json.dumps(result.model_dump(), indent=2)}")]
        elif name == "get_trade_history":  # Read-only
            result = get_trade_history(**arguments)
            return [TextContent(type="text", text=f"Trade History:\n{json.dumps(result.model_dump(), indent=2)}")]
        elif name == "batch_place_order":
            result = batch_place_order(**arguments)
            return [TextContent(type="text", text=f"Batch Place Order Response:\n{json.dumps(result.model_dump(), indent=2)}")]
        elif name == "batch_amend_order":
            result = batch_amend_order(**arguments)
            return [TextContent(type="text", text=f"Batch Amend Order Response:\n{json.dumps(result.model_dump(), indent=2)}")]
        elif name == "batch_cancel_order":
            result = batch_cancel_order(**arguments)
            return [TextContent(type="text", text=f"Batch Cancel Order Response:\n{json.dumps(result.model_dump(), indent=2)}")]
        elif name == "get_wallet_balance":
            result = get_wallet_balance(**arguments)
            return [TextContent(type="text", text=f"Wallet Balance:\n{json.dumps(result.model_dump(), indent=2)}")]
        elif name == "get_single_coin_balance":
            result = get_single_coin_balance(**arguments)
            return [TextContent(type="text", text=f"Single Coin Balance:\n{json.dumps(result.model_dump(), indent=2)}")]
        elif name == "get_account_info":
            result = get_account_info(**arguments)
            return [
                TextContent(type="text", text=f"Account Information:\n{json.dumps(result.model_dump(), indent=2)}")
            ]  # Position Management Tools
        elif name == "get_position_info":
            result = get_position_info(**arguments)
            return [TextContent(type="text", text=f"Position Information:\n{json.dumps(result.model_dump(), indent=2)}")]
        elif name == "get_closed_pnl":
            result = get_closed_pnl(**arguments)
            return [TextContent(type="text", text=f"Closed P&L:\n{json.dumps(result.model_dump(), indent=2)}")]
        elif name == "set_leverage":
            result = set_leverage(**arguments)
            return [TextContent(type="text", text=f"Set Leverage Response:\n{json.dumps(result.model_dump(), indent=2)}")]
        elif name == "switch_cross_isolated_margin":
            result = switch_cross_isolated_margin(**arguments)
            return [TextContent(type="text", text=f"Switch Margin Mode Response:\n{json.dumps(result.model_dump(), indent=2)}")]
        elif name == "switch_position_mode":
            result = switch_position_mode(**arguments)
            return [TextContent(type="text", text=f"Switch Position Mode Response:\n{json.dumps(result.model_dump(), indent=2)}")]
        elif name == "set_trading_stop":
            result = set_trading_stop(**arguments)
            return [TextContent(type="text", text=f"Set Trading Stop Response:\n{json.dumps(result.model_dump(), indent=2)}")]
        elif name == "set_auto_add_margin":
            result = set_auto_add_margin(**arguments)
            return [TextContent(type="text", text=f"Set Auto Add Margin Response:\n{json.dumps(result.model_dump(), indent=2)}")]
        elif name == "modify_position_margin":
            result = modify_position_margin(**arguments)
            return [TextContent(type="text", text=f"Modify Position Margin Response:\n{json.dumps(result.model_dump(), indent=2)}")]
        elif name == "place_trigger_order":
            result = place_trigger_order(**arguments)
            return [TextContent(type="text", text=f"Place Trigger Order Response:\n{json.dumps(result.model_dump(), indent=2)}")]
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as e:
        logger.error(f"Error calling tool {name} with arguments {arguments}: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error calling {name}: {str(e)}")]


@server.list_resources()
async def handle_list_resources() -> List[Resource]:
    """List available resources."""
    return [
        Resource(
            uri=AnyUrl("bybit://market/info"),
            name="Bybit Market Information",
            description="General information about Bybit market endpoints and capabilities",
            mimeType="text/plain",
        )
    ]


@server.read_resource()
async def handle_read_resource(uri: AnyUrl) -> str:
    """Read resource content."""
    if str(uri) == "bybit://market/info":
        content = """
# Bybit MCP Server

This MCP server provides access to Bybit's v5 Market API endpoints.

## Available Endpoints:

### Core Market Data
- get_server_time: Get Bybit server time
- get_tickers: Get ticker information for symbols
- get_order_book: Get order book depth
- get_recent_trades: Get recent trade history

### Kline/Candlestick Data
- get_kline: Get standard candlestick data
- get_mark_price_kline: Get mark price klines
- get_index_price_kline: Get index price klines
- get_premium_index_price_kline: Get premium index price klines

### Trading Information
- get_instruments_info: Get trading instrument details
- get_funding_rate_history: Get historical funding rates
- get_open_interest: Get open interest data
- get_risk_limit: Get risk limit information

### Statistics
- get_insurance: Get insurance fund data
- get_long_short_ratio: Get long/short ratio statistics

## Supported Categories:
- linear: USDT perpetual, USDC perpetual, USDC futures
- inverse: Inverse perpetual, Inverse futures
- option: Options
- spot: Spot trading

## Usage:
Each tool accepts parameters specific to the endpoint. Required parameters
are marked in the tool schema. Most tools support optional filtering by
symbol, category, time ranges, and pagination.
        """
        return content.strip()
    else:
        raise ValueError(f"Unknown resource: {uri}")


async def main() -> None:
    """Main entry point for the Bybit MCP server."""
    # Initialize the server
    logger.info("Starting Bybit MCP Server...")

    async with stdio_server() as (read_stream, write_stream):
        logger.info("Server initialized and ready for connections")
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="bybit-mcp",
                server_version="0.1.0",
                capabilities=server.get_capabilities(NotificationOptions(), {}),
            ),
        )


def cli_main() -> None:
    """CLI entry point that wraps the async main function."""
    asyncio.run(main())


if __name__ == "__main__":
    cli_main()
