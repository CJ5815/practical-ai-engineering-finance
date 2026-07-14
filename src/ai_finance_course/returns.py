"""Small starter module used during the Python fundamentals weeks."""

from __future__ import annotations


def simple_return(beginning_price: float, ending_price: float) -> float:
    """Calculate a simple asset return.

    Args:
        beginning_price: Price at the beginning of the period. Must be positive.
        ending_price: Price at the end of the period. Must be non-negative.

    Returns:
        The decimal return. For example, 0.05 represents 5%.

    Raises:
        ValueError: If either input is outside the allowed range.
    """
    if beginning_price <= 0:
        raise ValueError("beginning_price must be greater than zero")
    if ending_price < 0:
        raise ValueError("ending_price cannot be negative")

    return (ending_price / beginning_price) - 1


def classify_return(value: float) -> str:
    """Classify a return as positive, negative, or flat.

    Args:
        value: A decimal return, such as the output of simple_return.

    Returns:
        "positive" if value > 0, "negative" if value < 0, otherwise "flat".
    """
    if value > 0:
        return "positive"
    if value < 0:
        return "negative"
    return "flat"


def main() -> None:
    result = simple_return(100.0, 105.0)
    print(f"Return: {result:.2%}")
    print(f"Classification: {classify_return(result)}")


if __name__ == "__main__":
    main()
