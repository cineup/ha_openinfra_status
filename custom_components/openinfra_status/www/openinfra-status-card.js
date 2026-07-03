/*
 * OpenInfra Status Card
 *
 * A dependency-free Lovelace card for the OpenInfra Status integration.
 * Ships with the integration and is auto-registered as a Lovelace resource,
 * so no Mushroom / stacked cards are required.
 *
 * Config:
 *   type: custom:openinfra-status-card
 *   entity: sensor.openinfra_<postcode>_netzwerkstatus   # the network_status sensor
 *
 * The view is routed directly off the enum state of the network_status sensor
 * (up / down / maintenance / disruption / recently_resolved). Details come from
 * that sensor's attributes. The general-info sensor is auto-discovered from the
 * same device via translation_key (language-independent) and can be overridden:
 *   general_info_entity, general_info_binary_entity, country_code_entity
 */

const CARD_VERSION = "1.0.0";

const STATUS_URL = "https://openinfra.tech";

// Auxiliary entities discovered from the same device via translation_key.
const ROLE_BY_TRANSLATION_KEY = {
  general_info: "general_info",
  general_info_active: "general_info_active",
  country_code: "country_code",
};

const LABELS = {
  en: {
    error: "Error",
    outage: "Network outage",
    disruption: "Network disruption",
    maintenance: "Planned maintenance",
    resolved: "Disruption resolved",
    ok: "OpenInfra OK",
    unknown: "Unknown",
    ok_secondary: "No disruptions found in your area.",
    since: "since",
    update: "Update",
    general_one: "1 general notice",
    general_many: "{n} general notices",
  },
  de: {
    error: "Fehler",
    outage: "Netzwerk ausgefallen",
    disruption: "Netzwerkstörung",
    maintenance: "Geplante Wartung",
    resolved: "Störung behoben",
    ok: "OpenInfra OK",
    unknown: "Unbekannt",
    ok_secondary: "Keine Störungen in Ihrem Bereich gefunden.",
    since: "seit",
    update: "Update",
    general_one: "1 allgemeine Meldung",
    general_many: "{n} allgemeine Meldungen",
  },
  sv: {
    error: "Fel",
    outage: "Nätverksavbrott",
    disruption: "Nätverksstörning",
    maintenance: "Planerat underhåll",
    resolved: "Störning åtgärdad",
    ok: "OpenInfra OK",
    unknown: "Okänt",
    ok_secondary: "Inga störningar hittades i ditt område.",
    since: "sedan",
    update: "Uppdatering",
    general_one: "1 allmänt meddelande",
    general_many: "{n} allmänna meddelanden",
  },
  nb: {
    error: "Feil",
    outage: "Nettverk nede",
    disruption: "Nettverksforstyrrelse",
    maintenance: "Planlagt vedlikehold",
    resolved: "Feil rettet",
    ok: "OpenInfra OK",
    unknown: "Ukjent",
    ok_secondary: "Ingen forstyrrelser funnet i ditt område.",
    since: "siden",
    update: "Oppdatering",
    general_one: "1 generell melding",
    general_many: "{n} generelle meldinger",
  },
};

// Per enum state: primary-label key, base icon, corner badge icon, badge color.
// The base icon stays a network device; the small badge carries the state color.
const STATE_STYLE = {
  up: { label: "ok", baseIcon: "mdi:network", badgeIcon: "mdi:check", color: "var(--success-color, #43a047)" },
  down: { label: "outage", baseIcon: "mdi:network-off", badgeIcon: "mdi:alert", color: "var(--error-color, #db4437)" },
  disruption: { label: "disruption", baseIcon: "mdi:network", badgeIcon: "mdi:alert", color: "var(--warning-color, #ffa600)" },
  maintenance: { label: "maintenance", baseIcon: "mdi:network", badgeIcon: "mdi:wrench-clock", color: "var(--warning-color, #ffa600)" },
  recently_resolved: { label: "resolved", baseIcon: "mdi:network", badgeIcon: "mdi:check-bold", color: "#1976d2" },
  unknown: { label: "unknown", baseIcon: "mdi:help-network-outline", badgeIcon: null, color: "var(--disabled-text-color, #9e9e9e)" },
};

