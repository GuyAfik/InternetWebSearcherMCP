from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator

from crawler import Crawler
from fastmcp import FastMCP
from crawl4ai import BrowserConfig


@dataclass
class MCPContext:
    crawler: Crawler


@asynccontextmanager
async def mcp_context_lifespan(server: FastMCP) -> AsyncIterator[MCPContext]:
    browser_config = BrowserConfig(headless=True, verbose=False)

    crawler = Crawler(config=browser_config)
    await crawler.__aenter__()
    try:
        yield MCPContext(crawler=crawler)
    finally:
        await crawler.__aexit__(None, None, None)
