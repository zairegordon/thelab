"""Fantasy football draft comparison app."""

from __future__ import annotations

import base64
import importlib
import io
import os
import re
import time
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import requests
from flask import Flask, jsonify, render_template, request

# Optional native data libraries are loaded lazily and only when explicitly enabled,
# because some builds can crash on unsupported CPUs before Flask starts.
ENABLE_OPTIONAL_PLAYER_DATA = os.getenv("ENABLE_OPTIONAL_PLAYER_DATA", "0") == "1"


def _load_optional_module(module_name: str):
    if not ENABLE_OPTIONAL_PLAYER_DATA:
        return None
    try:
        return importlib.import_module(module_name)
    except Exception:
        return None

try:
    from ff_espn_api import League
except Exception:  # pragma: no cover - optional dependency for local data access
    League = None

import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt

try:
    import fantasyfootball  # type: ignore
except Exception:  # pragma: no cover - optional package for matchup intel
    fantasyfootball = None

try:
    from sleeper_wrapper import Players as SleeperPlayers
except Exception:  # pragma: no cover - optional package for trending data
    SleeperPlayers = None

_SLEEPER_DIRECTORY_CACHE = {"players": {}, "fetched_at": 0}
_SLEEPER_DIRECTORY_CACHE_TTL = 24 * 60 * 60


NFL_TEAMS = [
    {"abbr": "ARI", "name": "Arizona Cardinals", "label": "Cardinals", "logo": "https://a.espncdn.com/i/teamlogos/nfl/500/ari.png"},
    {"abbr": "ATL", "name": "Atlanta Falcons", "label": "Falcons", "logo": "https://a.espncdn.com/i/teamlogos/nfl/500/atl.png"},
    {"abbr": "BAL", "name": "Baltimore Ravens", "label": "Ravens", "logo": "https://a.espncdn.com/i/teamlogos/nfl/500/bal.png"},
    {"abbr": "BUF", "name": "Buffalo Bills", "label": "Bills", "logo": "https://a.espncdn.com/i/teamlogos/nfl/500/buf.png"},
    {"abbr": "CAR", "name": "Carolina Panthers", "label": "Panthers", "logo": "https://a.espncdn.com/i/teamlogos/nfl/500/car.png"},
    {"abbr": "CHI", "name": "Chicago Bears", "label": "Bears", "logo": "https://a.espncdn.com/i/teamlogos/nfl/500/chi.png"},
    {"abbr": "CIN", "name": "Cincinnati Bengals", "label": "Bengals", "logo": "https://a.espncdn.com/i/teamlogos/nfl/500/cin.png"},
    {"abbr": "CLE", "name": "Cleveland Browns", "label": "Browns", "logo": "https://a.espncdn.com/i/teamlogos/nfl/500/cle.png"},
    {"abbr": "DAL", "name": "Dallas Cowboys", "label": "Cowboys", "logo": "https://a.espncdn.com/i/teamlogos/nfl/500/dal.png"},
    {"abbr": "DEN", "name": "Denver Broncos", "label": "Broncos", "logo": "https://a.espncdn.com/i/teamlogos/nfl/500/den.png"},
    {"abbr": "DET", "name": "Detroit Lions", "label": "Lions", "logo": "https://a.espncdn.com/i/teamlogos/nfl/500/det.png"},
    {"abbr": "GB", "name": "Green Bay Packers", "label": "Packers", "logo": "https://a.espncdn.com/i/teamlogos/nfl/500/gb.png"},
    {"abbr": "HOU", "name": "Houston Texans", "label": "Texans", "logo": "https://a.espncdn.com/i/teamlogos/nfl/500/hou.png"},
    {"abbr": "IND", "name": "Indianapolis Colts", "label": "Colts", "logo": "https://a.espncdn.com/i/teamlogos/nfl/500/ind.png"},
    {"abbr": "JAX", "name": "Jacksonville Jaguars", "label": "Jaguars", "logo": "https://a.espncdn.com/i/teamlogos/nfl/500/jax.png"},
    {"abbr": "KC", "name": "Kansas City Chiefs", "label": "Chiefs", "logo": "https://a.espncdn.com/i/teamlogos/nfl/500/kc.png"},
    {"abbr": "LV", "name": "Las Vegas Raiders", "label": "Raiders", "logo": "https://a.espncdn.com/i/teamlogos/nfl/500/lv.png"},
    {"abbr": "LAC", "name": "Los Angeles Chargers", "label": "Chargers", "logo": "https://a.espncdn.com/i/teamlogos/nfl/500/lac.png"},
    {"abbr": "LAR", "name": "Los Angeles Rams", "label": "Rams", "logo": "https://a.espncdn.com/i/teamlogos/nfl/500/lar.png"},
    {"abbr": "MIA", "name": "Miami Dolphins", "label": "Dolphins", "logo": "https://a.espncdn.com/i/teamlogos/nfl/500/mia.png"},
    {"abbr": "MIN", "name": "Minnesota Vikings", "label": "Vikings", "logo": "https://a.espncdn.com/i/teamlogos/nfl/500/min.png"},
    {"abbr": "NE", "name": "New England Patriots", "label": "Patriots", "logo": "https://a.espncdn.com/i/teamlogos/nfl/500/ne.png"},
    {"abbr": "NO", "name": "New Orleans Saints", "label": "Saints", "logo": "https://a.espncdn.com/i/teamlogos/nfl/500/no.png"},
    {"abbr": "NYG", "name": "New York Giants", "label": "Giants", "logo": "https://a.espncdn.com/i/teamlogos/nfl/500/nyg.png"},
    {"abbr": "NYJ", "name": "New York Jets", "label": "Jets", "logo": "https://a.espncdn.com/i/teamlogos/nfl/500/nyj.png"},
    {"abbr": "PHI", "name": "Philadelphia Eagles", "label": "Eagles", "logo": "https://a.espncdn.com/i/teamlogos/nfl/500/phi.png"},
    {"abbr": "PIT", "name": "Pittsburgh Steelers", "label": "Steelers", "logo": "https://a.espncdn.com/i/teamlogos/nfl/500/pit.png"},
    {"abbr": "SEA", "name": "Seattle Seahawks", "label": "Seahawks", "logo": "https://a.espncdn.com/i/teamlogos/nfl/500/sea.png"},
    {"abbr": "SF", "name": "San Francisco 49ers", "label": "49ers", "logo": "https://a.espncdn.com/i/teamlogos/nfl/500/sf.png"},
    {"abbr": "TB", "name": "Tampa Bay Buccaneers", "label": "Buccaneers", "logo": "https://a.espncdn.com/i/teamlogos/nfl/500/tb.png"},
    {"abbr": "TEN", "name": "Tennessee Titans", "label": "Titans", "logo": "https://a.espncdn.com/i/teamlogos/nfl/500/ten.png"},
    {"abbr": "WAS", "name": "Washington Commanders", "label": "Commanders", "logo": "https://a.espncdn.com/i/teamlogos/nfl/500/wsh.png"},
]
NFL_TEAMS_BY_ABBR = {team["abbr"]: team["name"] for team in NFL_TEAMS}