const UNAVAILABLE = ["unknown", "unavailable", "none", ""];

function isEmpty(value) {
  if (value === null || value === undefined) return true;
  return UNAVAILABLE.includes(String(value).trim().toLowerCase());
}

// Parse an API timestamp. Naive timestamps (no timezone) are treated as UTC,
// matching the website JS and the integration's Python side.
function parseApiDate(value) {
  if (isEmpty(value)) return null;
  let v = String(value).trim().replace(" ", "T");
  const hasTz = /[zZ]$|[+-]\d{2}:?\d{2}$/.test(v);
  if (!hasTz) v += "Z";
  const d = new Date(v);
  return isNaN(d.getTime()) ? null : d;
}

class OpenInfraStatusCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
  }

  setConfig(config) {
    if (!config || !config.entity) {
      throw new Error("Please define the 'entity' (network_status sensor).");
    }
    this._config = config;
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() {
    return 3;
  }

  static getConfigElement() {
    return document.createElement("openinfra-status-card-editor");
  }

  static getStubConfig(hass) {
    const match = Object.keys(hass.states || {}).find(
      (id) =>
        id.startsWith("sensor.") &&
        /openinfra/i.test(id) &&
        hass.states[id].attributes &&
        hass.states[id].attributes.device_class === "enum"
    );
    return { type: "custom:openinfra-status-card", entity: match || "" };
  }

  get _lang() {
    const lang = (this._hass && this._hass.language) || "en";
    const short = lang.split("-")[0];
    return LABELS[short] ? short : "en";
  }

  get _t() {
    return LABELS[this._lang];
  }

  get _tz() {
    return (this._hass && this._hass.config && this._hass.config.time_zone) || undefined;
  }

  _fmtDateTime(date) {
    return new Intl.DateTimeFormat(this._lang, {
      timeZone: this._tz,
      day: "2-digit",
      month: "2-digit",
      year: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    }).format(date);
  }

  _fmtTime(date) {
    return new Intl.DateTimeFormat(this._lang, {
      timeZone: this._tz,
      hour: "2-digit",
      minute: "2-digit",
    }).format(date);
  }

  _duration(startDate) {
    const totalMin = Math.max(0, Math.floor((Date.now() - startDate.getTime()) / 60000));
    const h = Math.floor(totalMin / 60);
    const m = totalMin % 60;
    return `${h}:${String(m).padStart(2, "0")} h`;
  }

  // Resolve auxiliary entity ids from the same device via translation_key.
  _relatedEntities() {
    const cfg = this._config;
    const hass = this._hass;
    const roles = {
      general_info: cfg.general_info_entity,
      general_info_active: cfg.general_info_binary_entity,
      country_code: cfg.country_code_entity,
    };
    const registry = hass.entities || {};
    const mainReg = registry[cfg.entity];
    const deviceId = mainReg && mainReg.device_id;
    if (deviceId) {
      for (const [entityId, entry] of Object.entries(registry)) {
        if (entry.device_id !== deviceId) continue;
        const role = ROLE_BY_TRANSLATION_KEY[entry.translation_key];
        if (role && !roles[role]) roles[role] = entityId;
      }
    }
    return roles;
  }

  _state() {
    const main = this._hass.states[this._config.entity];
    const ns = main ? main.state : undefined;
    return STATE_STYLE[ns] ? ns : "unknown";
  }

  _primary(state) {
    // Variant A: the title is always just the state label; timing goes below.
    return this._t[STATE_STYLE[state].label];
  }

  _line(text) {
    return `<div class="status-line">${text}</div>`;
  }

  // Build the secondary block as structured elements (timing line + a combined
  // update/comment block) rather than a <br>-joined string, so the comment can
  // be clamped. The status-site link lives in the card's top-right corner.
  _secondaryHtml(state, attrs) {
    const t = this._t;
    const parts = [];

    if (state === "up") {
      return this._line(t.ok_secondary);
    }

    if (state === "maintenance") {
      if (!isEmpty(attrs.planned_work_title)) {
        parts.push(this._line(this._escape(attrs.planned_work_title)));
      }
      const start = parseApiDate(attrs.planned_work_start);
      const end = parseApiDate(attrs.planned_work_end);
      if (start) {
        let line = this._fmtDateTime(start);
        if (end) line += ` → ${this._fmtTime(end)}`;
        parts.push(this._line(line));
      }
      return parts.join("");
    }

    if (state === "down" || state === "disruption" || state === "recently_resolved") {
      // Timing line: down → "seit <start> · <duration>", resolved → "seit <end>".
      if (state === "down") {
        const start = parseApiDate(attrs.outage_start_time);
        if (start) {
          parts.push(this._line(`${t.since} ${this._fmtDateTime(start)} · ${this._duration(start)}`));
        }
      } else if (state === "recently_resolved") {
        const resolvedAt = parseApiDate(attrs.outage_resolved_at);
        if (resolvedAt) {
          parts.push(this._line(`${t.since} ${this._fmtDateTime(resolvedAt)}`));
        }
      }
      // Update time and comment share one line to stay compact; the whole
      // block is clamped to two lines via CSS.
      const commentTime = parseApiDate(attrs.latest_comment_time);
      const hasComment = !isEmpty(attrs.latest_comment);
      if (commentTime || hasComment) {
        const upd = commentTime
          ? `<span class="upd">${t.update}: ${this._fmtTime(commentTime)}</span>`
          : "";
        const text = hasComment ? this._escape(attrs.latest_comment) : "";
        const sep = upd && text ? " " : "";
        parts.push(`<div class="comment">${upd}${sep}${text}</div>`);
      }
    }
    return parts.join("");
  }

  _generalInfoHtml(related) {
    const hass = this._hass;
    const activeId = related.general_info_active;
    const infoId = related.general_info;
    if (!infoId) return "";
    if (activeId && hass.states[activeId] && hass.states[activeId].state !== "on") {
      return "";
    }
    const infoState = hass.states[infoId];
    if (!infoState) return "";
    const count = parseInt(infoState.state, 10);
    if (!count || count < 1) return "";

    const t = this._t;
    const heading = count === 1 ? t.general_one : t.general_many.replace("{n}", count);
    const attrs = infoState.attributes || {};
    const emoji = { maintenance: "🔧", warning: "⚠️", success: "✅" };

    const items = [];
    for (let i = 0; i < count; i++) {
      const title = attrs[`item_${i}_title`];
      if (isEmpty(title)) continue;
      const typ = attrs[`item_${i}_type`];
      const icon = emoji[typ] || "ℹ️";
      let line = `${icon} ${this._escape(title)}`;
      const start = parseApiDate(attrs[`item_${i}_start_time`]);
      const end = parseApiDate(attrs[`item_${i}_end_time`]);
      if (start) {
        line += ` · ${this._fmtDateTime(start)}`;
        if (end) line += ` → ${this._fmtDateTime(end)}`;
      } else if (end) {
        line += ` · ${this._fmtDateTime(end)}`;
      }
      items.push(`<div class="info-item">${line}</div>`);
    }
    if (!items.length) return "";

    return `
      <div class="divider"></div>
      <div class="general" data-action="open-url">
        <ha-icon class="info-icon" icon="mdi:information-outline"></ha-icon>
        <div class="general-body">
          <div class="general-heading">${this._escape(heading)}</div>
          ${items.join("")}
        </div>
      </div>`;
  }

  // Build https://openinfra.tech/<country>/?postcode=<postcode>.
  // Postcode: config → device name ("OpenInfra <postcode>") → entity_id slug.
  // Country: config → country_code sensor (lowercased) → UI language.
  _openInfraUrl(related) {
    const cfg = this._config;
    const hass = this._hass;

    let postcode = isEmpty(cfg.postcode) ? "" : String(cfg.postcode).trim();
    if (!postcode) {
      const mainReg = (hass.entities || {})[cfg.entity];
      const deviceId = mainReg && mainReg.device_id;
      const device = deviceId && hass.devices ? hass.devices[deviceId] : null;
      const deviceName = device && (device.name_by_user || device.name);
      if (deviceName) {
        const m = String(deviceName).match(/OpenInfra\s+(.+)$/i);
        if (m) postcode = m[1].trim();
      }
    }
    if (!postcode) {
      const objectId = (cfg.entity.split(".")[1] || "");
      const m = objectId.match(/^openinfra_(.+)_[^_]+$/);
      if (m) postcode = m[1].replace(/_/g, " ");
    }

    let country = isEmpty(cfg.country) ? "" : String(cfg.country).toLowerCase();
    if (!country) {
      const countryId = related.country_code;
      const cc = countryId && hass.states[countryId] && hass.states[countryId].state;
      if (!isEmpty(cc)) country = String(cc).toLowerCase();
    }
    if (!country) country = this._lang;

    const base = `${STATUS_URL}/${country}/`;
    return postcode ? `${base}?postcode=${encodeURIComponent(postcode)}` : base;
  }

  _escape(text) {
    return String(text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  _fireMoreInfo() {
    this.dispatchEvent(
      new CustomEvent("hass-more-info", {
        detail: { entityId: this._config.entity },
        bubbles: true,
        composed: true,
      })
    );
  }

  _render() {
    if (!this._hass || !this._config) return;
    const main = this._hass.states[this._config.entity];
    if (!main) {
      this.shadowRoot.innerHTML = `
        <ha-card>
          <div class="warn">${this._escape(this._config.entity)} — unavailable</div>
        </ha-card>`;
      return;
    }

    const related = this._relatedEntities();
    const state = this._state();
    const style = STATE_STYLE[state];
    const attrs = main.attributes || {};

    // URL must be set before building the secondary block (it renders the link).
    this._url = this._openInfraUrl(related);
    const primary = this._primary(state);
    const secondary = this._secondaryHtml(state, attrs);
    const general = this._generalInfoHtml(related);

    const badge = style.badgeIcon
      ? `<span class="badge" style="background:${style.color}"><ha-icon icon="${style.badgeIcon}"></ha-icon></span>`
      : "";

    this.shadowRoot.innerHTML = `
      <style>
        ha-card { position: relative; padding: var(--spacing, 12px); }
        .row {
          display: flex;
          align-items: flex-start;
          gap: var(--spacing, 12px);
          cursor: pointer;
        }
        .icon-wrap {
          position: relative;
          flex: 0 0 auto;
          width: 34px;
          height: 34px;
          display: flex;
          align-items: center;
          justify-content: center;
        }
        .base-icon {
          --mdc-icon-size: 24px;
          color: var(--primary-text-color);
        }
        .badge {
          position: absolute;
          right: -1px;
          top: -1px;
          width: 16px;
          height: 16px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          border: 2px solid var(--card-background-color, #fff);
          box-sizing: border-box;
        }
        .badge ha-icon {
          --mdc-icon-size: 10px;
          color: #fff;
        }
        .text { min-width: 0; flex: 1 1 auto; }
        .primary {
          font-weight: var(--card-primary-font-weight, bold);
          font-size: var(--card-primary-font-size, 14px);
          line-height: var(--card-primary-line-height, 1.4);
          color: var(--primary-text-color);
          padding-right: 22px;
        }
        .secondary {
          margin-top: 2px;
          font-size: var(--card-secondary-font-size, 12px);
          font-weight: var(--card-secondary-font-weight, normal);
          line-height: var(--card-secondary-line-height, 1.4);
          color: var(--secondary-text-color);
        }
        .status-line { word-break: break-word; }
        .upd { color: var(--primary-text-color); }
        .comment {
          display: -webkit-box;
          -webkit-line-clamp: 2;
          line-clamp: 2;
          -webkit-box-orient: vertical;
          overflow: hidden;
          word-break: break-word;
        }
        .url-badge {
          position: absolute;
          top: var(--spacing, 12px);
          right: var(--spacing, 12px);
          color: var(--secondary-text-color);
          --mdc-icon-size: 18px;
          cursor: pointer;
          opacity: 0.7;
        }
        .url-badge:hover { opacity: 1; }
        .divider {
          height: 1px;
          background: var(--divider-color, rgba(0,0,0,0.12));
          margin: 12px 0;
        }
        .general {
          display: flex;
          gap: 14px;
          align-items: flex-start;
          cursor: pointer;
        }
        .info-icon {
          flex: 0 0 auto;
          color: var(--info-color, #039be5);
          --mdc-icon-size: 22px;
          margin-top: 2px;
        }
        .general-heading {
          font-weight: 600;
          color: var(--primary-text-color);
          margin-bottom: 4px;
        }
        .info-item {
          font-size: 0.9rem;
          line-height: 1.35;
          color: var(--secondary-text-color);
          word-break: break-word;
        }
        .warn { padding: 12px; color: var(--error-color, #db4437); }
      </style>
      <ha-card>
        <ha-icon class="url-badge" data-action="open-url" icon="mdi:open-in-new" title="openinfra.tech"></ha-icon>
        <div class="row" data-action="more-info">
          <div class="icon-wrap">
            <ha-icon class="base-icon" icon="${style.baseIcon}"></ha-icon>
            ${badge}
          </div>
          <div class="text">
            <div class="primary">${this._escape(primary)}</div>
            ${secondary ? `<div class="secondary">${secondary}</div>` : ""}
          </div>
        </div>
        ${general}
      </ha-card>`;

    const moreInfoEl = this.shadowRoot.querySelector('[data-action="more-info"]');
    if (moreInfoEl) {
      moreInfoEl.addEventListener("click", () => this._fireMoreInfo());
    }
    // The corner symbol and the general-info section open the status site
    // without triggering the more-info dialog.
    this.shadowRoot.querySelectorAll('[data-action="open-url"]').forEach((el) => {
      el.addEventListener("click", (ev) => {
        ev.stopPropagation();
        window.open(this._url, "_blank", "noopener");
      });
    });
  }
}

class OpenInfraStatusCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = config;
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _render() {
    if (!this._hass) return;
    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.addEventListener("value-changed", (ev) => {
        this.dispatchEvent(
          new CustomEvent("config-changed", {
            detail: { config: ev.detail.value },
            bubbles: true,
            composed: true,
          })
        );
      });
      this._form.computeLabel = (schema) =>
        schema.name === "entity" ? "OpenInfra network status sensor" : schema.name;
      this.appendChild(this._form);
    }
    this._form.hass = this._hass;
    this._form.data = this._config || {};
    this._form.schema = [
      {
        name: "entity",
        required: true,
        selector: {
          entity: { integration: "openinfra_status", domain: "sensor", device_class: "enum" },
        },
      },
    ];
  }
}

customElements.define("openinfra-status-card", OpenInfraStatusCard);
customElements.define("openinfra-status-card-editor", OpenInfraStatusCardEditor);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "openinfra-status-card",
  name: "OpenInfra Status Card",
  description: "Network status, disruptions, planned work and general info from OpenInfra.",
  preview: true,
  documentationURL: "https://github.com/cineup/ha_openinfra_status",
});

// eslint-disable-next-line no-console
console.info(
  `%c OPENINFRA-STATUS-CARD %c v${CARD_VERSION} `,
  "color:#fff;background:#039be5;font-weight:700",
  "color:#039be5;background:#fff"
);
