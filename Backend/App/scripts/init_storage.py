import argparse
import os

from App.database_utils.postgres_service import (
    create_database_if_needed,
    ensure_database,
)
from App.rag_utils.chroma_service import create_vector_store, ensure_chroma_ready


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--session-id",
        default=os.getenv("SESSION_ID", ""),
        help="Optional session id to create as a Chroma collection.",
    )
    args = parser.parse_args()

    create_database_if_needed()
    ensure_database()
    ensure_chroma_ready()

    if args.session_id:
        create_vector_store(args.session_id)

    print("Postgres and Chroma storage initialized.")


if __name__ == "__main__":
    main()
