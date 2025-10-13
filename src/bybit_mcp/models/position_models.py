# src/bybit_mcp/models/position_models.py
from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from .trade_models import BaseApiResponse  # Re-use BaseApiResponse for common fields


class PositionInfoItem(BaseModel):
    positionIdx: int
    riskId: int
    riskLimitValue: str
    symbol: str
    side: str
    size: str
    avgPrice: str
    positionValue: str
    tradeMode: int
    autoAddMargin: int
    positionStatus: str
    leverage: str
    markPrice: str
    liqPrice: str
    bustPrice: str
    positionIM: str
    positionMM: str
    positionBalance: str
    takeProfit: str
    stopLoss: str
    trailingStop: str
    sessionAvgPrice: Optional[str] = None  # For USDC contracts
    delta: Optional[str] = None  # Only for options
    gamma: Optional[str] = None  # Only for options
    vega: Optional[str] = None   # Only for options
    theta: Optional[str] = None  # Only for options
    unrealisedPnl: str
    curRealisedPnl: str
    cumRealisedPnl: str
    adlRankIndicator: int
    createdTime: str
    updatedTime: str
    # Fields that might be optional or not present in all responses
    tpslMode: Optional[str] = None
    tpLimitPrice: Optional[str] = None
    slLimitPrice: Optional[str] = None
    tpTriggerBy: Optional[str] = None
    slTriggerBy: Optional[str] = None
    seq: Optional[int] = None  # from docs, type might be long, using int
    isReduceOnly: Optional[bool] = None
    mmrSysUpdatedTime: Optional[str] = None
    leverageSysUpdatedTime: Optional[str] = None

    model_config = ConfigDict(extra="allow")


class PositionInfoResult(BaseModel):
    category: str
    nextPageCursor: str
    list: List[PositionInfoItem]


class GetPositionInfoResponse(BaseApiResponse):
    result: PositionInfoResult


# Models for Set Leverage
class SetLeverageResult(BaseModel):
    pass  # Empty result for successful leverage setting


class SetLeverageResponse(BaseApiResponse):
    result: SetLeverageResult


# Models for Switch Margin Mode
class SwitchMarginModeResult(BaseModel):
    pass  # Empty result for successful margin mode switch


class SwitchMarginModeResponse(BaseApiResponse):
    result: SwitchMarginModeResult


# Models for Switch Position Mode
class SwitchPositionModeResult(BaseModel):
    pass  # Empty result for successful position mode switch


class SwitchPositionModeResponse(BaseApiResponse):
    result: SwitchPositionModeResult


# Models for Set Trading Stop
class SetTradingStopResult(BaseModel):
    pass  # Empty result for successful trading stop setting


class SetTradingStopResponse(BaseApiResponse):
    result: SetTradingStopResult


# Models for Set Auto Add Margin
class SetAutoAddMarginResult(BaseModel):
    pass  # Empty result for successful auto add margin setting


class SetAutoAddMarginResponse(BaseApiResponse):
    result: SetAutoAddMarginResult


# Models for Add/Reduce Margin
class AddReduceMarginResult(BaseModel):
    positionIdx: int
    riskId: int
    riskLimitValue: str
    symbol: str
    side: str
    size: str
    avgPrice: str
    liqPrice: str
    bustPrice: str
    positionValue: str
    leverage: str
    autoAddMargin: int
    positionStatus: str
    positionIM: str
    positionMM: str
    unrealisedPnl: str
    cumRealisedPnl: str
    createdTime: str
    updatedTime: str


class AddReduceMarginResponse(BaseApiResponse):
    result: AddReduceMarginResult


# Models for Get Closed PnL
class ClosedPnlItem(BaseModel):
    symbol: str
    orderId: str
    side: str
    qty: str
    orderPrice: str
    orderType: str
    execType: str
    closedSize: str
    cumEntryValue: str
    avgEntryPrice: str
    cumExitValue: str
    avgExitPrice: str
    closedPnl: str
    fillCount: str
    leverage: str
    createdTime: str


class ClosedPnlResult(BaseModel):
    nextPageCursor: str
    category: str
    list: List[ClosedPnlItem]


class GetClosedPnlResponse(BaseApiResponse):
    result: ClosedPnlResult


# Models for Move Position
class MovePositionResult(BaseModel):
    blockTradeId: str


class MovePositionResponse(BaseApiResponse):
    result: MovePositionResult


# Models for Get Move Position History
class MovePositionHistoryItem(BaseModel):
    blockTradeId: str
    category: str
    orderId: str
    userId: int
    symbol: str
    side: str
    orderPrice: str
    orderQty: str
    execPrice: str
    execQty: str
    execValue: str
    execFee: str
    execTime: str
    resultStatus: str
    rejectParty: str


class MovePositionHistoryResult(BaseModel):
    nextPageCursor: str
    category: str
    list: List[MovePositionHistoryItem]


class GetMovePositionHistoryResponse(BaseApiResponse):
    result: MovePositionHistoryResult


# Models for Confirm New Risk Limit
class ConfirmNewRiskLimitResult(BaseModel):
    riskId: int
    riskLimitValue: str
    symbol: str
    side: str
    size: str
    positionValue: str
    leverage: str
    markPrice: str
    positionIM: str
    positionMM: str


class ConfirmNewRiskLimitResponse(BaseApiResponse):
    result: ConfirmNewRiskLimitResult
