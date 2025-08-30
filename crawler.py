import os
from pathlib import Path
from typing import List, Dict, Any
from urllib.parse import urldefrag
from xml.etree import ElementTree

from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    AsyncLoggerBase,
    CrawlerRunConfig,
    CacheMode,
    MemoryAdaptiveDispatcher,
    AdaptiveCrawler,
)
from crawl4ai.async_crawler_strategy import AsyncCrawlerStrategy
import requests


class Crawler(AsyncWebCrawler):

    def __init__(
        self,
        crawler_strategy: AsyncCrawlerStrategy = None,
        config: BrowserConfig = None,
        base_directory: str = str(os.getenv("CRAWL4_AI_BASE_DIRECTORY", Path.home())),
        thread_safe: bool = False,
        logger: AsyncLoggerBase = None,
        **kwargs,
    ):
        super().__init__(
            crawler_strategy, config, base_directory, thread_safe, logger, **kwargs
        )
        self.requests = requests

    @property
    def adaptive_crawling(self) -> AdaptiveCrawler:
        return AdaptiveCrawler(self)

    async def crawl_markdown(self, url: str) -> List[Dict[str, Any]]:
        result = await self.arun(url=url, config=CrawlerRunConfig())
        if result.success and result.markdown:
            return [{"url": url, "markdown": result.markdown}]
        else:
            print(f"Failed to crawl {url}: {result.error_message}")
            return []

    async def crawl_sitemap(
        self, sitemap_url: str, max_concurrent: int = 10
    ) -> List[Dict[str, Any]]:
        resp = self.requests.get(sitemap_url)
        urls = []

        if resp.status_code == 200:
            try:
                tree = ElementTree.fromstring(resp.content)
                urls = [loc.text for loc in tree.findall(".//{*}loc")]
            except Exception as e:
                print(f"Error parsing sitemap XML: {e}")

        if urls:
            return await self.crawl_multiple_urls(urls, max_concurrent=max_concurrent)
        return urls

    async def crawl_multiple_urls(self, urls: List[str], max_concurrent: int = 10):
        crawl_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, stream=False)
        dispatcher = MemoryAdaptiveDispatcher(
            memory_threshold_percent=70.0,
            check_interval=1.0,
            max_session_permit=max_concurrent,
        )
        results = await self.arun_many(
            urls=urls, config=crawl_config, dispatcher=dispatcher
        )
        return [
            {"url": r.url, "markdown": r.markdown}
            for r in results
            if r.success and r.markdown
        ]

    async def crawl_recursive_internal_links(
        self, start_urls: List[str], max_depth: int = 3, max_concurrent: int = 10
    ) -> List[Dict[str, Any]]:
        run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, stream=False)
        dispatcher = MemoryAdaptiveDispatcher(
            memory_threshold_percent=70.0,
            check_interval=1.0,
            max_session_permit=max_concurrent,
        )

        visited = set()

        def normalize_url(url):
            return urldefrag(url)[0]

        current_urls = set([normalize_url(u) for u in start_urls])
        results_all = []

        for depth in range(max_depth):
            urls_to_crawl = [
                normalize_url(url)
                for url in current_urls
                if normalize_url(url) not in visited
            ]
            if not urls_to_crawl:
                break

            results = await self.arun_many(
                urls=urls_to_crawl, config=run_config, dispatcher=dispatcher
            )
            next_level_urls = set()

            for result in results:
                norm_url = normalize_url(result.url)
                visited.add(norm_url)

                if result.success and result.markdown:
                    results_all.append({"url": result.url, "markdown": result.markdown})
                    for link in result.links.get("internal", []):
                        next_url = normalize_url(link["href"])
                        if next_url not in visited:
                            next_level_urls.add(next_url)

            current_urls = next_level_urls

        return results_all
