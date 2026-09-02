"""MaxPreps client exceptions."""


class MaxPrepsError(Exception):
    """Base exception for MaxPreps client errors."""


class NextDataNotFoundError(MaxPrepsError):
    """Expected Next.js __NEXT_DATA__ document data was not found in HTML."""


class MalformedNextDataError(MaxPrepsError):
    """__NEXT_DATA__ was present but could not be parsed as valid Next.js JSON."""


class SearchSchemaError(MaxPrepsError):
    """School search pageProps did not match the expected schema."""


class SportSeasonsSchemaError(MaxPrepsError):
    """School-home sportSeasons rows did not match the expected schema."""


class ContestSchemaError(MaxPrepsError):
    """Schedule contests[] rows did not match the expected positional schema."""


class CurrentCohortError(MaxPrepsError):
    """Current school-year cohort could not be determined from team-season rows."""


class CurrentCohortEmptyError(CurrentCohortError):
    """No team-season rows were provided."""


class CurrentCohortAmbiguousError(CurrentCohortError):
    """Team-season rows did not yield an unambiguous current cohort."""


class TransportError(MaxPrepsError):
    """Base exception for transport-layer failures."""


class TransportHttpError(TransportError):
    """HTTP response whose final status was not successful."""

    def __init__(self, message: str, *, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


class TransportTimeoutError(TransportError):
    """Request or read timed out."""


class TransportResponseTooLargeError(TransportError):
    """Response body exceeded the configured size cap."""


class TransportInvalidResponseError(TransportError):
    """HTTP succeeded but the body was empty or not plausibly HTML."""
