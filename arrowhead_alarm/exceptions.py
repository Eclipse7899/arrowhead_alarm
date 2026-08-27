"""Custom exceptions for the Arrowhead Alarm integration."""


class AuthError(Exception):
    """Base class for authentication-related errors."""
    pass


class NoStringMatchError(Exception):
    """Raised when no matching option is found in a union type."""

    def __init__(self, buffer: str) -> None:
        """Initialize NoUnionMatchError.

        Args:
            buffer: The line buffer that failed to match any option.

        """
        super().__init__(f"No matching option for line: '{buffer}'")
        self.buffer = buffer


class MissingCredentialsError(AuthError):
    """Raised when credentials are required but not provided."""

    def __init__(self, *args: object) -> None:
        """Initialize MissingCredentialsError.

        Args:
            *args: Additional arguments to pass to the base Exception class.

        """
        super().__init__(
            "Credentials are required for authentication but were not provided.", *args
        )


class InvalidCredentialsError(AuthError):
    """Raised when provided credentials are invalid."""

    def __init__(self) -> None:
        """Initialize InvalidCredentialsError."""
        super().__init__("Provided credentials are invalid.")
