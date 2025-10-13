from bybit_mcp.models.position_models import GetPositionInfoResponse


def test_position_parses_without_option_greeks():
    sample_response = {
        "retCode": 0,
        "retMsg": "OK",
        "result": {
            "category": "linear",
            "nextPageCursor": "",
            "list": [
                {
                    "positionIdx": 0,
                    "riskId": 1,
                    "riskLimitValue": "100000",
                    "symbol": "SKYAIUSDT",
                    "side": "Buy",
                    "size": "10",
                    "avgPrice": "1.25",
                    "positionValue": "12.5",
                    "tradeMode": 0,
                    "autoAddMargin": 0,
                    "positionStatus": "Open",
                    "leverage": "10",
                    "markPrice": "1.30",
                    "liqPrice": "0.80",
                    "bustPrice": "0.75",
                    "positionIM": "1.25",
                    "positionMM": "0.50",
                    "positionBalance": "1.25",
                    "takeProfit": "1.50",
                    "stopLoss": "1.00",
                    "trailingStop": "0",
                    "unrealisedPnl": "0.50",
                    "curRealisedPnl": "0.00",
                    "cumRealisedPnl": "0.00",
                    "adlRankIndicator": 2,
                    "createdTime": "1718131200000",
                    "updatedTime": "1718134800000",
                }
            ],
        },
    }

    response = GetPositionInfoResponse(**sample_response)
    position = response.result.list[0]

    assert position.symbol == "SKYAIUSDT"
    assert position.delta is None
    assert position.gamma is None
    assert position.vega is None
    assert position.theta is None
