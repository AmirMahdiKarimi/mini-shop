class ShopError(Exception):
    pass


class ValidationError(ShopError):
    pass


class NotFoundError(ShopError):
    pass
