import concurrent.futures
import json
import logging
import os
import re
import time
import urllib.parse
from typing import Dict, List, Optional, Set, Tuple, Union

import backoff
import dspy
import httpx
import requests
import ujson
from dspy.retrieve.retrieve import Retrieve
from pathlib import Path

from .interface import Information
from .utils import ArticleTextProcessing

logging.basicConfig(
    level=logging.INFO, format="%(name)s : %(levelname)-8s : %(message)s"
)
logger = logging.getLogger(__name__)


class BingSearch(dspy.Retrieve):
    """Retrieve information from custom queries using Bing."""

    def __init__(
        self,
        bing_search_api_key=None,
        k=10,
        exclude_urls=None,
        include_raw_content=False,
        include_domains=None,
        exclude_domains=None,
        freshness=None,
        **kwargs,
    ):
        """
        Initialize the BingSearch retriever.

        Args:
            bing_search_api_key: API key for Bing Search. If None, will try to get from environment variable BING_SEARCH_API_KEY.
            k: Number of results to return.
            exclude_urls: List of URLs to exclude from the search results.
            include_raw_content: Whether to include raw content in the search results.
            include_domains: List of domains to include in the search results.
            exclude_domains: List of domains to exclude from the search results.
            freshness: Filter search results by time. Options: 'Day', 'Week', 'Month'.
            **kwargs: Additional arguments to pass to the Bing Search API.
        """
        super().__init__()
        self.bing_search_api_key = bing_search_api_key or os.environ.get(
            "BING_SEARCH_API_KEY"
        )
        if not self.bing_search_api_key:
            raise ValueError(
                "Bing Search API key must be provided or set as environment variable BING_SEARCH_API_KEY."
            )
        self.k = k
        self.exclude_urls = exclude_urls or []
        self.include_raw_content = include_raw_content
        self.include_domains = include_domains
        self.exclude_domains = exclude_domains
        self.freshness = freshness
        self.kwargs = kwargs

    @backoff.on_exception(
        backoff.expo,
        (
            requests.exceptions.RequestException,
            httpx.HTTPError,
            json.JSONDecodeError,
            KeyError,
        ),
        max_tries=3,
    )
    def forward(self, query: str) -> List[Dict]:
        """
        Forward the query to Bing Search API and return the results.

        Args:
            query: Query to search for.

        Returns:
            List of dictionaries containing the search results.
        """
        if not query:
            return []

        headers = {"Ocp-Apim-Subscription-Key": self.bing_search_api_key}
        params = {
            "q": query,
            "count": self.k,
            "offset": 0,
            "mkt": "en-US",
            "safesearch": "Moderate",
        }

        if self.include_domains:
            domain_filter = " OR ".join(
                [f"site:{domain}" for domain in self.include_domains]
            )
            params["q"] = f"{params['q']} ({domain_filter})"

        if self.exclude_domains:
            domain_filter = " ".join(
                [f"-site:{domain}" for domain in self.exclude_domains]
            )
            params["q"] = f"{params['q']} {domain_filter}"

        if self.freshness:
            params["freshness"] = self.freshness

        response = requests.get(
            "https://api.bing.microsoft.com/v7.0/search", headers=headers, params=params
        )
        response.raise_for_status()
        search_results = response.json()

        if "webPages" not in search_results:
            return []

        collected_results = []
        for item in search_results["webPages"]["value"]:
            url = item["url"]
            if url in self.exclude_urls:
                continue

            title = item["name"]
            description = item["snippet"]
            snippets = [description]

            if self.include_raw_content:
                try:
                    content = ArticleTextProcessing.extract_article_text(url)
                    if content:
                        snippets.append(content)
                except Exception as e:
                    logger.warning(f"Failed to extract content from {url}: {e}")

            result = {
                "url": url,
                "title": title,
                "description": description,
                "snippets": snippets,
            }
            collected_results.append(result)

        return collected_results