@dataclass
class Player:
    """A player profile used for draft comparison."""

    name: str
    position: str
    team: str
    projected_points: float
    floor: float
    ceiling: float
    bye_week: int
    risk: str = "medium"
    headshot_url: Optional[str] = None


_HEADSHOT_CACHE: Dict[str, object] = {"map": {}, "fetched_at": 0}
_HEADSHOT_CACHE_TTL = 60 * 60


def _normalize_headshot_url(url: Optional[str]) -> Optional[str]:
    """Promote known provider URLs to high-resolution headshot variants."""
    if not url:
        return None

    normalized = str(url).strip()
    if not normalized:
        return None

    if "a.espncdn.com/i/headshots/nfl/players" in normalized:
        normalized = re.sub(
            r"/players/(?:\d+x\d+|small|medium|large|xlarge)/",
            "/players/full/",
            normalized,
            flags=re.IGNORECASE,
        )
        normalized = re.sub(r"(\.png|\.jpg|\.jpeg|\.webp).*$", r"\1", normalized, flags=re.IGNORECASE)

    if "static.www.nfl.com/image/private/" in normalized and "/league/players/headshot/" in normalized:
        normalized = re.sub(
            r"/image/private/[^/]+/league/players/headshot/",
            "/image/private/f_png,q_auto:best,w_512,h_512,c_limit/league/players/headshot/",
            normalized,
            flags=re.IGNORECASE,
        )

    return normalized


def _nfl_headshot_url_from_id(player_id: str) -> Optional[str]:
    if not player_id:
        return None
    return _normalize_headshot_url(
        f"https://static.www.nfl.com/image/private/f_png,q_auto:best,w_512,h_512,c_limit/league/players/headshot/{player_id}.png"
    )


