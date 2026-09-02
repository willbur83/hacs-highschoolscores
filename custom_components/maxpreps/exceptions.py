"""MaxPreps client exceptions."""


class MaxPrepsError(Exception):
    """Base exception for MaxPreps client errors."""


class NextDataNotFoundError(MaxPrepsError):
    """Expected Next.js __NEXT_DATA__ document data was not found in HTML."""


class MalformedNextDataError(MaxPrepsError):
    """__NEXT_DATA__ was present but could not be parsed as valid Next.js JSON."""


class SearchSchemaError(MaxPrepsError):
    """School search pageProps did not match the expected schema."""
