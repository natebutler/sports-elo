from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def season_dir(root: Path, league: str, season: int) -> Path:
    return root / "data" / league / str(season)


def load_games(root: Path, league: str, season: int) -> list[dict[str, Any]]:
    return read_json(season_dir(root, league, season) / "games.json", [])


def save_games(root: Path, league: str, season: int, games: list[dict[str, Any]]) -> None:
    write_json(season_dir(root, league, season) / "games.json", games)


def load_state(root: Path, league: str, season: int) -> dict[str, Any]:
    return read_json(season_dir(root, league, season) / "state.json", {})


def save_state(root: Path, league: str, season: int, state: dict[str, Any]) -> None:
    write_json(season_dir(root, league, season) / "state.json", state)


def load_ratings(root: Path, league: str, season: int) -> dict[str, Any]:
    return read_json(season_dir(root, league, season) / "ratings.json", {})


def save_ratings(root: Path, league: str, season: int, ratings: dict[str, Any]) -> None:
    write_json(season_dir(root, league, season) / "ratings.json", ratings)