def _normalize_player_name(name: str) -> str:
    if not name:
        return ""
    normalized = unicodedata.normalize("NFKD", name)
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = normalized.strip().lower()
    normalized = re.sub(r"[^\w\s]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _build_headshot_map() -> Dict[str, str]:
    if not ENABLE_OPTIONAL_PLAYER_DATA:
        return {}

    nfl_data_py = _load_optional_module("nfl_data_py")
    if nfl_data_py is not None:
        try:
            df = nfl_data_py.import_players()
            if hasattr(df, "to_pandas"):
                pdf = df.to_pandas()
            else:
                pdf = df

            columns = set(getattr(pdf, "columns", []))
            if not columns or "player_name" not in columns:
                return {}

            id_field = None
            for candidate in ("player_id", "gsis_id", "nfl_id"):
                if candidate in columns:
                    id_field = candidate
                    break

            if id_field is None:
                return {}

            if hasattr(pdf, "to_dicts"):
                records = pdf.to_dicts()
            elif hasattr(pdf, "to_dict"):
                records = pdf.to_dict(orient="records")
            else:
                records = [dict(row) for row in pdf]

            mapping: Dict[str, str] = {}
            for row in records:
                player_name = str(row.get("player_name") or row.get("name") or "").strip()
                player_id = str(row.get(id_field) or "").strip()
                if not player_name or not player_id:
                    continue
                headshot = _nfl_headshot_url_from_id(player_id)
                if headshot:
                    normalized_name = _normalize_player_name(player_name)
                    mapping[player_name.lower()] = headshot
                    mapping[normalized_name] = headshot
            return mapping
        except Exception:
            pass

    nflreadpy = _load_optional_module("nflreadpy")
    if nflreadpy is None or not hasattr(nflreadpy, "load_players"):
        return {}

    try:
        df = nflreadpy.load_players()
        if hasattr(df, "to_pandas"):
            pdf = df.to_pandas()
        else:
            pdf = df

        if not hasattr(pdf, "columns") or "headshot" not in pdf.columns:
            return {}

        if hasattr(pdf, "to_dicts"):
            records = pdf.to_dicts()
        elif hasattr(pdf, "to_dict"):
            records = pdf.to_dict(orient="records")
        else:
            return {}

        mapping: Dict[str, str] = {}
        for row in records:
            headshot = str(
                row.get("headshot")
                or row.get("headshot_url")
                or row.get("image_url")
                or row.get("photo_url")
                or ""
            ).strip()
            if not headshot:
                continue

            for field in (
                "display_name",
                "football_name",
                "short_name",
                "name",
                "displayName",
                "fullName",
                "player_name",
                "playerName",
            ):
                value = str(row.get(field) or "").strip()
                if not value:
                    continue

                normalized_value = _normalize_player_name(value)
                headshot = _normalize_headshot_url(headshot)
                mapping[value.lower()] = headshot
                mapping[normalized_value] = headshot
        return mapping
    except Exception:
        return {}


def get_headshot_map() -> Dict[str, str]:
    now = time.time()
    if _HEADSHOT_CACHE["map"] and now - _HEADSHOT_CACHE["fetched_at"] < _HEADSHOT_CACHE_TTL:
        return _HEADSHOT_CACHE["map"]

    mapping = _build_headshot_map()
    if mapping:
        _HEADSHOT_CACHE["map"] = mapping
        _HEADSHOT_CACHE["fetched_at"] = now
    return mapping


def resolve_headshot_url(name: str) -> Optional[str]:
    if not name:
        return None
    normalized_name = _normalize_player_name(name)
    headshot_map = get_headshot_map()
    if normalized_name and normalized_name in headshot_map:
        return _normalize_headshot_url(headshot_map[normalized_name])
    known_url = _normalize_headshot_url(headshot_map.get(name.strip().lower()))
    if known_url:
        return known_url

    if SleeperPlayers is not None and name:
        try:
            now = time.time()
            if now - _SLEEPER_DIRECTORY_CACHE["fetched_at"] >= _SLEEPER_DIRECTORY_CACHE_TTL:
                directory = SleeperPlayers().get_all_players("nfl")
                _SLEEPER_DIRECTORY_CACHE["players"] = directory if isinstance(directory, dict) else {}
                _SLEEPER_DIRECTORY_CACHE["fetched_at"] = now
            target = _normalize_player_name(name)
            for player_id, player_data in _SLEEPER_DIRECTORY_CACHE["players"].items():
                first = str(player_data.get("first_name") or "").strip()
                last = str(player_data.get("last_name") or "").strip()
                full_name = _normalize_player_name(str(player_data.get("full_name") or f"{first} {last}"))
                if full_name == target:
                    return f"https://sleepercdn.com/content/nfl/players/thumb/{player_id}.jpg"
        except Exception:
            pass

    return None


def sleeper_headshot_url(player_id: str, player_data: dict, name: str) -> Optional[str]:
    """Build a Sleeper CDN headshot URL, falling back to the existing resolver."""
    avatar = str(player_data.get("avatar") or "").strip()
    if avatar.startswith("http"):
        return avatar
    if player_id:
        return f"https://sleepercdn.com/content/nfl/players/thumb/{player_id}.jpg"
    return resolve_headshot_url(name)


def sleeper_player_profile(name: str) -> dict:
    """Find a player's Sleeper profile from the cached NFL directory."""
    if SleeperPlayers is None or not name:
        return {}
    try:
        now = time.time()
        if now - _SLEEPER_DIRECTORY_CACHE["fetched_at"] >= _SLEEPER_DIRECTORY_CACHE_TTL:
            directory = SleeperPlayers().get_all_players("nfl")
            _SLEEPER_DIRECTORY_CACHE["players"] = directory if isinstance(directory, dict) else {}
            _SLEEPER_DIRECTORY_CACHE["fetched_at"] = now
        target = _normalize_player_name(name)
        for player_data in _SLEEPER_DIRECTORY_CACHE["players"].values():
            first = str(player_data.get("first_name") or "").strip()
            last = str(player_data.get("last_name") or "").strip()
            full_name = _normalize_player_name(str(player_data.get("full_name") or f"{first} {last}"))
            if full_name == target:
                return player_data
    except Exception:
        pass
    return {}


def enrich_player_position(player: Player) -> Player:
    """Prefer Sleeper's position data when enriching a player for the UI."""
    sleeper_profile = sleeper_player_profile(player.name)
    sleeper_position = str(sleeper_profile.get("position") or "").strip().upper()
    if sleeper_position:
        player.position = sleeper_position
    return player


def player_from_espn_record(record) -> Player:
    """Normalize a live ESPN record into the app's Player model."""
    if hasattr(record, "name"):
        record = {
            "name": getattr(record, "name"),
            "position": getattr(record, "position", "FLEX"),
            "team": getattr(record, "proTeam", "FA"),
            "projected_points": getattr(record, "projected_points", 0),
            "floor": getattr(record, "floor", 0),
            "ceiling": getattr(record, "ceiling", getattr(record, "projected_points", 0)),
            "bye_week": getattr(record, "bye_week", 0),
            "risk": getattr(record, "risk", "medium"),
        }

    player_data = dict(record)
    name = (
        player_data.get("name")
        or player_data.get("fullName")
        or player_data.get("player_name")
        or "Unknown Player"
    )
    position = player_data.get("position") or "FLEX"
    team = player_data.get("team") or player_data.get("proTeam") or "FA"
    projected_points = float(player_data.get("projected_points", player_data.get("projectedPoints", 0)) or 0)
    floor = float(player_data.get("floor", projected_points * 0.8) or 0)
    ceiling = float(player_data.get("ceiling", projected_points * 1.2) or projected_points)
    bye_week = int(player_data.get("bye_week", player_data.get("byeWeek", 0)) or 0)
    risk = str(player_data.get("risk", "medium")).lower()
    headshot_url = resolve_headshot_url(name)

    return Player(
        name=name,
        position=position,
        team=team,
        projected_points=projected_points,
        floor=floor,
        ceiling=ceiling,
        bye_week=bye_week,
        risk=risk,
        headshot_url=headshot_url,
    )


def get_default_players() -> list[Player]:
    """Return a curated pool of players to compare before a draft."""
    return [
        Player(
            name="Christian McCaffrey",
            position="RB",
            team="SF",
            projected_points=320.0,
            floor=250.0,
            ceiling=370.0,
            bye_week=9,
            risk="low",
            headshot_url=resolve_headshot_url("Christian McCaffrey"),
        ),
        Player(
            name="CeeDee Lamb",
            position="WR",
            team="DAL",
            projected_points=290.0,
            floor=220.0,
            ceiling=335.0,
            bye_week=7,
            risk="low",
            headshot_url=resolve_headshot_url("CeeDee Lamb"),
        ),
        Player(
            name="Jalen Hurts",
            position="QB",
            team="PHI",
            projected_points=280.0,
            floor=210.0,
            ceiling=320.0,
            bye_week=5,
            risk="medium",
            headshot_url=resolve_headshot_url("Jalen Hurts"),
        ),
        Player(
            name="Sam LaPorta",
            position="TE",
            team="DET",
            projected_points=210.0,
            floor=150.0,
            ceiling=250.0,
            bye_week=9,
            risk="medium",
            headshot_url=resolve_headshot_url("Sam LaPorta"),
        ),
        Player(
            name="Bijan Robinson",
            position="RB",
            team="ATL",
            projected_points=300.0,
            floor=230.0,
            ceiling=345.0,
            bye_week=6,
            risk="low",
            headshot_url=resolve_headshot_url("Bijan Robinson"),
        ),
        Player(
            name="Amon-Ra St. Brown",
            position="WR",
            team="DET",
            projected_points=260.0,
            floor=190.0,
            ceiling=305.0,
            bye_week=9,
            risk="low",
            headshot_url=resolve_headshot_url("Amon-Ra St. Brown"),
        ),
    ]


def _normalize_roster_value(value, fallback="FLEX") -> str:
    """Convert ESPN roster fields from dict/list values into a string."""
    if value is None:
        return fallback
    if isinstance(value, dict):
        for key in ("abbreviation", "name", "displayName", "shortName", "text"):
            nested = value.get(key)
            if nested is not None:
                return str(nested)
        for key in ("position", "team"):
            nested = value.get(key)
            if nested is not None:
                normalized = _normalize_roster_value(nested, fallback)
                if normalized != fallback:
                    return normalized
        return fallback
    if isinstance(value, list):
        for item in value:
            normalized = _normalize_roster_value(item, fallback=None)
            if normalized not in (None, fallback):
                return str(normalized)
        return fallback
    return str(value)

_ROSTER_CACHE = {"players": [], "fetched_at": 0}
_ROSTER_CACHE_TTL = 60 * 60
_PLAYER_SEARCH_CACHE: Dict[str, List[Player]] = {}
_NEWS_CACHE = {"items": [], "fetched_at": 0}
_NEWS_CACHE_TTL = 2 * 60
_GAMES_CACHE = {"items": [], "fetched_at": 0}
_GAMES_CACHE_TTL = 2 * 60
_TRENDING_CACHE = {"items": [], "fetched_at": 0}
_TRENDING_CACHE_TTL = 4 * 60 * 60


def get_latest_nfl_news(force_refresh: bool = False) -> List[dict]:
    """Return latest NFL news headlines from ESPN with short in-memory caching."""
    now = time.time()
    if not force_refresh and _NEWS_CACHE["items"] and now - _NEWS_CACHE["fetched_at"] < _NEWS_CACHE_TTL:
        return _NEWS_CACHE["items"]

    fallback = [
        {"headline": "NFL training camp reports continue across all 32 teams."},
        {"headline": "Depth-chart updates and injury reports shape draft boards."},
        {"headline": "Preseason usage trends highlight emerging fantasy values."},
        {"headline": "Coaching updates and scheme shifts impact weekly projections."},
    ]

    try:
        response = requests.get(
            "https://site.api.espn.com/apis/site/v2/sports/football/nfl/news",
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return fallback

    items = []
    for article in payload.get("articles", [])[:8]:
        headline = str(article.get("headline") or "").strip()
        if not headline:
            continue
        source = str(article.get("source") or "ESPN").strip() or "ESPN"
        link = str(article.get("links", {}).get("web", {}).get("href") or "").strip()
        items.append({"headline": headline, "source": source, "link": link})

    if not items:
        return fallback

    _NEWS_CACHE["items"] = items
    _NEWS_CACHE["fetched_at"] = now
    return items


def _format_kickoff_time(date_value: str) -> str:
    """Format an ESPN kickoff timestamp into a compact readable string."""
    if not date_value:
        return "TBD"
    try:
        kickoff = datetime.fromisoformat(str(date_value).replace("Z", "+00:00"))
        return kickoff.strftime("%b %d %I:%M %p")
    except Exception:
        return "TBD"


def _upcoming_games_from_payload(payload: dict) -> List[dict]:
    """Extract scheduled/in-progress games from an ESPN scoreboard payload."""
    season_labels = {
        "preseason": "Preseason",
        "regular-season": "Regular Season",
        "post-season": "Postseason",
        "postseason": "Postseason",
    }
    games = []
    for event in payload.get("events", []):
        status = event.get("status", {}).get("type", {})
        state = str(status.get("state") or "").lower()
        if state not in {"pre", "in"}:
            continue

        season = event.get("season", {})
        season_slug = str(season.get("slug") or "").strip().lower()
        season_label = season_labels.get(season_slug, "NFL")

        competition = (event.get("competitions") or [{}])[0]
        competitors = competition.get("competitors") or []

        away_team = ""
        home_team = ""
        for competitor in competitors:
            team = competitor.get("team", {})
            team_name = str(team.get("nickname") or team.get("shortDisplayName") or team.get("displayName") or "").strip()
            if competitor.get("homeAway") == "away":
                away_team = team_name
            elif competitor.get("homeAway") == "home":
                home_team = team_name

        if not away_team or not home_team:
            continue

        games.append(
            {
                "id": str(event.get("id") or ""),
                "matchup": f"{away_team} at {home_team}",
                "kickoff": _format_kickoff_time(event.get("date") or ""),
                "season_label": season_label,
                "state": state,
                "date": str(event.get("date") or ""),
            }
        )
    return games


def get_upcoming_nfl_games(force_refresh: bool = False) -> List[dict]:
    """Return upcoming NFL games, including preseason, with short caching."""
    now = time.time()
    if not force_refresh and _GAMES_CACHE["items"] and now - _GAMES_CACHE["fetched_at"] < _GAMES_CACHE_TTL:
        return _GAMES_CACHE["items"]

    fallback = [
        {"matchup": "Preseason games loading", "kickoff": "Check back shortly", "season_label": "Preseason", "state": "pre"},
        {"matchup": "Regular season slate loading", "kickoff": "Check back shortly", "season_label": "Regular Season", "state": "pre"},
    ]

    all_games: List[dict] = []
    today = datetime.utcnow().date()
    end_date = today + timedelta(days=60)
    date_range = f"{today:%Y%m%d}-{end_date:%Y%m%d}"

    try:
        response = requests.get(
            f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates={date_range}",
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
        all_games = _upcoming_games_from_payload(payload)
    except Exception:
        all_games = []

    if not all_games:
        return fallback

    all_games.sort(key=lambda game: game.get("date") or "")
    cleaned_games = [
        {
            "matchup": game["matchup"],
            "kickoff": game["kickoff"],
            "season_label": game["season_label"],
            "state": game["state"],
        }
        for game in all_games[:48]
    ]

    _GAMES_CACHE["items"] = cleaned_games
    _GAMES_CACHE["fetched_at"] = now
    return cleaned_games


def get_trending_players(force_refresh: bool = False) -> List[dict]:
    """Return Sleeper's top ten added players with four-hour caching."""
    now = time.time()
    if not force_refresh and _TRENDING_CACHE["items"] and now - _TRENDING_CACHE["fetched_at"] < _TRENDING_CACHE_TTL:
        return _TRENDING_CACHE["items"]

    if SleeperPlayers is None:
        return []

    try:
        sleeper_players = SleeperPlayers()
        trending = sleeper_players.get_trending_players("nfl", add_drop="add", hours=24, limit=10)
        directory = sleeper_players.get_all_players("nfl")
    except Exception:
        return _TRENDING_CACHE["items"] or []

    items = []
    for entry in trending:
        player_id = str(entry.get("player_id") or "")
        player_data = directory.get(player_id, {})
        first_name = str(player_data.get("first_name") or "").strip()
        last_name = str(player_data.get("last_name") or "").strip()
        name = str(player_data.get("full_name") or f"{first_name} {last_name}").strip()
        if not name:
            continue
        items.append(
            {
                "rank": len(items) + 1,
                "name": name,
                "position": str(player_data.get("position") or "FLEX"),
                "team": str(player_data.get("team") or "FA"),
                "trend_count": int(entry.get("count") or 0),
                "headshot_url": sleeper_headshot_url(player_id, player_data, name),
            }
        )
        if len(items) == 10:
            break

    _TRENDING_CACHE["items"] = items
    _TRENDING_CACHE["fetched_at"] = now
    return items


def _fetch_all_active_players(year: int = 2026) -> List[Player]:
    try:
        teams_response = requests.get(
            "https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams",
            timeout=20,
        )
        teams_response.raise_for_status()
        teams_payload = teams_response.json()
    except Exception:
        return []

    teams = []
    for sport in teams_payload.get("sports", []):
        for league in sport.get("leagues", []):
            for team_entry in league.get("teams", []):
                team = team_entry.get("team", {})
                team_id = team.get("id")
                team_abbr = team.get("abbreviation") or team.get("shortName") or "FA"
                team_name = team.get("displayName") or team.get("name") or team_abbr
                if team_id:
                    teams.append({"id": str(team_id), "abbreviation": str(team_abbr).upper(), "name": team_name})

    players = []
    projected_by_position = {
        "QB": 265.0,
        "RB": 165.0,
        "WR": 150.0,
        "TE": 120.0,
        "K": 95.0,
        "DST": 90.0,
        "FLEX": 135.0,
    }

    def _extract_espn_headshot(item: dict) -> Optional[str]:
        headshot_data = item.get("headshot")
        if isinstance(headshot_data, dict):
            return _normalize_headshot_url(headshot_data.get("href") or headshot_data.get("url"))

        athlete_data = item.get("athlete")
        if isinstance(athlete_data, dict):
            athlete_headshot = athlete_data.get("headshot")
            if isinstance(athlete_headshot, dict):
                return _normalize_headshot_url(athlete_headshot.get("href") or athlete_headshot.get("url"))

        return None

    for team in teams:
        try:
            roster_url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/{team['id']}/roster"
            roster_response = requests.get(roster_url, timeout=20)
            roster_response.raise_for_status()
            roster_payload = roster_response.json()
        except Exception:
            continue

        athletes = roster_payload.get("athletes", [])
        for athlete_group in athletes:
            for item in athlete_group.get("items", []):
                full_name = (item.get("fullName") or item.get("displayName") or "").strip()
                if not full_name:
                    continue

                raw_position = item.get("displayPosition") or item.get("position") or "FLEX"
                position = _normalize_roster_value(raw_position, "FLEX").upper()
                raw_team = item.get("team") or team.get("abbreviation") or "FA"
                team_abbr = _normalize_roster_value(raw_team, "FA").upper()
                projected = projected_by_position.get(position, 120.0)
                floor = max(0.0, projected * 0.75)
                ceiling = projected * 1.25

                headshot_url = _extract_espn_headshot(item) or resolve_headshot_url(full_name)

                players.append(
                    Player(
                        name=full_name,
                        position=position,
                        team=team_abbr,
                        projected_points=round(projected, 1),
                        floor=round(floor, 1),
                        ceiling=round(ceiling, 1),
                        bye_week=0,
                        risk="medium",
                        headshot_url=headshot_url,
                    )
                )

    return players


def get_cached_active_players(year: int = 2026) -> List[Player]:
    now = time.time()
    if _ROSTER_CACHE["players"] and now - _ROSTER_CACHE["fetched_at"] < _ROSTER_CACHE_TTL:
        return _ROSTER_CACHE["players"]

    players = _fetch_all_active_players(year)
    if players:
        _ROSTER_CACHE["players"] = players
        _ROSTER_CACHE["fetched_at"] = now
    return players


def search_active_players(query: str, year: int = 2026) -> List[Player]:
    """Search every active NFL roster by team through ESPN’s public roster endpoints."""
    text = (query or "").strip()
    if not text or len(text) < 2:
        return get_default_players()

    players = get_cached_active_players(year)
    if not players:
        return get_default_players()

    needle = text.lower()
    cache_key = needle
    if cache_key in _PLAYER_SEARCH_CACHE:
        return _PLAYER_SEARCH_CACHE[cache_key]

    results = [player for player in players if needle in player.name.lower()]
    if results:
        results.sort(key=lambda player: player.projected_points, reverse=True)
        results = results[:12]
    else:
        results = get_default_players()

    _PLAYER_SEARCH_CACHE[cache_key] = results
    return results


def get_team_roster(team_code: str, year: int = 2026) -> List[Player]:
    """Return active roster players for a selected NFL team."""
    normalized_team = (team_code or "").strip().upper()
    if not normalized_team:
        return []

    players = [player for player in get_cached_active_players(year) if player.team.upper() == normalized_team]
    players.sort(key=lambda player: (player.position, player.name))
    return players


def get_espn_players() -> List[Player]:
    """Pull a live player pool from ESPN if league credentials are available."""
    if League is None:
        return get_default_players()

    league_id = os.getenv("ESPN_LEAGUE_ID")
    year = os.getenv("ESPN_YEAR", "2026")
    espn_s2 = os.getenv("ESPN_S2")
    swid = os.getenv("SWID")

    if not league_id or not (espn_s2 and swid):
        return get_default_players()

    try:
        league = League(int(league_id), int(year), espn_s2=espn_s2, swid=swid)
        free_agents = league.free_agents(week=league.current_week or 1, size=10)
    except Exception:
        return get_default_players()

    players = []
    for player in free_agents:
        try:
            record = {
                "name": getattr(player, "name", "Unknown Player"),
                "position": getattr(player, "position", "FLEX"),
                "team": getattr(player, "proTeam", "FA"),
                "projected_points": getattr(player, "projected_points", 0),
                "floor": getattr(player, "floor", getattr(player, "projected_points", 0) * 0.8),
                "ceiling": getattr(player, "ceiling", getattr(player, "projected_points", 0) * 1.2),
                "bye_week": getattr(player, "bye_week", 0),
                "risk": "medium",
            }
            players.append(player_from_espn_record(record))
        except Exception:
            continue

    return players or get_default_players()


def player_draft_score(player: Player, mode: str = "redraft") -> float:
    """Score a player for a redraft or dynasty comparison."""
    risk_bonus = {"low": 12.0, "medium": 6.0, "high": 0.0}.get(player.risk.lower(), 6.0)
    if mode == "dynasty":
        position_bonus = {"QB": 8.0, "RB": 3.0, "WR": 10.0, "TE": 8.0}.get(player.position.upper(), 0.0)
        return round(
            player.projected_points * 0.9
            + player.ceiling * 0.75
            + (player.ceiling - player.floor) * 0.65
            + risk_bonus
            + position_bonus,
            2,
        )
    return round(
        player.projected_points * 1.2
        + (player.ceiling - player.floor) * 0.5
        + risk_bonus,
        2,
    )


def compare_players(player_a: Player, player_b: Player, mode: str = "redraft") -> dict:
    """Compare two players using the selected fantasy format."""
    mode = mode if mode in {"redraft", "dynasty"} else "redraft"
    a_score = player_draft_score(player_a, mode)
    b_score = player_draft_score(player_b, mode)
    winner = player_a if a_score >= b_score else player_b

    return {
        "mode": mode,
        "winner": winner.name,
        "score_gap": round(abs(a_score - b_score), 2),
        "category_winner": {
            "projected_points": player_a.name if player_a.projected_points >= player_b.projected_points else player_b.name,
            "floor": player_a.name if player_a.floor >= player_b.floor else player_b.name,
            "ceiling": player_a.name if player_a.ceiling >= player_b.ceiling else player_b.name,
            "draft_score": winner.name,
        },
        "player_a": {
            "name": player_a.name,
            "position": player_a.position,
            "projected_points": player_a.projected_points,
            "draft_score": a_score,
            "headshot_url": player_a.headshot_url,
        },
        "player_b": {
            "name": player_b.name,
            "position": player_b.position,
            "projected_points": player_b.projected_points,
            "draft_score": b_score,
            "headshot_url": player_b.headshot_url,
        },
    }


def player_from_identity(selected_value: str) -> Player:
    """Build a minimal Player record from a saved identity when it is not in the current search results."""
    parts = [part.strip() for part in selected_value.split("|")]
    name = parts[0] if len(parts) > 0 else "Unknown Player"
    position = parts[1] if len(parts) > 1 else "FLEX"
    team = parts[2] if len(parts) > 2 else "FA"
    roster_search = search_active_players(name) if name else []
    for player in roster_search:
        if player.name.lower() != name.lower():
            continue
        if position != "FLEX" and player.position.upper() != position.upper():
            continue
        if team != "FA" and player.team.upper() != team.upper():
            continue
        return player
    return Player(
        name=name,
        position=position,
        team=team,
        projected_points=0.0,
        floor=0.0,
        ceiling=0.0,
        bye_week=0,
        risk="medium",
        headshot_url=resolve_headshot_url(name),
    )


def resolve_player_choice(players: List[Player], selected_value: Optional[str], fallback_index: int = 0) -> Player:
    """Resolve a selected player from either a legacy name-only value or a composite name|position|team value."""
    if not players:
        return get_default_players()[0]

    if not selected_value:
        return players[fallback_index if fallback_index < len(players) else 0]

    selected_value = selected_value.strip()
    if not selected_value:
        return players[fallback_index if fallback_index < len(players) else 0]

    for player in players:
        identity = f"{player.name}|{player.position}|{player.team}"
        if selected_value == identity:
            return player

    for player in players:
        if selected_value == player.name:
            return player

    roster_search = search_active_players(selected_value)
    for player in roster_search:
        if player.name.lower() == selected_value.lower():
            return player

    if "|" in selected_value:
        name_part, position_part, team_part = (selected_value.split("|") + ["", "", ""])[:3]
        player_name = name_part.strip()
        if player_name:
            roster_search = search_active_players(player_name)
            for player in roster_search:
                if player.name.lower() == player_name.lower():
                    if position_part and player.position.upper() != position_part.upper():
                        continue
                    if team_part and player.team.upper() != team_part.upper():
                        continue
                    return player
            return player_from_identity(selected_value)

    return players[fallback_index if fallback_index < len(players) else 0]


def player_identity(player: Player) -> str:
    """Create a stable identity string for a player selection."""
    return f"{player.name}|{player.position}|{player.team}"


def format_player(player: Player) -> str:
    """Create a clean, readable summary for a player."""
    return (
        f"{player.name} ({player.position}, {player.team}) | "
        f"Proj: {player.projected_points} | Floor: {player.floor} | Ceiling: {player.ceiling} | "
        f"Risk: {player.risk.title()} | Bye: {player.bye_week}"
    )


def build_projection_chart(players: List[Player]) -> str:
    """Create a Matplotlib comparison chart and return a base64-encoded PNG."""
    names = [player.name for player in players]
    scores = [player.projected_points for player in players]

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(names, scores, color="#39ff14")
    ax.set_title("Projected fantasy points")
    ax.set_ylabel("Projected points")
    ax.set_xlabel("Player")
    ax.tick_params(axis="x", rotation=20)
    for bar, value in zip(bars, scores):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 5, f"{value}", ha="center", va="bottom")
    fig.tight_layout()

    image_buffer = io.BytesIO()
    fig.savefig(image_buffer, format="png", dpi=150)
    plt.close(fig)
    return base64.b64encode(image_buffer.getvalue()).decode("utf-8")


def build_matchup_intel(players: List[Player]) -> List[dict]:
    """Return centralized matchup intel for upcoming games, with a graceful fallback when the package is unavailable."""
    if fantasyfootball is not None:
        try:
            getter = getattr(fantasyfootball, "get_matchup_intel", None)
            if callable(getter):
                intel = getter(players)
                if isinstance(intel, list) and intel:
                    photos_by_name = {player.name.lower(): player.headshot_url for player in players if player.headshot_url}
                    positions_by_name = {player.name.lower(): player.position for player in players}
                    for card in intel:
                        if not card.get("headshot_url"):
                            card["headshot_url"] = photos_by_name.get(str(card.get("player") or "").lower())
                        if not card.get("position"):
                            card["position"] = positions_by_name.get(str(card.get("player") or "").lower(), "FLEX")
                    return intel
        except Exception:
            pass

    default_cards = [
        {
            "player": "Josh Allen",
            "team": "BUF",
            "opponent": "vs KC",
            "spread": "-3.5",
            "moneyline": "-180",
            "total": "47.5",
            "injury_status": "No injury designation",
            "weather": "Clear skies • 68°F • 7 mph wind",
            "detail": "High ceiling with strong rushing equity.",
        },
        {
            "player": "Patrick Mahomes",
            "team": "KC",
            "opponent": "at BUF",
            "spread": "+3.5",
            "moneyline": "+150",
            "total": "47.5",
            "injury_status": "No injury designation",
            "weather": "Cool evening • 66°F • 9 mph wind",
            "detail": "Elite red-zone efficiency and late-game volume.",
        },
    ]

    if not players:
        return default_cards

    intel = []
    for player in players[:2]:
        team = player.team.upper()
        opponent = "vs BAL" if team == "BUF" else "at BUF" if team == "KC" else "vs IND" if team == "JAX" else "at LAC"
        intel.append(
            {
                "player": player.name,
                "position": player.position,
                "team": team,
                "opponent": opponent,
                "spread": "-2.5" if team == "BUF" else "+2.5",
                "moneyline": "-140" if team == "BUF" else "+120",
                "total": "48.5",
                "injury_status": "No active injury report",
                "weather": "Comfortable conditions • 70°F • light wind",
                "detail": "Strong weekly matchup with favorable game script.",
                "headshot_url": player.headshot_url,
            }
        )

    return intel[:2] if intel else default_cards


def create_app() -> Flask:
    """Create a lightweight local web dashboard for fantasy comparison."""
    app = Flask(__name__)
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.config['DEBUG'] = True
    # Completely disable Jinja2 caching
    app.jinja_env.cache = None
    app.jinja_env.auto_reload = True
    # Force direct template file reading without caching
    from jinja2 import FileSystemLoader
    import os
    template_dir = os.path.join(os.path.dirname(__file__), 'templates')
    app.jinja_loader = FileSystemLoader(template_dir)
    
    @app.after_request
    def add_no_cache_headers(response):
        """Add cache control headers to disable all caching."""
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response

    @app.route("/", methods=["GET"])
    def index():
        search_query = (request.args.get("search") or "").strip()
        selected_team = (request.args.get("team") or "").strip().upper()
        if selected_team not in NFL_TEAMS_BY_ABBR:
            selected_team = ""

        if search_query:
            players = search_active_players(search_query)
            if selected_team:
                players = [player for player in players if player.team.upper() == selected_team]
        elif selected_team:
            players = get_team_roster(selected_team)
        else:
            players = get_default_players()

        if not players:
            players = [] if selected_team else get_default_players()

        selected_values = request.args.getlist("selected")
        add_player = request.args.get("add_player")

        if add_player:
            if add_player not in selected_values:
                selected_values.append(add_player)
            selected_values = selected_values[:2]

        selected_players = []
        seen = set()
        for selected_value in selected_values:
            resolved = enrich_player_position(resolve_player_choice(players, selected_value, fallback_index=0))
            identity = player_identity(resolved)
            if identity not in seen:
                selected_players.append(resolved)
                seen.add(identity)

        compare_requested = request.args.get("compare") == "true"
        compare_mode = (request.args.get("mode") or "redraft").strip().lower()
        if compare_mode not in {"redraft", "dynasty"}:
            compare_mode = "redraft"
        comparison = None
        if len(selected_players) == 2 and compare_requested:
            comparison = compare_players(selected_players[0], selected_players[1], compare_mode)

        chart_players = selected_players if len(selected_players) == 2 else players[:10]
        chart_data = build_projection_chart(chart_players)
        matchup_intel = build_matchup_intel(selected_players) if selected_players else []
        selected_team_name = NFL_TEAMS_BY_ABBR.get(selected_team, "")
        if selected_team_name:
            result_title = f"{selected_team_name} Roster"
        else:
            result_title = "Search results"

        html = render_template(
            "index.html",
            players=players,
            comparison=comparison,
            chart_data=chart_data,
            selected_players=selected_players,
            selected_values=selected_values,
            player_list=players,
            search_query=search_query,
            compare_requested=compare_requested,
            compare_mode=compare_mode,
            matchup_intel=matchup_intel,
            nfl_teams=NFL_TEAMS,
            selected_team=selected_team,
            selected_team_name=selected_team_name,
            result_title=result_title,
        )
        from flask import Response
        return Response(html, mimetype='text/html')

    from threading import Thread

    def preload_suggestion_cache() -> None:
        get_cached_active_players()
        if ENABLE_OPTIONAL_PLAYER_DATA:
            get_headshot_map()

    Thread(target=preload_suggestion_cache, daemon=True).start()

    @app.route("/suggest", methods=["GET"])
    def suggest():
        query = (request.args.get("q") or "").strip()
        if not query:
            return jsonify([])

        players = search_active_players(query)[:10]
        suggestions = [
            {
                "name": player.name,
                "position": enrich_player_position(player).position,
                "team": player.team,
                "projected_points": player.projected_points,
                "identity": player_identity(player),
                "value": player.name,
                "display": f"{player.name} ({player.position}, {player.team})",
                "headshot_url": player.headshot_url,
            }
            for player in players
        ]
        return jsonify(suggestions)

    @app.route("/news", methods=["GET"])
    def news():
        refresh_value = (request.args.get("refresh") or "").strip().lower()
        force_refresh = refresh_value in {"1", "true", "yes", "y", "on"}
        return jsonify(get_latest_nfl_news(force_refresh=force_refresh))

    @app.route("/games", methods=["GET"])
    def games():
        refresh_value = (request.args.get("refresh") or "").strip().lower()
        force_refresh = refresh_value in {"1", "true", "yes", "y", "on"}
        return jsonify(get_upcoming_nfl_games(force_refresh=force_refresh))

    @app.route("/trending", methods=["GET"])
    def trending():
        refresh_value = (request.args.get("refresh") or "").strip().lower()
        force_refresh = refresh_value in {"1", "true", "yes", "y", "on"}
        return jsonify(get_trending_players(force_refresh=force_refresh))

    # Force template to reload from disk on every request
    @app.before_request
    def clear_template_cache():
        if app.jinja_env.cache is not None:
            app.jinja_env.cache.clear()

    return app


def run_cli() -> None:
    """Launch a simple command-line comparison tool."""
    players = get_espn_players()
    print("Fantasy Football Draft Comparator")
    print("=" * 36)
    for index, player in enumerate(players, start=1):
        print(f"{index}. {format_player(player)}")

    try:
        first_choice = int(input("Choose player 1 number: ")) - 1
        second_choice = int(input("Choose player 2 number: ")) - 1
    except ValueError:
        print("Please enter valid numbers only.")
        return

    if not (0 <= first_choice < len(players) and 0 <= second_choice < len(players)):
        print("Please select player numbers from the list.")
        return

    player_one = players[first_choice]
    player_two = players[second_choice]
    result = compare_players(player_one, player_two)

    print("\nComparison result")
    print("-" * 24)
    print(f"Winner: {result['winner']}")
    print(f"Draft score gap: {result['score_gap']}")
    print(f"Projected points winner: {result['category_winner']['projected_points']}")
    print(f"Ceiling winner: {result['category_winner']['ceiling']}")
    print(f"Floor winner: {result['category_winner']['floor']}")
    print(f"\n{player_one.name}: {player_draft_score(player_one)}")
    print(f"{player_two.name}: {player_draft_score(player_two)}")


app = create_app()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(host="127.0.0.1", port=port, debug=debug)
