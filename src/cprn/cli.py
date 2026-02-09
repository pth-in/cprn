import argparse
import asyncio
import sys
from supabase import create_client

from cprn.core.config import SUPABASE_URL, SUPABASE_KEY
from cprn.scavengers.news_ingest import NewsIngester
from cprn.scavengers.social_ingest import SocialIngester

def main():
    parser = argparse.ArgumentParser(description="CPRN Ingestion Pipeline CLI")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Ingest News Command
    ingest_parser = subparsers.add_parser("ingest", help="Ingest news from RSS and NGO sites")
    ingest_parser.add_argument("--days", type=int, default=7, help="Days to look back (default: 7)")
    ingest_parser.add_argument("--limit", type=int, default=None, help="Limit number of incidents to process")

    # Social Media Command
    social_parser = subparsers.add_parser("social", help="Ingest social media updates (X)")
    social_parser.add_argument("--days", type=int, default=7, help="Days to look back (default: 7)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if not SUPABASE_URL or not SUPABASE_KEY:
        print("Error: SUPABASE_URL or SUPABASE_SECRET_KEY environment variables not set.")
        sys.exit(1)

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    if args.command == "ingest":
        ingester = NewsIngester(supabase)
        ingester.run(days_lookback=args.days, limit=args.limit)
    elif args.command == "social":
        ingester = SocialIngester(supabase)
        asyncio.run(ingester.run(days_lookback=args.days))

if __name__ == "__main__":
    main()
