from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .config import get_league_config
from .elo import calculate_ratings, replay_from_checkpoint, season_seed
from .sources import fetch_games
from .store import load_games, load_ratings, load_state, save_games, save_ratings, save_state


def daterange(start: date, end: date):
    while start <= end:
        yield start
        start += timedelta(days=1)


def upsert_games(existing: list[dict[str, Any]], incoming: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str | None]:
    by_id = {game["id"]: game for game in existing}
    changed_dates: list[str] = []
    for game in incoming:
        if by_id.get(game["id"]) != game:
            changed_dates.append(game["date"])
            by_id[game["id"]] = game
    return sorted(by_id.values(), key=lambda game: (game["date"], game.get("start_time", ""), game["id"])), min(changed_dates, default=None)


def run_league(root: Path, league: str, season: int, today: date | None = None) -> dict[str, Any]:
    today = today or date.today()
    config = get_league_config(league, season)
    state, existing = load_state(root, league, season), load_games(root, league, season)
    last_checked = date.fromisoformat(state["last_checked"]) if state.get("last_checked") else config.season_start - timedelta(days=1)
    start = max(config.season_start, last_checked - timedelta(days=config.repair_days - 1))
    incoming: list[dict[str, Any]] = []
    for game_day in daterange(start, today):
        incoming.extend(fetch_games(league, game_day))
    games, changed_from = upsert_games(existing, incoming)
    save_games(root, league, season, games)
    previous = load_ratings(root, league, season)
    if not changed_from and previous.get("checkpoints"):
        ratings = previous
    elif previous.get("checkpoints") and changed_from:
        ratings = replay_from_checkpoint(games, previous, changed_from, k_factor=config.k_factor, home_field=config.home_field, granularity=config.checkpoint)
    else:
        prior_season = load_ratings(root, league, season - 1)
        prior_final = {row["team"]: row["rating"] for row in prior_season.get("current", [])}
        ratings = calculate_ratings(games, k_factor=config.k_factor, home_field=config.home_field, granularity=config.checkpoint, initial_ratings=season_seed(prior_final))
    ratings.update({"league": league, "season": season, "generated_at": datetime.now(timezone.utc).isoformat(), "changed_from": changed_from})
    save_ratings(root, league, season, ratings)
    save_state(root, league, season, {"last_checked": today.isoformat(), "last_changed_from": changed_from, "game_count": len(games), "updated_at": ratings["generated_at"]})
    return {"league": league, "season": season, "fetched_from": start.isoformat(), "changed_from": changed_from, "games": len(games)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Incrementally refresh Sports Elo data.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--season", type=int, default=date.today().year)
    parser.add_argument("--league", choices=["mlb", "nfl", "all"], default="all")
    args = parser.parse_args()
    leagues = ("mlb", "nfl") if args.league == "all" else (args.league,)
    for league in leagues:
        print(run_league(args.root, league, args.season))


if __name__ == "__main__":
    main()
