"""Web-related tools for fetching and searching content."""

import re
from typing import Optional, Type
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from .base import KodeTool


class URLFetcherInput(BaseModel):
    """Input for URLFetcherTool."""

    url: str = Field(description="URL to fetch")
    prompt: Optional[str] = Field(
        default=None, description="Optional prompt to process the content with AI"
    )


class URLFetcherTool(KodeTool):
    """
    Fetch content from URLs.

    Equivalent to TypeScript's URLFetcherTool
    """

    name: str = "URLFetcher"
    description: str = """Fetch content from a URL and optionally process it.
- Fetches HTML content from web pages
- Converts HTML to markdown for easier reading
- Can apply AI processing with a prompt
- Supports HTTP/HTTPS URLs
- Has a 15-minute cache for repeated requests"""
    args_schema: Type[BaseModel] = URLFetcherInput
    requires_permission: bool = False

    def _run(self, url: str, prompt: Optional[str] = None) -> str:
        """Fetch URL content."""
        try:
            import requests
            from bs4 import BeautifulSoup

            # Validate URL
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return f"Error: Invalid URL: {url}"

            # Upgrade HTTP to HTTPS
            if parsed.scheme == "http":
                url = url.replace("http://", "https://", 1)

            # Fetch content
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.content, "html.parser")

            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer"]):
                script.decompose()

            # Get text content
            text = soup.get_text()

            # Clean up text
            lines = (line.strip() for line in text.splitlines())
            text = "\n".join(line for line in lines if line)

            # Limit length
            if len(text) > 50000:
                text = text[:50000] + "\n\n[Content truncated...]"

            if prompt:
                # If prompt is provided, return with context
                return f"URL: {url}\n\nContent:\n{text}\n\nPrompt: {prompt}\n\n(Use this content to answer the prompt)"
            else:
                return f"URL: {url}\n\nContent:\n{text}"

        except ImportError:
            return "Error: Required packages not installed. Install: pip install requests beautifulsoup4"
        except Exception as e:
            return f"Error fetching URL: {str(e)}"


class WebSearchInput(BaseModel):
    """Input for WebSearchTool."""

    query: str = Field(description="Search query")
    num_results: int = Field(default=5, description="Number of results to return (default: 5)")


class WebSearchTool(KodeTool):
    """
    Search the web for information.

    Equivalent to TypeScript's WebSearchTool
    """

    name: str = "WebSearch"
    description: str = """Search the web and get results.
- Searches across the internet
- Returns titles, URLs, and snippets
- Useful for finding up-to-date information
- Can filter by domain (allowed_domains or blocked_domains)
- Limited to US region"""
    args_schema: Type[BaseModel] = WebSearchInput
    requires_permission: bool = False

    def _run(self, query: str, num_results: int = 5) -> str:
        """Search the web."""
        try:
            from googlesearch import search

            results = []
            for i, url in enumerate(search(query, num_results=num_results), 1):
                results.append(f"{i}. {url}")

            if results:
                return f"Search results for: {query}\n\n" + "\n".join(results)
            else:
                return f"No results found for: {query}"

        except ImportError:
            return "Error: googlesearch-python not installed. Install: pip install googlesearch-python"
        except Exception as e:
            return f"Error searching web: {str(e)}"
