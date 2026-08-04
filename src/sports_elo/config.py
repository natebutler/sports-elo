from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class LeagueConfig:
    key: str
    name: str
    k_factor: float
    home_field: float
    season_start: date
    checkpoint: str
    repair_days: int = 3


def get_league_config(league: str, season: int) -> LeagueConfig:
    if league == "mlb":
        return LeagueConfig("mlb", "MLB", 7, 0, date(season, 3, 1), "daily")
    if league == "nfl":
        return LeagueConfig("nfl", "NFL", 25, 40, date(season, 9, 1), "weekly")
    raise ValueError(f"Unsupported league: {league}")
