from app import compare_players, create_app, get_default_players, player_draft_score, player_from_espn_record, search_active_players


def test_single_result_search_does_not_crash_on_comparison():
    app = create_app()

    response = app.test_client().get("/?search=Tuten&first=Christian+McCaffrey&second=CeeDee+Lamb")

    assert response.status_code == 200
    assert b"Bhayshul Tuten" in response.data


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
    assert b"0.0" not in response.data


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
