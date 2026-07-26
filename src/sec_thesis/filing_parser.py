"""Turn a cached filing's raw HTML into plain text suitable for prompting."""

from __future__ import annotations

import re
import warnings

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

# Some real filings embed XML-like namespace declarations inside an
# otherwise ordinary .htm document, which triggers a false-positive
# warning from bs4's HTML parser. Harmless here — we always want HTML
# parsing for cached filing documents.
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)


def extract_text(html: str) -> str:
    """Strip a filing's HTML down to clean, whitespace-collapsed plain text.

    Args:
        html: The raw HTML content of a cached filing document.

    Returns:
        Plain text with scripts/styles removed and whitespace collapsed,
        ready to include in an LLM prompt.
    """
    soup = BeautifulSoup(html, "lxml")

    for tag in soup(["script", "style"]):
        tag.decompose()

    # Modern 10-Ks embed inline XBRL: machine-readable tag data sitting in
    # display:none elements (often <ix:header>) that browsers never render
    # but get_text() would otherwise include as if it were filing prose.
    for tag in soup.find_all(style=re.compile(r"display:\s*none")):
        tag.decompose()

    text = soup.get_text(separator=" ")
    return re.sub(r"\s+", " ", text).strip()
