# Sports Elo

A static, interactive MLB and NFL Elo dashboard built in Python and published with GitHub Pages.

## Local use

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
python -m sports_elo.update --season 2026
python -m sports_elo.build --season 2026 --output docs
```

The first update hydrates the current season. Later updates re-request only a three-day repair window after the saved `state.json` watermark, upsert changed games, and replay ratings from the prior daily/weekly checkpoint.

## Publish

Create `natebutler/sports-elo`, push this directory's `main` branch, and select **GitHub Actions** as the repository's Pages source. The included workflow refreshes data daily at 10:00 UTC and deploys the generated dashboard.

`data/<league>/<season>/games.json` contains normalized game records; `ratings.json` holds compact rating checkpoints; `state.json` records the incremental ingestion watermark. These files are committed so GitHub Actions always resumes safely without relying on an external database or a cache.