class GoogleSearch(dspy.Retrieve):
    """Retrieve information from custom queries using Google."""

    def __init__(
        self,
        google_search_api_key=None,
        google_cse_id=None,
        k=10,
        exclude_urls=None,
        include_raw_content=False,
        **kwargs,
    ):
        """
        Initialize the GoogleSearch retriever.

        Args:
            google_search_api_key: API key for Google Search. If None, will try to get from environment variable GOOGLE_SEARCH_API_KEY.
            google_cse_id: Custom Search Engine ID. If None, will try to get from environment variable GOOGLE_CSE_ID.
            k: Number of results to return.
            exclude_urls: List of URLs to exclude from the search results.
            include_raw_content: Whether to include raw content in the search results.
            **kwargs: Additional arguments to pass to the Google Search API.
        """
        super().__init__()
        self.google_search_api_key = google_search_api_key or os.environ.get(
            "GOOGLE_SEARCH_API_KEY"
        )
        self.google_cse_id = google_cse_id or os.environ.get("GOOGLE_CSE_ID")
        if not self.google_search_api_key:
            raise ValueError(
                "Google Search API key must be provided or set as environment variable GOOGLE_SEARCH_API_KEY."
            )
        if not self.google_cse_id:
            raise ValueError(
                "Google Custom Search Engine ID must be provided or set as environment variable GOOGLE_CSE_ID."
            )
        self.k = k
        self.exclude_urls = exclude_urls or []
        self.include_raw_content = include_raw_content
        self.kwargs = kwargs

    @backoff.on_exception(
        backoff.expo,
        (
            requests.exceptions.RequestException,
            httpx.HTTPError,
            json.JSONDecodeError,
            KeyError,
        ),
        max_tries=3,
    )
    def forward(self, query_or_queries=None, **kwargs) -> List[Dict]:
        """
        Forward the query to Google Search API and return the results.

        Args:
            query_or_queries: Query or list of queries to search for.
            **kwargs: Additional arguments.

        Returns:
            List of dictionaries containing the search results.
        """
        if query_or_queries is None:
            return []
            
        # Handle both single query and list of queries
        if isinstance(query_or_queries, list):
            query = query_or_queries[0] if query_or_queries else ""
        else:
            query = query_or_queries
            
        if not query:
            return []

        url = f"https://www.googleapis.com/customsearch/v1"
        params = {
            "key": self.google_search_api_key,
            "cx": self.google_cse_id,
            "q": query,
            "num": self.k,
        }

        response = requests.get(url, params=params)
        response.raise_for_status()
        search_results = response.json()

        if "items" not in search_results:
            return []

        collected_results = []
        for item in search_results["items"]:
            url = item["link"]
            if url in self.exclude_urls:
                continue

            title = item["title"]
            description = item.get("snippet", "")
            snippets = [description]

            if self.include_raw_content:
                try:
                    content = ArticleTextProcessing.extract_article_text(url)
                    if content:
                        snippets.append(content)
                except Exception as e:
                    logger.warning(f"Failed to extract content from {url}: {e}")

            result = {
                "url": url,
                "title": title,
                "description": description,
                "snippets": snippets,
            }
            collected_results.append(result)

        return collected_results


