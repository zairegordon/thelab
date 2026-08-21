from io import BytesIO

import app
from app import compare_players, create_app, get_default_players, player_draft_score, player_from_espn_record, search_active_players, sleeper_projected_points


def test_sleeper_analytics_upload_uses_league_wrapper(monkeypatch):
    class FakeLeague:
        def __init__(self, league_id):
            assert league_id == "123"

        def get_league(self):
            return {"name": "Test League"}

        def get_rosters(self):
            return [{
                "owner_id": "u1",
                "players": ["p1", "p2"],
                "starters": ["p1"],
                "settings": {"wins": 3, "losses": 1, "fpts": 100.5, "total_moves": 4},
            }]

        def get_users(self):
            return [{"user_id": "u1"}]

        def map_users_to_team_name(self, users):
            return {"u1": "Team One"}

        def get_standings(self, rosters, users):
            return [("Team One", "3", "1", "100.5")]

        def get_league_name(self):
            return "Test League"

    monkeypatch.setattr("app.SleeperLeague", FakeLeague)
    response = create_app().test_client().post(
        "/sleeper-analytics",
        data={"league_file": (BytesIO(b'{"league_id":"123"}'), "league.json")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert response.get_json()["teams"][0]["name"] == "Team One"


def test_sleeper_analytics_accepts_manual_league_id(monkeypatch):
    class FakeLeague:
        def __init__(self, league_id):
            assert league_id == "456"

        def get_league(self):
            return {"name": "Manual League"}

        def get_rosters(self):
            return []

        def get_users(self):
            return []

        def get_standings(self, rosters, users):
            return []

        def map_users_to_team_name(self, users):
            return {}

        def get_league_name(self):
            return "Manual League"

    monkeypatch.setattr("app.SleeperLeague", FakeLeague)
    response = create_app().test_client().post(
        "/sleeper-analytics",
        data={"league_id": "456"},
    )

    assert response.status_code == 200
    assert response.get_json()["league_name"] == "Manual League"


def test_trade_comparison_exposes_point_calculations(monkeypatch):
    projections = {
        "George Pickens": {"season": 220.0, "per_game": 14.7, "position_rank": 18, "source": "Sleeper 2026 projection"},
        "CeeDee Lamb": {"season": 290.0, "per_game": 19.3, "position_rank": 2, "source": "Sleeper 2026 projection"},
    }
    monkeypatch.setattr("app.sleeper_projected_points", lambda name, fallback: projections[name])
    players = get_default_players()
    player_a = next(player for player in players if player.name == "CeeDee Lamb")
    player_b = players[0]
    player_b.name = "George Pickens"

    comparison = compare_players(player_a, player_b)

    assert comparison["winner"] == "CeeDee Lamb"
    assert comparison["player_a"]["projected_points"] == 290.0
    assert comparison["player_b"]["projected_points_per_game"] == 14.7
    assert comparison["player_a"]["position_rank"] == 2
    assert comparison["player_b"]["position_rank"] == 18


def test_sleeper_projection_uses_half_ppr_and_games_played(monkeypatch):
    class FakePlayers:
        def get_all_players(self, sport):
            return {
                "p1": {"first_name": "Test", "last_name": "Player", "position": "WR"},
                "p2": {"first_name": "Other", "last_name": "Receiver", "position": "WR"},
            }

    class FakeStats:
        def get_all_projections(self, season_type, season):
            return {
                "p1": {"pts_half_ppr": 240.0, "pts_ppr": 260.0, "pts_std": 220.0, "gp": 16.0},
                "p2": {"pts_half_ppr": 200.0, "gp": 17.0},
            }

    monkeypatch.setattr("app.SleeperPlayers", FakePlayers)
    monkeypatch.setattr("app.SleeperStats", FakeStats)
    monkeypatch.setenv("SLEEPER_PROJECTIONS_ENABLED", "1")
    app._SLEEPER_DIRECTORY_CACHE["players"] = {}
    app._SLEEPER_DIRECTORY_CACHE["fetched_at"] = 0
    app._SLEEPER_PROJECTION_CACHE["players"] = {}
    app._SLEEPER_PROJECTION_CACHE["season"] = ""
    app._SLEEPER_PROJECTION_CACHE["fetched_at"] = 0

    projection = sleeper_projected_points("Test Player", 100.0)

    assert projection["season"] == 240.0
    assert projection["games"] == 16.0
    assert projection["per_game"] == 15.0
    assert projection["source"] == "Sleeper 2026 half-PPR projection"


def test_search_page_shows_selection_surface_without_results_section():
    app = create_app()

    response = app.test_client().get("/?search=Tuten&first=Christian+McCaffrey&second=CeeDee+Lamb")

    assert response.status_code == 200
    assert b"Selected players" in response.data
    assert b"Search results" not in response.data


def test_selected_player_list_can_be_compared():
    app = create_app()

    response = app.test_client().get(
        "/?search=allen&selected=Patrick+Mahomes%7CQB%7CKC&selected=Joe+Burrow%7CQB%7BCIN&compare=true"
    )

    assert response.status_code == 200
    assert b"Patrick Mahomes" in response.data
    assert b"Joe Burrow" in response.data
    assert b"Winner" in response.data


def test_selected_players_persist_across_different_searches():
    app = create_app()

    response = app.test_client().get(
        "/?search=mahomes&selected=Josh+Allen%7CQB%7CBUF&selected=Patrick+Mahomes%7CQB%7CKC"
    )

    assert response.status_code == 200
    assert b"Josh Allen" in response.data
    assert b"Patrick Mahomes" in response.data
    assert b"Selected players" in response.data


def test_search_active_players_uses_team_rosters(monkeypatch):
    class FakeResponse:
        def __init__(self, payload):
            self.payload = payload

        def json(self):
            return self.payload

        def raise_for_status(self):
            return None

    def fake_get(url, timeout=20):
        if url.endswith("/teams"):
            return FakeResponse({
                "sports": [{
                    "leagues": [{
                        "teams": [{
                            "team": {"id": "12", "abbreviation": "KC", "displayName": "Kansas City Chiefs"}
                        }]
                    }]
                }]
            })
        if url.endswith("/roster"):
            return FakeResponse({
                "athletes": [{
                    "position": "offense",
                    "items": [{
                        "fullName": "Patrick Mahomes",
                        "displayPosition": {"name": "QB"},
                        "team": {"abbreviation": "KC"},
                    }]
                }]
            })
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr("app.requests.get", fake_get)
    monkeypatch.setattr("app.get_cached_active_players", lambda year=2026: app._fetch_all_active_players(year))
    app._ROSTER_CACHE["players"] = []
    app._ROSTER_CACHE["fetched_at"] = 0
    app._PLAYER_SEARCH_CACHE.clear()

    results = search_active_players("Mahomes")

    assert results[0].name == "Patrick Mahomes"
    assert results[0].team == "KC"
    assert results[0].position == "QB"


def test_player_from_espn_record_maps_api_data():
    api_record = {
        "name": "Ja'Marr Chase",
        "position": "WR",
        "team": "CIN",
        "projected_points": 245.0,
        "floor": 180.0,
        "ceiling": 300.0,
        "bye_week": 6,
    }

    player = player_from_espn_record(api_record)

    assert player.name == "Ja'Marr Chase"
    assert player.position == "WR"
    assert player.projected_points == 245.0
    assert player.bye_week == 6


def test_get_default_players_returns_draft_pool():
    players = get_default_players()

    assert len(players) >= 5
    assert {player.name for player in players} >= {
        "Christian McCaffrey",
        "CeeDee Lamb",
        "Jalen Hurts",
    }


def test_player_draft_score_ranks_top_value():
    players = get_default_players()
    scores = {player.name: player_draft_score(player) for player in players}

    assert scores["Christian McCaffrey"] > scores["Jalen Hurts"]
    assert scores["CeeDee Lamb"] > scores["Sam LaPorta"]


def test_compare_players_reports_clear_winner():
    players = get_default_players()
    christian = next(player for player in players if player.name == "Christian McCaffrey")
    jalen = next(player for player in players if player.name == "Jalen Hurts")

    result = compare_players(christian, jalen)

    assert result["winner"] == "Christian McCaffrey"
    assert result["score_gap"] > 0
    assert result["category_winner"]["projected_points"] == "Christian McCaffrey"
