"""Constants for the OpenInfra Status integration."""

DOMAIN = "openinfra_status"

API_URL = "https://openinfra.tech/api/status"
API_TIMEOUT = 10

CONF_COUNTRY = "country"
CONF_POSTCODE = "postcode"

DEFAULT_SCAN_INTERVAL_MINUTES = 10

# ---------------------------------------------------------------------------
# OpenInfra API field reference
# ---------------------------------------------------------------------------
# Endpoint: GET https://openinfra.tech/api/status?country=<cc>&postcode=<zip>
#
# The sections below classify each field as CONFIRMED (observed in a real API
# response) or SPECULATED (assumed based on field naming conventions; never
# verified against an actual response).  When maintaining sensors keep this
# distinction in mind so that no speculated structure is silently trusted.
#
# ---- CONFIRMED fields (observed 2026-03-12, status "up") -----------------
#
#   Field             Type      Example             Notes
#   ─────────────────────────────────────────────────────────────────────
#   success           bool      true                Indicates a valid response
#   error             bool      false               Boolean when no error (*)
#   network_status    string    "up"                Known value: "up"
#   is_down           bool      false               Boolean when no disruption
#   is_planned_work   bool      false               Boolean when no planned work
#   country_code      string    "DE"                Uppercase country code
#   detected_region   string    "se"                Region detected by backend
#   request_url       string    "API call for ..."  Debug / echo of request
#   response_code     int       200                 HTTP-level status echo
#
# (*) The "error" field is a plain boolean (false) in the normal case.
#     It is unknown whether it becomes a dict with title/description on error
#     or stays boolean true.  The integration handles both possibilities.
#
# ---- SPECULATED fields (never observed, structure assumed) ----------------
#
#   Field                       Assumed type    Used by
#   ─────────────────────────────────────────────────────────────────────
#   planned_work                dict | null     sensor: planned_work_title,
#     .title                    string            planned_work_description,
#     .description              string            planned_work_start,
#     .start_time               ISO 8601 str      planned_work_end
#     .end_time                 ISO 8601 str    binary_sensor: planned_work_active
#   planned_work_status         string          sensor: planned_work_status
#                               ("upcoming"|"active"|"completed")
#   is_down (as dict)           dict | bool     sensor: disruption_title,
#     .title                    string            disruption_description
#     .description              string          binary_sensor: disruption_active
#   error (as dict)             dict | bool     sensor: error_title,
#     .title                    string            error_description
#     .description              string          binary_sensor: error_active
#   network_status values       string          sensor: network_status (ENUM)
#     "down", "maintenance",                    Only "up" has been confirmed;
#     "disruption"                              others are assumed possible.
#
# ---- Fields NOT used by this integration ----------------------------------
#   request_url, response_code, postal_code
#
# When the API is observed in a disruption / planned-work / error state the
# speculated fields above should be verified and this table updated.
# ---------------------------------------------------------------------------
