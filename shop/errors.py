class UserError(Exception):
    pass


class ValidationUserError(UserError):
    pass


class NotFoundUserError(UserError):
    pass


class AuthenticationUserError(UserError):
    pass


class ShopError(Exception):
    pass


class ValidationError(ShopError):
    pass


class NotFoundError(ShopError):
    pass
