import logging
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from restaurant_service.application.use_cases import RegisterMealCommand, RegisterMealUseCase
from restaurant_service.domain.entities import InvalidAmountError, InvalidCardNumberError

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class RegisterMealRequest(BaseModel):
    card_number: str = Field(..., description="Customer loyalty card number")
    restaurant_code: str = Field(..., description="Unique code identifying the restaurant")
    amount: Decimal = Field(..., gt=0, description="Transaction amount in PEN")
    customer_email: Optional[str] = Field(default="", description="Customer email (optional)")


class MealTransactionResponse(BaseModel):
    transaction_id: str
    card_number: str
    restaurant_code: str
    amount: Decimal
    currency: str
    timestamp: str


class TransactionNotFoundResponse(BaseModel):
    detail: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post(
    "/api/v1/meals",
    status_code=status.HTTP_201_CREATED,
    summary="Register a new meal transaction",
)
async def register_meal(body: RegisterMealRequest, request: Request) -> MealTransactionResponse:
    """
    Register a meal transaction and publish it to the Kafka topic.

    Returns a 201 with the created transaction details.
    Returns 422 if the amount is invalid or the card number is empty.
    """
    use_case: RegisterMealUseCase = request.app.state.register_meal_use_case

    try:
        event = use_case.execute(
            RegisterMealCommand(
                card_number=body.card_number,
                restaurant_code=body.restaurant_code,
                amount=body.amount,
                customer_email=body.customer_email or "",
            )
        )
    except (InvalidAmountError, InvalidCardNumberError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    return MealTransactionResponse(
        transaction_id=str(event.transaction_id),
        card_number=event.card_number,
        restaurant_code=event.restaurant_code,
        amount=event.amount,
        currency=event.currency,
        timestamp=event.timestamp.isoformat(),
    )


@router.get(
    "/api/v1/meals/{transaction_id}",
    responses={404: {"model": TransactionNotFoundResponse}},
    summary="Retrieve a meal transaction by ID",
)
async def get_meal_transaction(transaction_id: str, request: Request) -> MealTransactionResponse:
    """
    Look up a meal transaction by its UUID.

    Returns 404 if the transaction does not exist in the repository.
    """
    try:
        tx_uuid = UUID(transaction_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"'{transaction_id}' is not a valid UUID",
        )

    repository = request.app.state.transaction_repository
    transaction = repository.get_by_id(tx_uuid)

    if transaction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction {transaction_id} not found",
        )

    return MealTransactionResponse(
        transaction_id=str(transaction.transaction_id),
        card_number=transaction.card_number,
        restaurant_code=transaction.restaurant_code,
        amount=transaction.amount,
        currency=transaction.currency,
        timestamp=transaction.timestamp.isoformat(),
    )


@router.get(
    "/health",
    summary="Health check",
)
async def health_check() -> dict:
    """Return service liveness status."""
    return {"status": "ok", "service": "restaurant_service"}
