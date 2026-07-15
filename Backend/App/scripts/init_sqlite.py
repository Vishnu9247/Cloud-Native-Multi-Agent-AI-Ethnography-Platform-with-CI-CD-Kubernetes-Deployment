from App.database_utils.sqlite_storage_service import DATABASE_PATH, ensure_database


def main() -> None:
    ensure_database()
    print(f"SQLite database initialized: {DATABASE_PATH}")


if __name__ == "__main__":
    main()
