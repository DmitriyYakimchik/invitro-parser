import argparse
import asyncio
import logging

from async_invitro_parser import AsyncInvitroParser

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(description="Scrape Invitro analyses and export to XLSX")
    parser.add_argument(
        "--cities",
        default="cities.txt",
        help="Path to file with list of cities (one per line)",
    )
    parser.add_argument("--output", default="results.xlsx", help="Output XLSX filename")
    parser.add_argument("--workers", type=int, default=40, help="Maximum concurrent requests")
    parser.add_argument("--limit", type=int, default=0, help="Max analyses per city (0 = all)")
    parser.add_argument("--retries", type=int, default=3, help="Number of retries on transient errors")
    parser.add_argument("--timeout", type=int, default=60, help="Total request timeout in seconds")
    parser.add_argument("--backoff", type=float, default=1.0, help="Base backoff seconds for retries")
    return parser.parse_args()


async def main():
    args = parse_args()
    with open(args.cities, encoding="utf-8") as f:
        cities = [line.strip() for line in f if line.strip()]

    parser = AsyncInvitroParser(
        max_concurrent=args.workers,
        limit=args.limit,
        retries=args.retries,
        timeout=args.timeout,
        backoff=args.backoff,
    )

    await parser.run(cities, args.output)


if __name__ == "__main__":
    asyncio.run(main())
