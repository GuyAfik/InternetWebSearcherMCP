import asyncio
from main import wikipedia_search, crawl_single_page, indepth_crawl_url
from lifespan import mcp_context_lifespan
from main import mcp


async def client_testing():
    result = wikipedia_search(None, query="python programming", sentences=50)
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
            context, url="https://en.wikipedia.org/wiki/Python", max_depth=2
        )
        print(result)
    pass


def main():
    asyncio.run(client_testing())


if __name__ == "__main__":
    main()
