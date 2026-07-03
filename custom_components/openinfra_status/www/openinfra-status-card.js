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

const COMMENT_MAX = 120;

// Auxiliary entities discovered from the same device via translation_key.
const ROLE_BY_TRANSLATION_KEY = {
  general_info: "general_info",
  general_info_active: "general_info_active",
  country_code: "country_code",
};

const LABELS = {
  en: {
    error: "Error",
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

// Primary-label key + icon + color per enum state. Colors use theme variables.
const STATE_STYLE = {
  up: { label: "ok", icon: "mdi:check-bold", color: "var(--success-color, #43a047)" },
  down: { label: "disruption", icon: "mdi:network-off", color: "var(--error-color, #db4437)" },
  disruption: { label: "disruption", icon: "mdi:network-off", color: "var(--error-color, #db4437)" },
  maintenance: { label: "maintenance", icon: "mdi:wrench-clock", color: "var(--warning-color, #ffa600)" },
  recently_resolved: { label: "resolved", icon: "mdi:check-circle", color: "var(--info-color, #039be5)" },
  unknown: { label: "unknown", icon: "mdi:help-circle", color: "var(--disabled-text-color, #9e9e9e)" },
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

  _comment(text) {
    const c = String(text);
    return this._escape(c.length > COMMENT_MAX ? c.slice(0, COMMENT_MAX) + "…" : c);
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

  _primary(state, attrs) {
    const t = this._t;
    const base = t[STATE_STYLE[state].label];

    if (state === "down") {
      const start = parseApiDate(attrs.outage_start_time);
      if (start) {
        return `${this._duration(start)} · ${base} · ${t.since} ${this._fmtDateTime(start)}`;
      }
    }
    if (state === "recently_resolved") {
      const resolvedAt = parseApiDate(attrs.outage_resolved_at);
      if (resolvedAt) {
        return `${base} · ${t.since} ${this._fmtDateTime(resolvedAt)}`;
      }
    }
    return base;
  }

  _secondaryHtml(state, attrs) {
    const t = this._t;
    const parts = [];

    if (state === "up") {
      return t.ok_secondary;
    }

    if (state === "maintenance") {
      if (!isEmpty(attrs.planned_work_title)) {
        parts.push(this._escape(attrs.planned_work_title));
      }
      const start = parseApiDate(attrs.planned_work_start);
      const end = parseApiDate(attrs.planned_work_end);
      if (start) {
        let line = this._fmtDateTime(start);
        if (end) line += ` → ${this._fmtTime(end)}`;
        parts.push(line);
      }
      return parts.join("<br>");
    }

    // down / disruption / recently_resolved: latest update + comment
    if (state === "down" || state === "disruption" || state === "recently_resolved") {
      const commentTime = parseApiDate(attrs.latest_comment_time);
      if (commentTime) {
        parts.push(`${t.update} ${this._fmtTime(commentTime)}`);
      }
      if (!isEmpty(attrs.latest_comment)) {
        parts.push(this._comment(attrs.latest_comment));
      }
    }
    return parts.join("<br>");
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

  _openInfraUrl(related) {
    let postcode = "";
    const hass = this._hass;
    const mainReg = (hass.entities || {})[this._config.entity];
    const deviceId = mainReg && mainReg.device_id;
    const device = deviceId && hass.devices ? hass.devices[deviceId] : null;
    const deviceName = device && (device.name_by_user || device.name);
    if (deviceName) {
      const m = String(deviceName).match(/OpenInfra\s+(.+)$/i);
      if (m) postcode = m[1].trim();
    }
    let lang = this._lang;
    const countryId = related.country_code;
    if (countryId && hass.states[countryId] && !isEmpty(hass.states[countryId].state)) {
      lang = String(hass.states[countryId].state).toLowerCase();
    }
    const base = `${STATUS_URL}/${lang}/`;
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

    const primary = this._primary(state, attrs);
    const secondary = this._secondaryHtml(state, attrs);
    const general = this._generalInfoHtml(related);
    this._url = this._openInfraUrl(related);

    this.shadowRoot.innerHTML = `
      <style>
        ha-card { padding: 12px 16px; }
        .row {
          display: flex;
          align-items: center;
          gap: 14px;
          cursor: pointer;
        }
        .icon-wrap {
          flex: 0 0 auto;
          width: 42px;
          height: 42px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          background: ${style.color};
        }
        .icon-wrap ha-icon {
          --mdc-icon-size: 24px;
          color: #fff;
        }
        .text { min-width: 0; flex: 1 1 auto; }
        .primary {
          font-weight: 600;
          font-size: 1.05rem;
          color: var(--primary-text-color);
        }
        .secondary {
          margin-top: 2px;
          font-size: 0.9rem;
          line-height: 1.3;
          color: var(--secondary-text-color);
          word-break: break-word;
        }
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
        <div class="row" data-action="more-info">
          <div class="icon-wrap"><ha-icon icon="${style.icon}"></ha-icon></div>
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
    const urlEl = this.shadowRoot.querySelector('[data-action="open-url"]');
    if (urlEl) {
      urlEl.addEventListener("click", (ev) => {
        ev.stopPropagation();
        window.open(this._url, "_blank", "noopener");
      });
    }
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
