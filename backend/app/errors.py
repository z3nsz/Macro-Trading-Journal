"""Application errors that the API turns into clear HTTP responses (see main.py)."""

from app.domain.trade_rules import RuleViolation


class NotFoundError(Exception):
    """The item doesn't exist OR belongs to someone else — we deliberately don't say which."""

    def __init__(self, what: str):
        super().__init__(f"{what} not found")
        self.what = what


class ConflictError(Exception):
    """The request clashes with existing data (e.g. duplicate name)."""


class RulesViolated(Exception):
    def __init__(self, violations: list[RuleViolation]):
        super().__init__("Validation failed")
        self.violations = violations
