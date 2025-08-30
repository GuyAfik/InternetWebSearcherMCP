import json
import os

from crawler import Crawler
from fastmcp import FastMCP, Context
from lifespan import mcp_context_lifespan
from crawl4ai import CrawlerRunConfig, CacheMode, CrawlResult

from sitemap import is_sitemap_url

mcp = FastMCP(
    "mcp-internet-web-searcher",
    lifespan=mcp_context_lifespan,
    host=os.getenv("HOST", "0.0.0.0"),
    port=os.getenv("PORT", 8051),
)


def is_text_url_file(url: str) -> bool:
    return url.endswith(".txt")


@mcp.tool()
async def crawl_single_page(context: Context, url: str) -> str:
    try:
        run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, stream=False)
        crawler = context.request_context.lifespan_context.crawler
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
    crawl_type = ""
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
                "url": url,
                "pages_crawled": len(crawl_results),
                "urls_crawled": [doc["url"] for doc in crawl_results][:5]
                + (["..."] if len(crawl_results) > 5 else []),
            }
        )

    except Exception as e:
        print(f"Failed to crawl url {url}: {e}")


def main():
    mcp.run()


if __name__ == "__main__":
    main()
