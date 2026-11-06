"""Errors safe to show in either user interface."""


class ShopError(Exception):
    """A requested shop operation cannot be completed."""


class ValidationError(ShopError):
    """Input does not satisfy a business rule."""


class NotFoundError(ShopError):
    """The requested active product does not exist."""
