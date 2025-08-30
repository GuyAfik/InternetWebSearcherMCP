import asyncio
from lifespan import mcp_context_lifespan
from main import (
    wikipedia_search,
    crawl_single_page,
    indepth_crawl_url,
    mcp,
    adaptive_crawling,
)


async def client_testing():
    result = await wikipedia_search(None, query="python programming", sentences=50)
    print(result)

    async with mcp_context_lifespan(mcp) as context:
        result = await crawl_single_page(context, url="https://pnina-afik-art.com")
        print(result)

    # sitemap
    async with mcp_context_lifespan(mcp) as context:
        result = await indepth_crawl_url(
            context, url="https://backlinko.com/sitemap_index.xml"
        )
        print(result)

    # webpage with depth 2 does not work
    async with mcp_context_lifespan(mcp) as context:
        result = await indepth_crawl_url(
            context, url="https://pnina-afik-art.com/about", max_depth=2
        )
        print(result)

    async with mcp_context_lifespan(mcp) as context:
        result = await adaptive_crawling(
            context,
            "https://docs.python.org/3/library/asyncio.html",
            "async await context managers coroutines",
        )
        print(result)


def main():
    asyncio.run(client_testing())


if __name__ == "__main__":
    main()
