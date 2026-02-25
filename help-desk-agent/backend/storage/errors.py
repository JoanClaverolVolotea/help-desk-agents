from __future__ import annotations


class CategoryNotFoundError(ValueError):
    pass


class UseCaseNotFoundError(ValueError):
    pass


class NoDraftAvailableError(ValueError):
    pass


class TicketNotFoundError(ValueError):
    pass
