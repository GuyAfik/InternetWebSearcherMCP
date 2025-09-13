import json
import os
import traceback

import aiohttp

from crawler import Crawler
from fastmcp import FastMCP, Context
from lifespan import mcp_context_lifespan
from crawl4ai import CrawlerRunConfig, CacheMode, CrawlResult
import wikipedia
from utils import is_sitemap_url, is_text_url_file


mcp = FastMCP(
    "mcp-internet-web-searcher",
    lifespan=mcp_context_lifespan,
    host=os.getenv("HOST", "0.0.0.0"),
    port=os.getenv("PORT", 8051),
)


@mcp.tool("crawl_single_url_page")
async def crawl_single_page(ctx: Context, url: str) -> str:
    """
    Crawl a single web page and returns its content.

    This tool is ideal for quickly retrieving content from a specific URL without following links.

    Args:
        ctx: The MCP server provided context
        url: URL of the web page to crawl

    Returns:
        str: a json representation including URL markdown data.
    """
    try:
        run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, stream=False)
        crawler = ctx.request_context.lifespan_context.crawler
        result: CrawlResult = await crawler.arun(url=url, config=run_config)
        if result.success:
            return json.dumps({"url": url, "markdown": result.markdown})
        return json.dumps(
            {"success": False, "url": url, "error": "No content found"}, indent=4
        )
    except Exception as e:
        traceback.print_exc()
        return json.dumps({"success": False, "url": url, "error": str(e)}, indent=4)


@mcp.tool("deep_crawl_url")
async def indepth_crawl_url(
    ctx: Context, url: str, max_depth: int = 3, max_concurrent: int = 10
) -> str:
    """
    Intelligently crawl a URL based on its type.

    This tool automatically detects the URL type and applies the appropriate crawling method:
    - For sitemaps: Extracts and crawls all URLs in parallel
    - For text files (llms.txt): Directly retrieves the content
    - For regular webpages: Recursively crawls internal links up to the specified depth

    Args:
        ctx: The MCP server provided context
        url: URL to crawl (can be a regular webpage, sitemap.xml, or .txt file)
        max_depth: Maximum recursion depth for regular URLs (default: 3)
        max_concurrent: Maximum number of concurrent browser sessions (default: 10)

    Returns:
        str: a json representation including URL markdown data.

    """
    try:
        crawler: Crawler = ctx.request_context.lifespan_context.crawler
        if is_text_url_file(url):
            crawl_results = await crawler.simple_crawl(url)
            crawl_type = "text_file"
        elif is_sitemap_url(url):
            crawl_type = "sitemap"
            crawl_results = await crawler.crawl_sitemap(
                url, max_concurrent=max_concurrent
            )
        else:
            crawl_type = "webpage"
            crawl_results = await crawler.crawl_recursive_internal_links(
                [url], max_depth=max_depth, max_concurrent=max_concurrent
            )

        if not crawl_results:
            return json.dumps(
                {"success": False, "url": url, "error": "No content found"}, indent=4
            )

        return json.dumps(
            {
                "success": True,
                "crawl_type": crawl_type,
                "url": url,
                "results": crawl_results,
                "pages_crawled": len(crawl_results),
                "urls_crawled": [doc["url"] for doc in crawl_results][:5]
                + (["..."] if len(crawl_results) > 5 else []),
            }
        )

    except Exception as e:
        traceback.print_exc()
        return json.dumps({"success": False, "url": url, "error": str(e)}, indent=4)


@mcp.tool("adaptive_crawling")
async def adaptive_crawling(ctx: Context, url: str, query: str):
    """
    Starts at a URL and intelligently crawls linked pages to find an answer to a query.

    Args:
        ctx: The MCP server provided context
        url: The initial URL to start crawling from.
        query: The question or query to find answers for.

    Returns:
        A JSON object containing the crawled pages and a synthesized summary.
    """
    crawler = ctx.request_context.lifespan_context.crawler.adaptive_crawling

    try:
        result = await crawler.digest(start_url=url, query=query)
        return json.dumps(
            {
                "success": True,
                "url": url,
                "urls_crawled": [doc.url for doc in result.knowledge_base][:5],
                "pages_crawled": len(result.knowledge_base),
                "results": [
                    {"url": url, "markdown": crawl_result.markdown}
                    for crawl_result in result.knowledge_base
                ],
            }
        )
    except Exception as e:
        traceback.print_exc()
        return json.dumps(
            {"success": False, "url": url, "query": query, "error": str(e)}, indent=4
        )


@mcp.tool("web_search")
async def web_search(ctx: Context, query: str, max_results: int = 5) -> str:
    """
    Searches the web for a query using Serper.dev API and returns relevant URLs.

    Args:
        ctx: MCP context
        query: Search query
        max_results: Number of top results to return

    Returns:
        JSON string with list of relevant URLs, titles, and snippets
    """
    serper_api_key = os.getenv("SERPER_API_KEY")
    if not serper_api_key:
        return json.dumps({"success": False, "error": "SERPER_API_KEY not set"})

    url = "https://google.serper.dev/search"
    headers = {"X-API-KEY": serper_api_key, "Content-Type": "application/json"}
    payload = {"q": query, "num": max_results}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                data = await resp.json()

        # Extract top results
        results = []
        for r in data.get("organic", [])[:max_results]:
            results.append(
                {
                    "title": r.get("title"),
                    "url": r.get("link"),
                    "snippet": r.get("snippet"),
                }
            )

        return json.dumps({"query": query, "results": results}, indent=4)

    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, indent=4)


@mcp.tool("wikipedia_search")
async def wikipedia_search(
    ctx: Context, query: str, sentences: int = 3, language: str = "en"
) -> str:
    """
    Searches Wikipedia for a query and returns a summary of the top result.

    Args:
        ctx: The MCP server provided context
        query: The search query.
        sentences: The number of sentences to include in the summary.
        language: The language code for Wikipedia (e.g., 'en', 'es', 'de').

    Returns:
        A JSON object with the article title, summary, and URL.
    """
    try:
        wikipedia.set_lang(language)  # Set default language
        results = wikipedia.search(query)

        if not results:
            return json.dumps(
                {
                    "query": query,
                    "summary": None,
                    "url": None,
                    "error": "No results found.",
                }
            )

        page = wikipedia.page(results[0])
        summary = wikipedia.summary(page.title, sentences=sentences)

        return json.dumps(
            {
                "query": query,
                "title": page.title,
                "summary": summary,
                "url": page.url,
            }
        )

    except wikipedia.exceptions.DisambiguationError as e:
        return json.dumps(
            {
                "query": query,
                "summary": None,
                "url": None,
                "error": f"Disambiguation: {e.options}",
            }
        )
    except wikipedia.exceptions.PageError:
        return json.dumps(
            {"query": query, "summary": None, "url": None, "error": "Page not found."}
        )
    except Exception as e:
        return json.dumps(
            {"query": query, "summary": None, "url": None, "error": str(e)}
        )


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
