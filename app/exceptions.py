"""Errors the business logic raises. They say what went wrong in domain terms;
app/main.py decides which HTTP status each one becomes."""


class DomainError(Exception):
    pass


class NotFound(DomainError):
    pass


class Forbidden(DomainError):
    pass


class Conflict(DomainError):
    pass


class Unauthorized(DomainError):
    pass
