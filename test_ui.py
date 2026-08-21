from __future__ import annotations

import json
import os
from threading import Thread
from urllib.parse import urlencode

import pytest
from werkzeug.serving import make_server

playwright_sync = pytest.importorskip("playwright.sync_api")
from playwright.sync_api import Page, sync_playwright

from app import create_app


BASE_URL = "http://127.0.0.1"


@pytest.fixture
def ui_page() -> Page:
    app = create_app()
    server = make_server("127.0.0.1", 0, app)
    server_thread = Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    base_url = f"{BASE_URL}:{server.server_port}"

    with sync_playwright() as playwright:
        headed = os.getenv("PLAYWRIGHT_HEADED", "0") == "1"
        browser = playwright.chromium.launch(headless=not headed)
        context = browser.new_context(base_url=base_url)
        page = context.new_page()
        _mock_browser_apis(page)
        try:
            yield page
        finally:
            context.close()
            browser.close()
            server.shutdown()
            server_thread.join(timeout=5)


def _mock_browser_apis(page: Page) -> None:
    fixtures = {
        "**/news*": [
            {"headline": "Mock NFL headline", "source": "Test Wire", "link": ""}
        ],
        "**/games*": [
            {"season_label": "2026", "matchup": "KC at BUF", "kickoff": "Sun 1:00 PM"}
        ],
        "**/trending*": [
            {
                "rank": 1,
                "name": "Patrick Mahomes",
                "position": "QB",
                "team": "KC",
                "trend_count": 42,
                "headshot_url": "",
            }
        ],
        "**/injuries*": [
            {
                "name": "Patrick Mahomes",
                "position": "QB",
                "team": "KC",
                "status": "Questionable",
                "comment": "Limited practice",
                "source_url": "https://example.com/injury",
            }
        ],
        "**/suggest*": [
            {
                "name": "Patrick Mahomes",
                "position": "QB",
                "team": "KC",
                "value": "Patrick Mahomes|QB|KC",
                "headshot_url": "",
            }
        ],
    }
    sleeper_payload = {
        "league_name": "Manual League",
        "league_id": "456",
        "team_count": 0,
        "total_points": 0,
        "average_points": 0,
        "teams": [],
    }

    def fulfill_json(payload):
        def handler(route):
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(payload),
            )

        return handler

    for route, payload in fixtures.items():
        page.route(route, fulfill_json(payload))
    page.route("**/sleeper-analytics", fulfill_json(sleeper_payload))


def test_home_page_shows_brand_and_player_search(ui_page: Page) -> None:
    ui_page.goto("/")

    assert ui_page.title() == "The Lab"
    assert ui_page.locator(".brand").inner_text().casefold() == "the lab"
    assert ui_page.locator("#search").is_visible()
    assert ui_page.locator("button[type='submit']").filter(has_text="Search").is_visible()
    ui_page.locator("#sports-ticker-track").get_by_text("KC at BUF").wait_for(state="visible")


def test_player_search_shows_suggestions_and_locks_player(ui_page: Page) -> None:
    ui_page.goto("/")
    ui_page.locator("#search").fill("Mahomes")

    suggestion = ui_page.locator(".suggestion-item").filter(has_text="Patrick Mahomes")
    suggestion.wait_for(state="visible")
    suggestion.click()

    assert "selected=Patrick+Mahomes%7CQB%7CKC" in ui_page.url
    selected_count = ui_page.locator(".selected-panel .selection-count")
    selected_count.wait_for(state="visible")
    assert "1 / 2" in selected_count.inner_text()


def test_news_trending_and_injury_menus_load_content(ui_page: Page) -> None:
    ui_page.goto("/")

    ui_page.locator("#trending-toggle").hover()
    ui_page.locator("#trending-menu").wait_for(state="visible")
    assert ui_page.locator(".trending-name").inner_text().casefold() == "patrick mahomes"

    ui_page.locator("#injury-toggle").hover()
    ui_page.locator("#injury-menu").wait_for(state="visible")
    assert ui_page.locator(".injury-player").count() or ui_page.locator(".injury-item").count()

    ui_page.locator("#top-news-toggle").hover()
    ui_page.locator("#top-news-menu").wait_for(state="visible")
    assert ui_page.locator("#top-news-menu").get_by_text("Mock NFL headline").is_visible()


def test_nfl_teams_menu_lists_team_links(ui_page: Page) -> None:
    ui_page.goto("/")
    ui_page.locator("#teams-toggle").hover()
    ui_page.locator("#teams-menu").wait_for(state="visible")

    team_link = ui_page.locator("#teams-menu a[href*='team=KC']")
    assert team_link.count() == 1
    assert "chiefs" in team_link.inner_text().casefold()


def test_manual_sleeper_league_id_loads_analytics(ui_page: Page) -> None:
    ui_page.goto("/")
    ui_page.locator("#sleeper-toggle").hover()
    ui_page.locator("#sleeper-menu").wait_for(state="visible")
    ui_page.locator("#league-id").fill("456")
    ui_page.locator("#sleeper-upload button[type='submit']").click()

    ui_page.wait_for_function(
        "document.querySelector('#sleeper-upload-status')?.textContent.trim().toLowerCase() === 'analytics updated.'"
    )
    assert ui_page.locator("#sleeper-upload-status").inner_text().casefold() == "analytics updated.".casefold()
    assert ui_page.locator("#sleeper-results").get_by_text("Manual League").is_visible()


def test_two_selected_players_expose_compare_action(ui_page: Page) -> None:
    query = urlencode(
        [
            ("selected", "Christian McCaffrey|RB|SF"),
            ("selected", "Patrick Mahomes|QB|KC"),
        ]
    )
    ui_page.goto(f"/?{query}")

    compare_button = ui_page.locator(".compare-action")
    assert compare_button.is_visible()
    assert compare_button.inner_text().casefold().startswith("compare trade")
    selected_items = ui_page.locator(".selected-panel .selected-item")
    assert selected_items.count() == 2
    assert all(item.is_visible() for item in selected_items.all())


def test_search_surface_stays_compact_on_mobile(ui_page: Page) -> None:
    ui_page.set_viewport_size({"width": 390, "height": 844})
    ui_page.goto("/")

    search_surface = ui_page.locator(".search-surface")
    box = search_surface.bounding_box()
    assert box is not None
    assert box["width"] <= 390
    assert search_surface.locator("#search").is_visible()