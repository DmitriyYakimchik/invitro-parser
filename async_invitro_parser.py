import asyncio
import logging
import random
import re
import time
from typing import Dict, List, Optional
from urllib.parse import urljoin

import aiohttp
import pandas as pd
from bs4 import BeautifulSoup

from constants import BASE, BASE_HOST, CITY_SLUGS_CACHE_FILE, COLS
from invitro_parser import parse_analysis_page
from utils import (
    build_city_url,
    load_city_slugs_cache,
    make_safe_sheet_name,
    parse_city_slugs,
    save_city_slugs_cache,
)

logger = logging.getLogger(__name__)


class AsyncInvitroParser:
    def __init__(
        self,
        max_concurrent: int = 30,
        limit: int = 0,
        retries: int = 3,
        timeout: int = 60,
        backoff: float = 1.0,
    ):
        self.max_concurrent = max_concurrent
        self.limit = limit
        self.retries = retries
        self.timeout = timeout
        self.backoff = backoff
        self.session: aiohttp.ClientSession | None = None
        self.semaphore = asyncio.Semaphore(self.max_concurrent)
        self.city_slugs_cache = load_city_slugs_cache()
        self.city_slugs_from_site = {}

    async def create_session(self):
        connector = aiohttp.TCPConnector(limit_per_host=self.max_concurrent)
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/139.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "ru-RU,ru;q=0.9",
            },
        )

    async def close_session(self):
        if self.session:
            await self.session.close()
            self.session = None

    async def fetch(self, url: str) -> str:
        """Fetch page content with retries and backoff. Returns empty string on failure."""
        assert self.session is not None, "Session not created"
        for attempt in range(1, self.retries + 1):
            try:
                async with self.semaphore:
                    async with self.session.get(url) as resp:
                        status = resp.status
                        text = await resp.text()
                        if status == 200:
                            return text
                        if status in (429, 500, 502, 503, 504):
                            wait = self.backoff * (2 ** (attempt - 1)) + random.random()
                            logger.warning(
                                f"Transient status {status} for {url}. Retry {attempt}/{self.retries} after {wait:.1f}s"
                            )
                            await asyncio.sleep(wait)
                            continue
                        logger.error(f"Non-200 status {status} for {url}")
                        return text
            except asyncio.CancelledError:
                raise
            except Exception as e:
                wait = self.backoff * (2 ** (attempt - 1)) + random.random()
                logger.warning(f"Error fetching {url}: {e}. Retry {attempt}/{self.retries} after {wait:.1f}s")
                await asyncio.sleep(wait)
        logger.error(f"Failed to fetch {url} after {self.retries} attempts")
        return ""

    async def load_city_slugs_from_site(self):
        """Fetch city slugs from Invitro site."""
        test_url = f"{BASE}481/2212/"
        html = await self.fetch(test_url)
        if not html:
            logger.error("Failed to load page for city slugs")
            return {}
        return parse_city_slugs(html)

    async def collect_analysis_links(self, city: str) -> list[str]:
        """Collect analysis page links for a given city."""
        url = build_city_url(city, self.city_slugs_cache, self.city_slugs_from_site)
        logger.info(f"Fetching URL for city {city}: {url}")
        html = await self.fetch(url)
        if not html:
            return []
        soup = BeautifulSoup(html, "lxml")
        links = []

        for a in soup.select(".analyzes-list__item .analyzes-item__title a"):
            href = a.get("href")
            if href:
                full = urljoin(BASE_HOST, href)
                if full not in links:
                    links.append(full)

        if not links:
            for a in soup.select("a[href]"):
                href = a.get("href")
                if href and re.match(r"^/analizes/for-doctors/(?:[\w\-]+/)?\d+/\d+/?$", href):
                    full = urljoin(BASE_HOST, href)
                    if full not in links:
                        links.append(full)
        return links

    async def fetch_analysis_data(self, url: str) -> dict[str, str] | None:
        """Fetch and parse analysis page data."""
        html = await self.fetch(url)
        if not html:
            return None
        try:
            return parse_analysis_page(html, url)
        except Exception as e:
            logger.exception(f"Error parsing {url}: {e}")
            return None

    async def process_city(self, city: str) -> (pd.DataFrame, float):
        """Process one city: collect links, fetch data, build DataFrame."""
        logger.info(f"Start city: {city}")
        t0 = time.time()
        links = await self.collect_analysis_links(city)
        logger.info(f"City {city}: found {len(links)} analyses")
        if self.limit > 0:
            links = links[: self.limit]

        tasks = [self.fetch_analysis_data(link) for link in links]
        results = []
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=False)

        rows = [r for r in results if r]
        df = pd.DataFrame(rows).reindex(columns=COLS)
        elapsed = time.time() - t0
        logger.info(f"Finish city: {city} in {elapsed:.1f}s, records: {len(df)}")
        return df, elapsed

    async def run(self, cities: list[str], output_file: str):
        """Main entry point: process list of cities and save to Excel."""
        await self.create_session()
        total_t0 = time.time()
        try:
            self.city_slugs_from_site = await self.load_city_slugs_from_site()
            logger.info(f"Loaded {len(self.city_slugs_from_site)} city slugs from site")

            with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
                city_stats = []
                for city in cities:
                    try:
                        df, elapsed = await self.process_city(city)
                    except Exception as e:
                        logger.exception(f"Error processing city {city}: {e}")
                        df = pd.DataFrame(columns=COLS)
                        elapsed = 0.0

                    if df.empty:
                        pd.DataFrame(columns=COLS).to_excel(writer, sheet_name=make_safe_sheet_name(city), index=False)
                    else:
                        df.to_excel(writer, sheet_name=make_safe_sheet_name(city), index=False)

                    city_stats.append((city, len(df), elapsed))

            total_elapsed = time.time() - total_t0
            for city, cnt, t_sec in city_stats:
                logger.info(f"[{city}] rows={cnt} time={t_sec:.1f}s")
            logger.info(f"All done. Total time: {total_elapsed:.1f}s. File: {output_file}")

            save_city_slugs_cache(self.city_slugs_cache)
            logger.info(f"City slugs cache saved to {CITY_SLUGS_CACHE_FILE}")
        finally:
            await self.close_session()
