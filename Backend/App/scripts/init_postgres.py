from App.database_utils.postgres_service import (
    create_database_if_needed,
    ensure_database,
)


def main() -> None:
    create_database_if_needed()
    ensure_database()
    print("Postgres database initialized.")


if __name__ == "__main__":
    main()
