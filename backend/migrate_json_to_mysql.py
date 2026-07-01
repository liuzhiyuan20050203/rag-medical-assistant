from pathlib import Path

from storage import ensure_json_store, is_database_enabled, migrate_local_json_file


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

JSON_FILES = {
    "diseases.json": list,
    "medicines.json": list,
    "warning_rules.json": list,
    "history.json": list,
    "users.json": list,
    "sessions.json": dict,
    "search_log.json": list,
}


def main():
    if not is_database_enabled():
        raise SystemExit("DATABASE_URL or MYSQL_HOST is required before running migration.")

    ensure_json_store()

    for file_name, default_factory in JSON_FILES.items():
        file_path = DATA_DIR / file_name
        key, _data = migrate_local_json_file(file_path, default_factory)
        print(f"migrated {file_name} -> key '{key}'")

    print("migration complete")


if __name__ == "__main__":
    main()
