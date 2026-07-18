"""Load external JSON data used by automated tests."""
import json
from pathlib import Path
from typing import Any


TESTS_DIRECTORY = Path(__file__).resolve().parents[1]
FIXTURES_DIRECTORY = TESTS_DIRECTORY / "fixtures"


def load_test_fixture(file_name: str) -> dict[str, Any]:
    """Load one JSON fixture file from the tests fixture directory."""
    fixture_path = FIXTURES_DIRECTORY / file_name
    return json.loads(fixture_path.read_text(encoding="utf-8"))