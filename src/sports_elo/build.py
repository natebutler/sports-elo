from __future__ import annotations

import argparse
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .store import load_ratings


def presentation(ratings: dict[str, Any]) -> dict[str, Any]:
    current = ratings.get("current", [])
    checkpoints = ratings.get("checkpoints", [])
    leader = current[0] if current else None
    spread = round(current[0]["rating"] - current[-1]["rating"], 1) if len(current) > 1 else 0
    mover = None
    if len(checkpoints) > 1:
        previous = {row["team"]: row["rating"] for row in checkpoints[-2]["teams"]}
        deltas = [(row["rating"] - previous.get(row["team"], row["rating"]), row) for row in current]
        if deltas:
            delta, row = max(deltas, key=lambda item: abs(item[0]))
            mover = {**row, "delta": round(delta, 1)}
    return {"ratings": ratings, "leader": leader, "spread": spread, "mover": mover}


def build(root: Path, season: int, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    assets_out = output / "assets"
    shutil.copytree(root / "assets", assets_out, dirs_exist_ok=True)
    league_data = {league: presentation(load_ratings(root, league, season)) for league in ("mlb", "nfl")}
    env = Environment(loader=FileSystemLoader(root / "templates"), autoescape=select_autoescape(["html", "xml"]))
    template = env.get_template("index.html")
    (output / "index.html").write_text(template.render(season=season, leagues=league_data, built_at=datetime.now(timezone.utc).strftime("%b %d, %Y %H:%M UTC")), encoding="utf-8")
    (output / ".nojekyll").write_text("", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Sports Elo static dashboard.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--output", type=Path, default=Path("docs"))
    args = parser.parse_args()
    build(args.root, args.season, args.output)


if __name__ == "__main__":
    main()
