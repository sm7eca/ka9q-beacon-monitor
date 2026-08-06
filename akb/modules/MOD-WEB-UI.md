---
id: MOD-WEB-UI
version: 1.0.1
status: DRAFT_FOR_REVIEW
title: Web UI
owner: Application Architecture
type: contract
normative: true
depends_on: [MOD-REST-API]
verified_by: [TEST-MOD-WEB-UI]
provides: [web-ui, beacon-overview]
consumes: [rest-api]
review:
  required: true
  passes: [contract-code, security, accessibility, test-traceability]
---
# Purpose
Define a read-only browser interface for current VHF beacon audibility.

# Scope
The module serves HTML, CSS and JavaScript and consumes the approved REST API. It does not calculate observations or summaries.

# Responsibilities
- Render a beacon overview.
- Retrieve beacon metadata and the latest interval summary.
- Refresh automatically at a configured interval.
- Present failures without corrupting the page.

# Definitions
- **Dashboard:** The page listing configured beacons and latest summary state.
- **Refresh interval:** Seconds between automatic REST API reads.
- **API base URL:** Prefix used for REST API requests.

# Interfaces
## Provides
- `GET /`
- `GET /assets/styles.css`
- `GET /assets/app.js`
- `GET /health`

## Consumes
- `GET {api_base_url}/beacons`
- `GET {api_base_url}/beacons/{beacon_id}/summaries?limit=1`

# Constraints
- The module SHALL be read-only.
- The module SHALL NOT contain classification, verification, aggregation or persistence logic.
- User-visible data SHALL be inserted with DOM text APIs rather than raw HTML interpolation.
- The default refresh interval SHALL be 30 seconds.

# Normative Requirements
- **MOD-WEB-UI-001:** The dashboard SHALL display every beacon returned by the REST API.
- **MOD-WEB-UI-002:** Each beacon card SHALL display identity, frequency, description, latest state and median effective SNR when available.
- **MOD-WEB-UI-003:** Missing summary data SHALL be presented as `no_data` and SHALL NOT be treated as an error.
- **MOD-WEB-UI-004:** REST API failures SHALL be presented in an accessible alert while preserving the last successful display.
- **MOD-WEB-UI-005:** Automatic refresh SHALL use the configured interval bounded to 5–3600 seconds.
- **MOD-WEB-UI-006:** Page title text SHALL be HTML-escaped.
- **MOD-WEB-UI-007:** Dynamic REST data SHALL be written through `textContent` or equivalent safe DOM APIs.
- **MOD-WEB-UI-008:** The dashboard response SHALL use `Cache-Control: no-store`; immutable assets MAY be cached.
- **MOD-WEB-UI-009:** The module SHALL expose a lightweight health endpoint independent of repository state.
- **MOD-WEB-UI-010:** No write route SHALL be exposed.
- **MOD-WEB-UI-011:** JSON embedded in HTML script elements SHALL escape literal `<` characters so `</script>` cannot terminate the intended element.

# Failure Modes
| Failure | Required behavior |
|---|---|
| Beacon request fails | Show accessible error message |
| One summary request fails | Treat refresh as failed; retain existing cards |
| Summary list empty | Show `no_data` |
| Invalid refresh interval | Reject configuration |
| Empty title | Reject configuration |

# Traceability
- `MOD-WEB-UI-001`–`011` → `tests/web/test_app.py`
- REST data contract → `MOD-REST-API`

# Review Questions
1. Is the module strictly presentation-only?
2. Are dynamic values inserted without `innerHTML`?
3. Are refresh and failure behaviors deterministic?
4. Does the review package include code, tests and this contract?

# Acceptance Criteria
- All M4.8 tests pass.
- No write endpoints exist.
- Required assets and configuration are served correctly.

# Change History
| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-08-06 | Initial M4.8 contract |
| 1.0.1 | 2026-08-06 | Hardened embedded configuration JSON against script-tag breakout |
