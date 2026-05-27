"""Command-line entrypoint for Tsuzuri."""

import argparse
import asyncio

from tsuzuri.config import RuntimeConfig
from tsuzuri.pipeline import MinimalPipeline


def main() -> None:
    """Run the CLI."""
    parser = argparse.ArgumentParser(prog="tsuzuri")
    subparsers = parser.add_subparsers(dest="command")
    run_parser = subparsers.add_parser("run", help="run the minimal local pipeline")
    run_parser.add_argument("query", help="research query")
    args = parser.parse_args()

    if args.command != "run":
        print("tsuzuri: pipeline implementation is in progress")
        return

    result = asyncio.run(MinimalPipeline(RuntimeConfig.from_env()).run(args.query))
    print(f"run_id: {result.run_id}")
    print(f"run_dir: {result.run_dir}")
    print(f"search_results: {result.search_result_count}")
    print(f"filtered_urls: {result.filtered_url_count}")
    print(f"extracted_documents: {result.extracted_document_count}")
    print(f"failed_fetches: {result.failed_fetch_count}")
    print(f"map_summaries: {result.map_summary_count}")
    if result.final_report_path is not None:
        print(f"final_report: {result.final_report_path}")
    for warning in result.warnings:
        print(f"warning: {warning}")


if __name__ == "__main__":
    main()
