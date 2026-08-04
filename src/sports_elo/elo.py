from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from typing import Any


BASE_RATING = 1500.0


def expected_score(team_rating: float, opponent_rating: float) -> float:
    return 1 / (1 + 10 ** ((opponent_rating - team_rating) / 400))


def update_pair(home_rating: float, away_rating: float, home_score: int, away_score: int, k_factor: float, home_field: float) -> tuple[float, float]:
    expected_home = expected_score(home_rating + home_field, away_rating)
    if home_score > away_score:
        actual_home = 1.0
    elif home_score < away_score:
        actual_home = 0.0
    else:
        actual_home = 0.5
    return (
        round(home_rating + k_factor * (actual_home - expected_home), 1),
        round(away_rating + k_factor * ((1 - actual_home) - (1 - expected_home)), 1),
    )


def season_seed(previous_final: dict[str, float] | None = None, regression: float = 0.75) -> dict[str, float]:
    return {team: round(regression * rating + (1 - regression) * BASE_RATING, 1) for team, rating in (previous_final or {}).items()}


def checkpoint_key(game_date: str, granularity: str) -> str:
    parsed = date.fromisoformat(game_date)
    if granularity == "daily":
        return game_date
    iso = parsed.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def calculate_ratings(games: list[dict[str, Any]], *, k_factor: float, home_field: float, granularity: str, initial_ratings: dict[str, float] | None = None, initial_records: dict[str, dict[str, int]] | None = None, initial_metadata: dict[str, dict[str, str]] | None = None) -> dict[str, Any]:
    ratings: dict[str, float] = dict(initial_ratings or {})
    records: dict[str, dict[str, int]] = defaultdict(lambda: {"wins": 0, "losses": 0, "ties": 0}, **(initial_records or {}))
    metadata: dict[str, dict[str, str]] = dict(initial_metadata or {})
    history: list[dict[str, Any]] = []
    checkpoints: list[dict[str, Any]] = []
    last_key: str | None = None

    ordered = sorted(games, key=lambda game: (game["date"], game.get("start_time", ""), game["id"]))
    for game in ordered:
        key = checkpoint_key(game["date"], granularity)
        if last_key is not None and key != last_key:
            checkpoints.append(_snapshot(last_key, ratings, records, metadata))
        home, away = game["home_team"], game["away_team"]
        ratings.setdefault(home, BASE_RATING)
        ratings.setdefault(away, BASE_RATING)
        metadata[home] = {"name": game.get("home_name", home), "logo": game.get("home_logo", "")}
        metadata[away] = {"name": game.get("away_name", away), "logo": game.get("away_logo", "")}
        old_home, old_away = ratings[home], ratings[away]
        ratings[home], ratings[away] = update_pair(old_home, old_away, game["home_score"], game["away_score"], k_factor, home_field)
        if game["home_score"] > game["away_score"]:
            records[home]["wins"] += 1; records[away]["losses"] += 1
        elif game["home_score"] < game["away_score"]:
            records[away]["wins"] += 1; records[home]["losses"] += 1
        else:
            records[home]["ties"] += 1; records[away]["ties"] += 1

        last_key = key
    if last_key:
        checkpoints.append(_snapshot(last_key, ratings, records, metadata))
    for checkpoint in checkpoints:
        history.extend(checkpoint["teams"])
    current = sorted(checkpoints[-1]["teams"] if checkpoints else [], key=lambda row: row["rating"], reverse=True)
    for rank, row in enumerate(current, 1):
        row["rank"] = rank
    return {"current": current, "history": history, "checkpoints": checkpoints}


def replay_from_checkpoint(games: list[dict[str, Any]], previous: dict[str, Any], changed_from: str, *, k_factor: float, home_field: float, granularity: str) -> dict[str, Any]:
    """Recalculate only the affected checkpoint and everything after it."""
    affected_key = checkpoint_key(changed_from, granularity)
    prefix = [item for item in previous.get("checkpoints", []) if item["checkpoint"] < affected_key]
    seed = prefix[-1]["teams"] if prefix else []
    last_key = prefix[-1]["checkpoint"] if prefix else None
    initial_ratings = {row["team"]: row["rating"] for row in seed}
    initial_records = {row["team"]: {key: row[key] for key in ("wins", "losses", "ties")} for row in seed}
    initial_metadata = {row["team"]: {"name": row["name"], "logo": row.get("logo", "")} for row in seed}
    remaining = [game for game in games if last_key is None or checkpoint_key(game["date"], granularity) > last_key]
    tail = calculate_ratings(remaining, k_factor=k_factor, home_field=home_field, granularity=granularity, initial_ratings=initial_ratings, initial_records=initial_records, initial_metadata=initial_metadata)
    checkpoints = prefix + tail["checkpoints"]
    current = sorted(checkpoints[-1]["teams"] if checkpoints else [], key=lambda row: row["rating"], reverse=True)
    for rank, row in enumerate(current, 1):
        row["rank"] = rank
    return {"current": current, "history": [row for item in checkpoints for row in item["teams"]], "checkpoints": checkpoints}


def _snapshot(key: str, ratings: dict[str, float], records: dict[str, dict[str, int]], metadata: dict[str, dict[str, str]]) -> dict[str, Any]:
    teams = []
    for team, rating in ratings.items():
        record = records[team]
        teams.append({"checkpoint": key, "team": team, "name": metadata[team]["name"], "logo": metadata[team]["logo"], "rating": rating, **record})
    return {"checkpoint": key, "teams": sorted(teams, key=lambda row: row["rating"], reverse=True)}
