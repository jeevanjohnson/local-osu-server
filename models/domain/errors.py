class DomainError(Exception):
    """Base error type for domain/usecase/repository failures."""


class NotFoundError(DomainError):
    """Raised when a required entity cannot be found."""


class SessionNotFoundError(NotFoundError):
    """Raised when no active session exists."""


class ProfileNotFoundError(NotFoundError):
    """Raised when a profile is missing."""


class ProfilesNotFoundError(NotFoundError):
    """Raised when there are no profiles available."""


class BeatmapNotFoundError(NotFoundError):
    """Raised when a beatmap lookup fails."""


class BeatmapSetNotFoundError(NotFoundError):
    """Raised when a beatmap set lookup fails."""


class ConflictError(DomainError):
    """Raised when an operation conflicts with current state."""


class SessionAlreadyExistsError(ConflictError):
    """Raised when creating a session while one is already active."""


class ProfileAlreadyExistsError(ConflictError):
    """Raised when trying to create an existing profile."""