class TavilySearchRM(dspy.Retrieve):
    """Retrieve information from custom queries using Tavily. Documentation and examples can be found at https://docs.tavily.com/docs/python-sdk/tavily-search/examples"""

    def __init__(
        self,
        tavily_search_api_key=None,
        k=10,
        exclude_urls=None,
        include_raw_content=False,
        include_domains=None,
        exclude_domains=None,
        search_depth="basic",
        max_results=10,
        **kwargs,
    ):
        """
        Initialize the TavilySearchRM retriever.

        Args:
            tavily_search_api_key: API key for Tavily Search. If None, will try to get from environment variable TAVILY_API_KEY.
            k: Number of results to return.
            exclude_urls: List of URLs to exclude from the search results.
            include_raw_content: Whether to include raw content in the search results.
            include_domains: List of domains to include in the search results.
            exclude_domains: List of domains to exclude from the search results.
            search_depth: Depth of search. Options: 'basic', 'advanced'.
            max_results: Maximum number of results to return.
            **kwargs: Additional arguments to pass to the Tavily Search API.
        """
        super().__init__()
        self.tavily_search_api_key = tavily_search_api_key or os.environ.get(
            "TAVILY_API_KEY"
        )
        if not self.tavily_search_api_key:
            raise ValueError(
                "Tavily Search API key must be provided or set as environment variable TAVILY_API_KEY."
            )
        self.k = k
        self.exclude_urls = exclude_urls or []
        self.include_raw_content = include_raw_content
        self.include_domains = include_domains
        self.exclude_domains = exclude_domains
        self.search_depth = search_depth
        self.max_results = max_results
        self.kwargs = kwargs

    @backoff.on_exception(
        backoff.expo,
        (
            requests.exceptions.RequestException,
            httpx.HTTPError,
            json.JSONDecodeError,
            KeyError,
        ),
        max_tries=3,
    )
    def forward(self, query_or_queries=None, exclude_urls=None, **kwargs) -> List[Dict]:
        """
        Forward the query to Tavily Search API and return the results.

        Args:
            query_or_queries: Query or list of queries to search for.
            exclude_urls: List of URLs to exclude from the search results.
            **kwargs: Additional arguments.

        Returns:
            List of dictionaries containing the search results.
        """
        if query_or_queries is None:
            return []
            
        # Handle both single query and list of queries
        if isinstance(query_or_queries, list):
            query = query_or_queries[0] if query_or_queries else ""
        else:
            query = query_or_queries
            
        if not query:
            return []

        # Combine exclude_urls from parameters and instance
        exclude_urls = list(set((exclude_urls or []) + (self.exclude_urls or [])))

        try:
            from tavily import TavilyClient
        except ImportError:
            raise ImportError(
                "Tavily Python SDK is not installed. Please install it with `pip install tavily-python`."
            )

        client = TavilyClient(api_key=self.tavily_search_api_key)

        search_params = {
            "query": query,
            "search_depth": self.search_depth,
            "max_results": self.max_results,
        }

        if self.include_domains:
            search_params["include_domains"] = self.include_domains

        if self.exclude_domains:
            search_params["exclude_domains"] = self.exclude_domains

        try:
            response = client.search(**search_params)
            search_results = response.get("results", [])
        except Exception as e:
            logger.warning(f"Tavily search failed: {e}")
            return []

        collected_results = []
        for item in search_results[: self.k]:
            try:
                url = item.get("url", "")
                if url and url not in exclude_urls:
                    title = item.get("title", "")
                    description = item.get("description", "")
                    content = item.get("content", "")
                    snippets = [description]

                    if content and self.include_raw_content:
                        snippets.append(content)
                    elif self.include_raw_content and not content:
                        try:
                            extracted_content = ArticleTextProcessing.extract_article_text(
                                url
                            )
                            if extracted_content:
                                snippets.append(extracted_content)
                        except Exception as e:
                            logger.warning(f"Failed to extract content from {url}: {e}")

                    result = {
                        "url": url,
                        "title": title,
                        "description": description,
                        "snippets": snippets,
                    }
                    collected_results.append(result)
                else:
                    print(f"invalid source {url} or url in exclude_urls")
            except Exception as e:
                print(f"Error occurs when processing result: {e}")
                print(f"Error occurs when searching query {query}: {e}")

        return collected_results


class WikipediaSearch(dspy.Retrieve):
    """Retrieve information from Wikipedia."""

    def __init__(
        self,
        k=3,
        exclude_urls=None,
        include_raw_content=True,
        **kwargs,
    ):
        """
        Initialize the WikipediaSearch retriever.

        Args:
            k: Number of results to return.
            exclude_urls: List of URLs to exclude from the search results.
            include_raw_content: Whether to include raw content in the search results.
            **kwargs: Additional arguments to pass to the Wikipedia API.
        """
        super().__init__()
        self.k = k
        self.exclude_urls = exclude_urls or []
        self.include_raw_content = include_raw_content
        self.kwargs = kwargs

    def forward(self, query_or_queries=None, exclude_urls=None, **kwargs) -> List[Dict]:
        """
        Forward the query to Wikipedia API and return the results.

        Args:
            query_or_queries: Query or list of queries to search for.
            exclude_urls: List of URLs to exclude from the search results.
            **kwargs: Additional arguments.

        Returns:
            List of dictionaries containing the search results.
        """
        if query_or_queries is None:
            return []
            
        # Handle both single query and list of queries
        if isinstance(query_or_queries, list):
            query = query_or_queries[0] if query_or_queries else ""
        else:
            query = query_or_queries
            
        if not query:
            return []

        # Combine exclude_urls from parameters and instance
        exclude_urls = list(set((exclude_urls or []) + (self.exclude_urls or [])))

        try:
            import wikipedia
        except ImportError:
            raise ImportError(
                "Wikipedia Python SDK is not installed. Please install it with `pip install wikipedia`."
            )

        try:
            search_results = wikipedia.search(query, results=self.k)
        except Exception as e:
            logger.warning(f"Wikipedia search failed: {e}")
            return []

        collected_results = []
        for title in search_results:
            try:
                page = wikipedia.page(title, auto_suggest=False)
                url = page.url
                if url in exclude_urls:
                    continue

                title = page.title
                description = page.summary.split("\n")[0]
                snippets = [description]

                if self.include_raw_content:
                    content = page.content
                    if content:
                        snippets.append(content)

                result = {
                    "url": url,
                    "title": title,
                    "description": description,
                    "snippets": snippets,
                }
                collected_results.append(result)
            except Exception as e:
                logger.warning(f"Failed to get Wikipedia page for {title}: {e}")

        return collected_results
