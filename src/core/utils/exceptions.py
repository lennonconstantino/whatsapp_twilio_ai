class AppError(Exception):
    """Base exception for application errors."""

    pass


class ConcurrencyError(AppError):
    """Raised when an optimistic locking conflict occurs."""

    def __init__(
        self,
        message: str = "Concurrency conflict detected",
        current_version: int = None,
    ):
        self.current_version = current_version
        super().__init__(message)


class DuplicateError(AppError):
    """Raised when a unique constraint violation occurs."""

    pass
