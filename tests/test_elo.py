import unittest
from datetime import date
from tempfile import TemporaryDirectory
from unittest.mock import patch

from sports_elo.elo import calculate_ratings, expected_score, replay_from_checkpoint, season_seed, update_pair
from sports_elo.sources import _score
from sports_elo.update import run_league, upsert_games


def game(game_id, played, home="A", away="B", home_score=1, away_score=0):
    return {"id": game_id, "date": played, "start_time": f"{played}T20:00:00Z", "home_team": home, "away_team": away, "home_name": home, "away_name": away, "home_logo": "", "away_logo": "", "home_score": home_score, "away_score": away_score}


class EloTests(unittest.TestCase):
    def test_missing_api_score_is_rejected(self):
        self.assertIsNone(_score(None))
        self.assertIsNone(_score(""))
        self.assertIsNone(_score("TBD"))
        self.assertEqual(_score("12"), 12)

    def test_expected_score_is_balanced(self):
        self.assertEqual(expected_score(1500, 1500), 0.5)

    def test_home_field_changes_expected_outcome(self):
        home, away = update_pair(1500, 1500, 1, 0, 25, 40)
        self.assertGreater(home, 1500)
        self.assertLess(away, 1500)
        self.assertLess(home - 1500, 12.5)

    def test_season_seed_regresses_to_mean(self):
        self.assertEqual(season_seed({"A": 1600}, .75), {"A": 1575.0})

    def test_upsert_is_idempotent_and_detects_correction(self):
        original = game("one", "2026-03-30")
        games, changed = upsert_games([], [original])
        self.assertEqual(changed, "2026-03-30")
        games, changed = upsert_games(games, [original])
        self.assertIsNone(changed)
        corrected = {**original, "home_score": 2}
        _, changed = upsert_games(games, [corrected])
        self.assertEqual(changed, "2026-03-30")

    def test_replay_from_changed_checkpoint_matches_full_rebuild(self):
        games = [game("one", "2026-03-30"), game("two", "2026-03-31", "B", "A", 1, 0), game("three", "2026-04-01", "A", "B", 1, 0)]
        prior = calculate_ratings(games, k_factor=7, home_field=0, granularity="daily")
        corrected = [{**item, "home_score": 2} if item["id"] == "two" else item for item in games]
        replayed = replay_from_checkpoint(corrected, prior, "2026-03-31", k_factor=7, home_field=0, granularity="daily")
        full = calculate_ratings(corrected, k_factor=7, home_field=0, granularity="daily")
        self.assertEqual(replayed["current"], full["current"])

    def test_incremental_run_reuses_state_and_accepts_correction(self):
        with TemporaryDirectory() as temporary:
            root = __import__("pathlib").Path(temporary)
            first = game("one", "2026-03-01")
            with patch("sports_elo.update.fetch_games", return_value=[first]) as fetch:
                result = run_league(root, "mlb", 2026, date(2026, 3, 1))
                self.assertEqual(result["games"], 1)
                self.assertEqual(fetch.call_count, 1)
            with patch("sports_elo.update.fetch_games", return_value=[first]):
                result = run_league(root, "mlb", 2026, date(2026, 3, 1))
                self.assertIsNone(result["changed_from"])
            corrected = {**first, "home_score": 2}
            with patch("sports_elo.update.fetch_games", return_value=[corrected]):
                result = run_league(root, "mlb", 2026, date(2026, 3, 1))
                self.assertEqual(result["changed_from"], "2026-03-01")
