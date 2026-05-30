import pytest
from decimal import Decimal
from uuid import UUID

from restaurant_service.application.use_cases import RegisterMealCommand, RegisterMealUseCase
from restaurant_service.domain.entities import InvalidAmountError
from shared.events.schemas import MealTransactionEvent


def test_execute_publishes_meal_transaction_event(mock_publisher, mock_repository, sample_command):
    """Calling execute() must invoke publisher.publish_meal_transaction exactly once
    with a MealTransactionEvent instance."""
    use_case = RegisterMealUseCase(publisher=mock_publisher, repository=mock_repository)
    use_case.execute(sample_command)

    mock_publisher.publish_meal_transaction.assert_called_once()
    args, _ = mock_publisher.publish_meal_transaction.call_args
    assert isinstance(args[0], MealTransactionEvent)


def test_execute_saves_to_repository(mock_publisher, mock_repository, sample_command):
    """Calling execute() must invoke repository.save exactly once with a MealTransaction."""
    from restaurant_service.domain.entities import MealTransaction

    use_case = RegisterMealUseCase(publisher=mock_publisher, repository=mock_repository)
    use_case.execute(sample_command)

    mock_repository.save.assert_called_once()
    saved_obj = mock_repository.save.call_args[0][0]
    assert isinstance(saved_obj, MealTransaction)


def test_execute_returns_meal_transaction_event(mock_publisher, mock_repository, sample_command):
    """execute() must return a MealTransactionEvent whose fields mirror the command values."""
    use_case = RegisterMealUseCase(publisher=mock_publisher, repository=mock_repository)
    event = use_case.execute(sample_command)

    assert isinstance(event, MealTransactionEvent)
    assert event.card_number == sample_command.card_number
    assert event.restaurant_code == sample_command.restaurant_code
    assert event.amount == sample_command.amount
    assert event.currency == "PEN"


def test_execute_with_invalid_amount_raises_error(mock_publisher, mock_repository):
    """execute() with amount=0 must raise InvalidAmountError before save or publish are called."""
    command = RegisterMealCommand(
        card_number="CARD-001",
        restaurant_code="REST-001",
        amount=Decimal("0"),
    )
    use_case = RegisterMealUseCase(publisher=mock_publisher, repository=mock_repository)

    with pytest.raises(InvalidAmountError):
        use_case.execute(command)

    mock_repository.save.assert_not_called()
    mock_publisher.publish_meal_transaction.assert_not_called()


def test_execute_assigns_transaction_id(mock_publisher, mock_repository, sample_command):
    """The MealTransactionEvent returned by execute() must carry a valid UUID transaction_id."""
    use_case = RegisterMealUseCase(publisher=mock_publisher, repository=mock_repository)
    event = use_case.execute(sample_command)

    assert isinstance(event.transaction_id, UUID)
