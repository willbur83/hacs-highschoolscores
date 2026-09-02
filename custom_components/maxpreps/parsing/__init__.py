"""MaxPreps payload parsing."""

from custom_components.maxpreps.parsing.next_data import extract_page_props
from custom_components.maxpreps.parsing.search import parse_search_page_props

__all__ = ["extract_page_props", "parse_search_page_props"]
