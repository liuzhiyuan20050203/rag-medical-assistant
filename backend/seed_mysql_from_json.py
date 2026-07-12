import argparse
import json
from pathlib import Path

from storage import db_key_exists, ensure_json_store, is_database_enabled, save_db_json


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

JSON_FILES = [
    "diseases.json",
    "medicines.json",
    "warning_rules.json",
    "history.json",
    "users.json",
    "sessions.json",
    "search_log.json",
]


def read_json(file_path: Path):
    if not file_path.exists():
        return {} if file_path.name == "sessions.json" else []

    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def seed_file(file_name: str, overwrite: bool = False):
    file_path = DATA_DIR / file_name
    key = file_path.stem

    if db_key_exists(key) and not overwrite:
        return key, "skipped"

    save_db_json(key, read_json(file_path))
    return key, "overwritten" if overwrite else "created"


def main():
    parser = argparse.ArgumentParser(
        description="Seed MySQL app_json_store from backend/data JSON files."
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing keys in MySQL instead of skipping them.",
    )
    args = parser.parse_args()

    if not is_database_enabled():
        raise SystemExit("MySQL is not enabled. Please configure MYSQL_* in backend/.env first.")

    ensure_json_store()

    for file_name in JSON_FILES:
        key, status = seed_file(file_name, overwrite=args.overwrite)
        print(f"{status}: {file_name} -> key '{key}'")

    print("seed complete")


if __name__ == "__main__":
    main()
