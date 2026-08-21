# The Lab UI Test Plan

**Document type:** Formal browser UI test sheet  
**Application:** The Lab fantasy football comparison app  
**Test framework:** Playwright with Python and pytest  
**Target browser:** Chromium  
**Test environment:** Local Flask server on an ephemeral port  
**Owner:** QA / Engineering  
**Date:** 2026-08-20

## 1. Objective

Verify the basic user-facing functionality currently implemented in The Lab, including page loading, player search, player selection, navigation menus, comparison setup, data-driven widgets, and responsive search layout.

## 2. Scope

### In scope

- Homepage rendering and branding
- Player search input and autocomplete suggestions
- Locking a player into the Selected players panel
- Trending players dropdown
- Injury Report dropdown
- Latest NFL News dropdown
- Upcoming games ticker
- NFL Teams dropdown and team links
- Two-player comparison action availability
- Mobile search surface sizing

### Out of scope

- Accuracy of third-party ESPN, Sleeper, or NFL data
- Visual pixel comparison against a design file
- Full comparison calculation correctness
- Sleeper league upload processing
- Network availability of external data providers
- Performance, load, and security testing

## 3. Test Setup

1. Install project dependencies:

   ```powershell
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

2. Install the Playwright Chromium browser:

   ```powershell
   .\.venv\Scripts\python.exe -m playwright install chromium
   ```

3. Run the UI suite:

   ```powershell
   .\.venv\Scripts\python.exe -m pytest .\test_ui.py -q -ra
   ```

4. The suite starts an isolated Flask server for each test and mocks browser API responses for deterministic results.

## 4. Test Data

| Data ID | Purpose | Value |
| --- | --- | --- |
| TD-001 | Search query | `Mahomes` |
| TD-002 | Suggested player | Patrick Mahomes, QB, KC |
| TD-003 | Trending player | Patrick Mahomes, QB, KC, 42 adds |
| TD-004 | Injury report | Patrick Mahomes, Questionable, Limited practice |
| TD-005 | News item | Mock NFL headline |
| TD-006 | Upcoming game | 2026, KC at BUF, Sun 1:00 PM |
| TD-007 | Comparison players | Christian McCaffrey and Patrick Mahomes |
| TD-008 | Mobile viewport | 390 x 844 pixels |

## 5. Test Cases

| ID | Test case | Preconditions | Test steps | Expected result | Status |
| --- | --- | --- | --- | --- | --- |
| UI-001 | Load homepage shell | App dependencies installed | Open `/` | Page title is `The Lab`; brand, player search field, and Search button are visible | Automated |
| UI-002 | Render upcoming games ticker | Homepage loaded; `/games` mocked with TD-006 | Open `/` and wait for ticker content | Ticker displays `KC at BUF` | Automated |
| UI-003 | Search for a player | Homepage loaded; `/suggest` mocked with TD-002 | Enter `Mahomes` in the player search field | A Patrick Mahomes suggestion appears | Automated |
| UI-004 | Lock a player from suggestions | UI-003 completed | Click the Patrick Mahomes suggestion | URL contains the selected player identity and Selected players shows Patrick Mahomes | Automated |
| UI-005 | Load Trending dropdown | Homepage loaded; `/trending` mocked with TD-003 | Hover over Trending | Dropdown opens and displays Patrick Mahomes | Automated |
| UI-006 | Load Injury Report dropdown | Homepage loaded; `/injuries` mocked with TD-004 | Hover over Injury Report | Dropdown opens and displays an injury item for Patrick Mahomes | Automated |
| UI-007 | Load Latest NFL News dropdown | Homepage loaded; `/news` mocked with TD-005 | Hover over Latest NFL News | Dropdown opens and displays Mock NFL headline | Automated |
| UI-008 | Open NFL Teams dropdown | Homepage loaded | Hover over NFL Teams | Team menu opens and contains a Kansas City Chiefs link for `team=KC` | Automated |
| UI-009 | Expose comparison action | Homepage loaded with TD-007 in the query string | Open the page with both players selected | Selected players panel displays Compare trade action | Automated |
| UI-010 | Preserve mobile search layout | Homepage loaded at TD-008 viewport | Set viewport to 390 x 844 and open `/` | Search surface remains within the viewport and the search input remains visible | Automated |

## 6. Acceptance Criteria

- All UI-001 through UI-010 tests pass in Chromium.
- Tests run against an isolated local Flask server.
- External data calls are mocked and do not make the result dependent on live provider availability.
- Failures identify the affected test ID and preserve enough detail for reproduction.
- The test command exits with code `0` for an accepted build.

## 7. Traceability

| Requirement area | Covered by |
| --- | --- |
| Homepage and search shell | UI-001 |
| Upcoming game ticker | UI-002 |
| Player autocomplete | UI-003 |
| Player selection persistence | UI-004 |
| Trending player data | UI-005 |
| Injury report data | UI-006 |
| NFL news data | UI-007 |
| NFL team navigation | UI-008 |
| Comparison setup | UI-009 |
| Responsive layout | UI-010 |

## 8. Execution Notes

The Playwright test module is implemented in `test_ui.py`. Playwright and Chromium were installed for the project environment. A complete final pytest summary was not captured because the terminal stopped returning reliable output after browser installation; the suite should be marked **Pass** only after the command in Section 3 completes with exit code `0`.

The existing backend test suite currently has unrelated failures in selected-player persistence, roster search ordering, and comparison scoring. Those are outside this browser UI plan and should be tracked separately.

## 9. Defect Recording Template

| Field | Value |
| --- | --- |
| Defect ID | `BUG-####` |
| Related test ID | `UI-###` |
| Summary |  |
| Steps to reproduce |  |
| Expected result |  |
| Actual result |  |
| Severity | Critical / High / Medium / Low |
| Browser and viewport |  |
| Evidence | Screenshot, trace, or console output |
| Owner |  |
| Resolution |  |
