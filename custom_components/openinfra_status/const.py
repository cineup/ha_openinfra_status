"""Constants for the OpenInfra Status integration."""

DOMAIN = "openinfra_status"

API_URL = "https://openinfra.tech/api/status"
API_GENERAL_URL = "https://openinfra.tech/api/general"
API_TIMEOUT = 10

CONF_COUNTRY = "country"
CONF_POSTCODE = "postcode"

DEFAULT_SCAN_INTERVAL_MINUTES = 10

# ---------------------------------------------------------------------------
# OpenInfra API field reference
# ---------------------------------------------------------------------------
#
# The integration uses two API endpoints:
#
#   1. GET /api/status?country=<cc>&postcode=<zip>
#      Postcode-specific network status.
#
#   2. GET /api/general?country=<cc>
#      General maintenance/outage information (not postcode-specific).
#
# Field classifications:
#   CONFIRMED  = observed in a real API response
#   JS-CONFIRMED = confirmed via website JavaScript source code analysis
#                  (NetworkStatusChecker.CMeFtdnm.js, analysed 2026-03-12)
#   LOCAL      = generated/tracked client-side, not from API
#
# ---- /api/status endpoint -------------------------------------------------
#
# CONFIRMED fields (observed 2026-03-12, status "up"):
#
#   Field             Type      Example             Notes
#   ─────────────────────────────────────────────────────────────────────
#   success           bool      true                Indicates a valid response
#   error             bool      false               Always boolean (see below)
#   network_status    string    "up"                Known value: "up"
#   is_down           bool      false               Always boolean (see below)
#   is_planned_work   bool      false               Boolean flag
#   country_code      string    "DE"                Uppercase country code
#   detected_region   string    "se"                Region detected by backend
#   request_url       string    "API call for ..."  Debug / echo of request
#   response_code     int       200                 HTTP-level status echo
#
# JS-CONFIRMED fields (from website JS, structure verified):
#
#   -- Error state --
#   error             bool      true                Stays boolean (NOT dict!)
#   error_message     string    "Service unavail."  Separate field for message
#
#   -- Disruption state (is_down === true) --
#   is_down           bool      true                Stays boolean (NOT dict!)
#   outage_start_time string    ISO 8601            When outage started (API-side)
#   comments          array     [{text, timestamp}] Update history (newest first)
#   latest_comment    object    {text, timestamp}    Fallback if comments missing
#
#   -- Planned work state (is_planned_work === true) --
#   planned_work      dict                          Contains work details:
#     .title          string                          Title of planned work
#     .description    string                          Description
#     .start_time     string    ISO 8601 / datetime   Start time
#     .end_time       string    ISO 8601 / datetime   End time (optional)
#   planned_work_status string  "scheduled"|other   "scheduled" = future, else active
#
#   -- Recently resolved state --
#   is_recently_resolved bool   true                Outage recently fixed
#   end_time          string    ISO 8601            When outage ended
#   outage_resolved_at string   ISO 8601            Alternative resolution time
#   resolved_within_hours int   2                   Hours since resolution
#   outage_start_time string    ISO 8601            When outage had started
#   comments          array     [{text, timestamp}] Update history
#
# ---- /api/general endpoint ------------------------------------------------
#
# JS-CONFIRMED fields:
#
#   Field             Type      Example             Notes
#   ─────────────────────────────────────────────────────────────────────
#   has_info          bool      true                Whether info items exist
#   info              array                         Array of info items:
#     .title          string                          Item title
#     .message        string                          Item message (may have \n)
#     .type           string    "warning"|"maintenance"|"success"|"info"
#
# ---- Fields NOT used by this integration ----------------------------------
#   request_url, response_code, postal_code
#
# ---- CORRECTED assumptions (previously speculated, now disproven) ----------
#   - "error" does NOT become a dict; error text is in "error_message"
#   - "is_down" does NOT become a dict; disruption text is in "comments"
#   - "affected_services" does NOT exist in the API
#   - "planned_work_status" uses "scheduled" (not "upcoming")
# ---------------------------------------------------------------------------
