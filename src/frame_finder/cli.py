"""Module holding CLI entry point for search process."""

import logging
import argparse
import os
from pathlib import Path

from frame_finder.engine import RacquetSearchEngine
from frame_finder.config import EMBEDDING_MODEL_NAME
from frame_finder.adapters import AnthropicAdapter

import pandas as pd
from tabulate import tabulate
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

logging.getLogger("huggingface_hub").setLevel(logging.WARNING)
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(
    logging.WARNING
)  # new — httpx's own request logging, surfaced by this traceback

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_ROOT / "data" / "processed"

load_dotenv()


def parse_args() -> argparse.Namespace:
    """Adds argparse flags to CLI intialization allowing for disabling of LLM-based
    query parsing.

    Returns:
        argparse.Namespace: A boolean-acting object (True for skip, False for use LLM).
    """
    parser = argparse.ArgumentParser(description="Frame Finder search CLI")
    parser.add_argument(
        "--no-parse",
        "-n",
        action="store_true",
        help="Bypass LLM query parsing; use the raw query string for both semantic and keyword search.",
    )
    return parser.parse_args()


def display_results(
    fused_results: list[tuple[str, float]], racquet_df: pd.DataFrame, top_n: int = 15
) -> None:
    """Displays a tabulate-styled table of the Rank, Name, Price, Rating, and RRF score for each of the
    top_n returned racquets from the RRF search method.

    Args:
        fused_results (list[tuple[str, float]]): The tuple of racquet_id, RRF score pairs sorted in descending order
        racquet_df (pd.DataFrame): The canonical racquet dataset loaded as a pandas DataFrame
        top_n (int, optional): How many top items to dispaly. Defaults to 15.
    """

    table_rows = []

    for rank, (racquet_id, score) in enumerate(fused_results[:top_n], start=1):
        row = racquet_df[racquet_df["racquet_id"] == racquet_id]

        if row.empty:
            table_rows.append(
                [rank, f"[unknown id: {racquet_id}]", "null", "null", f"{score:.4f}"]
            )
            continue

        row = row.iloc[0]
        price = (
            f"${row["racquet_price"]:.2f}" if pd.notna(row["racquet_price"]) else "null"
        )
        rating = row["racquet_rating"] if pd.notna(row["racquet_rating"]) else "null"

        table_rows.append([rank, row["racquet_name"], price, rating, f"{score:.4f}"])

    print(
        tabulate(table_rows, headers=["Rank", "Name", "Price", "Rating", "RRF Score"])
    )


def main() -> None:
    """The main orchestration function. Parses args, initiates adapter and engine, sets up engine, runs search with tabulate displays
    in a while loop until broken.

    Returns:
        None: Returns nothing, only runs through search process.
    """
    args = parse_args()

    terminal_width = os.get_terminal_size().columns
    print("=" * (terminal_width - 1))
    print(
        "Welcome to Frame Finder CLI. Please wait while the search engine initiates.",
        flush=True,
    )

    if args.no_parse:
        print(
            "Query parsing disabled - raw query will be used for both BM25 and semantic search.\n"
        )

    anthropic_adapter = AnthropicAdapter()
    engine = RacquetSearchEngine(
        path_to_artifacts=ARTIFACTS_DIR,
        embedder_name=EMBEDDING_MODEL_NAME,
        llm_adapter=anthropic_adapter,
    )

    logger.info("Creating and setting up search engine...")
    engine.setup()
    logger.info("Engine created and set up. Search capabilities ready.")

    print("Frame Finder CLI - enter a query, or 'quit' to exit.\n")

    while True:
        query = input("\nWhat type of racquet are you looking for?\n").strip()

        if query.lower() in ("quit", "exit", "q"):
            print("Thank you for using Frame Finder. Goodbye.")
            break

        if not query:
            continue

        search_result = (
            engine.search(query=query, skip_parsing=args.no_parse)
        ).fused_result
        display_results(search_result, engine.racquet_df, top_n=15)

    print("=" * (terminal_width - 1))


if __name__ == "__main__":
    main()
