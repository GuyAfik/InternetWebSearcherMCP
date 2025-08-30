import json
import os

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


@mcp.tool()
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
    print("crawl_single_page called")
    try:
        run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, stream=False)
        crawler = ctx.request_context.lifespan_context.crawler
        result: CrawlResult = await crawler.arun(url=url, config=run_config)
        if result.success:
            return result.model_dump_json()
        return f"Failed to crawl url {url}"
    except Exception as e:
        print(f"Failed to crawl url {url}: {e}")
        return f"Failed to crawl url {url}"


@mcp.tool()
async def indepth_crawl_url(
    ctx: Context, url: str, max_depth: int = 3, max_concurrent: int = 10
) -> str:
    """
    Intelligently crawl a URL based on its type and store content in Supabase.

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
    print("indepth_crawl_url called")
    try:
        crawler: Crawler = ctx.request_context.lifespan_context.crawler
        if is_text_url_file(url):
            crawl_results = await crawler.crawl_markdown(url)
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
                "pages_crawled": len(crawl_results),
                "urls_crawled": [doc["url"] for doc in crawl_results][:5]
                + (["..."] if len(crawl_results) > 5 else []),
            }
        )

    except Exception as e:
        print(f"Failed to crawl url {url}: {e}")
        return json.dumps({"success": False, "url": url, "error": str(e)}, indent=4)


@mcp.tool()
def wikipedia(
    ctx: Context, query: str, sentences: int = 3, language: str = "en"
) -> str:
    print("wikipedia called")
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
    mcp.run()


if __name__ == "__main__":
    main()
