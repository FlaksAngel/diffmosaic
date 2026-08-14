from decimal import Decimal


def calculate_total(subtotal: Decimal, discount: Decimal) -> Decimal:
    if discount > Decimal("1"):
        raise ValueError("discount cannot exceed 100%")
    return subtotal * (Decimal("1") - discount)


DEFAULT_CURRENCY = "RUB"


def validate_quantity(quantity: int) -> None:
    if quantity < 1:
        raise ValueError("quantity must be positive")
