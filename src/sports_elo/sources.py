from __future__ import annotations

import json
from datetime import date
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


USER_AGENT = "sports-elo-dashboard/1.0 (+https://github.com)"


def _get_json(url: str) -> dict[str, Any]:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urlopen(request, timeout=30) as response:  # nosec B310 - fixed public APIs
        return json.loads(response.read().decode("utf-8"))


def fetch_games(league: str, game_date: date) -> list[dict[str, Any]]:
    if league == "mlb":
        return _fetch_mlb(game_date)
    if league == "nfl":
        return _fetch_nfl(game_date)
    raise ValueError(f"Unsupported league: {league}")


def _fetch_mlb(game_date: date) -> list[dict[str, Any]]:
    query = urlencode({"sportId": 1, "date": game_date.isoformat(), "hydrate": "linescore"})
    payload = _get_json(f"https://statsapi.mlb.com/api/v1/schedule?{query}")
    games: list[dict[str, Any]] = []
    for day in payload.get("dates", []):
        for game in day.get("games", []):
            status = game.get("status", {})
            if status.get("abstractGameState") != "Final":
                continue
            home, away = game["teams"]["home"], game["teams"]["away"]
            home_team, away_team = home["team"], away["team"]
            games.append({
                "id": f"mlb-{game['gamePk']}", "date": game["officialDate"], "start_time": game.get("gameDate", ""),
                "home_team": str(home_team["id"]), "away_team": str(away_team["id"]),
                "home_name": home_team["name"], "away_name": away_team["name"],
                "home_logo": "", "away_logo": "", "home_score": int(home["score"]), "away_score": int(away["score"]),
            })
    return games


def _fetch_nfl(game_date: date) -> list[dict[str, Any]]:
    payload = _get_json(
        "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?"
        + urlencode({"dates": game_date.strftime("%Y%m%d"), "limit": 1000})
    )
    games: list[dict[str, Any]] = []
    for event in payload.get("events", []):
        if not event.get("status", {}).get("type", {}).get("completed"):
            continue
        competition = event["competitions"][0]
        competitors = {item["homeAway"]: item for item in competition["competitors"]}
        home, away = competitors["home"], competitors["away"]
        home_team, away_team = home["team"], away["team"]
        games.append({
            "id": f"nfl-{event['id']}", "date": event["date"][:10], "start_time": event["date"],
            "home_team": home_team["abbreviation"], "away_team": away_team["abbreviation"],
            "home_name": home_team["displayName"], "away_name": away_team["displayName"],
            "home_logo": (home_team.get("logos") or [{}])[0].get("href", ""),
            "away_logo": (away_team.get("logos") or [{}])[0].get("href", ""),
            "home_score": int(home["score"]), "away_score": int(away["score"]),
        })
    return games
