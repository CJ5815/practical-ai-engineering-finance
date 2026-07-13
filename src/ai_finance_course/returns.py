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


def main() -> None:
    result = simple_return(100.0, 105.0)
    print(f"Return: {result:.2%}")


if __name__ == "__main__":
    main()
