const CARD_TYPE = "predictive-thermostat-card";

const TEXT = {
  en: {
    menu: "Predictive heating details", close: "Close predictive heating details",
    controlState: "Control state", heater: "Heater", available: "Available",
    unavailable: "Unavailable", outdoor: "Outdoor temperature",
    scheduleTarget: "Schedule target", nextTarget: "Next target", nextTime: "Target time",
    predictedStart: "Predicted start", predictedDuration: "Predicted heating time",
    confidence: "Prediction confidence", predictionReason: "Prediction source",
    samples: "Learning samples", lastError: "Last prediction error",
    fallback: "Fallback reason", fault: "Fault", pending: "Pending command",
    none: "None", reset: "Acknowledge fault", resetLong: "Resume after long outage",
    confirmLong: "Confirm that the heater has actually remained off for at least the minimum off time and cooldown?",
    success: "Reset request accepted.", failed: "Reset failed", minutes: "min",
  },
  fr: {
    menu: "Détails de la chauffe prédictive", close: "Fermer les détails de la chauffe prédictive",
    controlState: "État du contrôle", heater: "Chauffage", available: "Disponible",
    unavailable: "Indisponible", outdoor: "Température extérieure",
    scheduleTarget: "Consigne planifiée", nextTarget: "Prochaine consigne", nextTime: "Heure cible",
    predictedStart: "Démarrage prévu", predictedDuration: "Durée de chauffe prévue",
    confidence: "Confiance de la prédiction", predictionReason: "Source de la prédiction",
    samples: "Cycles appris", lastError: "Dernière erreur de prédiction",
    fallback: "Motif du repli", fault: "Défaut", pending: "Commande en attente",
    none: "Aucun", reset: "Acquitter le défaut", resetLong: "Reprendre après coupure longue",
    confirmLong: "Confirmer que le chauffage est réellement resté éteint pendant au moins la durée minimale d’arrêt et le cooldown ?",
    success: "Demande de réinitialisation acceptée.", failed: "Échec de la réinitialisation", minutes: "min",
  },
};

class PredictiveThermostatCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._expanded = false;
    this._nativeCard = null;
  }

  setConfig(config) {
    if (!config.entity || !config.entity.startsWith("climate.")) {
      throw new Error("Predictive Thermostat card requires a climate entity");
    }
    this._config = { ...config };
    this._build();
    this._ensureNativeCard();
  }

  set hass(hass) {
    this._hass = hass;
    if (this._nativeCard) this._nativeCard.hass = hass;
    this._update();
  }

  getCardSize() { return this._expanded ? 8 : 5; }
  _language() { return this._hass?.language?.toLowerCase().startsWith("fr") ? "fr" : "en"; }
  _t(key) { return TEXT[this._language()][key]; }

  _build() {
    if (!this.shadowRoot || this.shadowRoot.childElementCount) return;
    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; position: relative; }
        #native { min-height: 120px; }
        .menu-button { position: absolute; top: 8px; right: 8px; z-index: 2; width: 40px; height: 40px; padding: 8px; border: 0; border-radius: 50%; color: var(--primary-text-color); background: transparent; cursor: pointer; }
        .menu-button:hover { background: var(--secondary-background-color); }
        .menu-button:focus-visible { outline: 2px solid var(--primary-color); }
        .menu-button ha-icon { pointer-events: none; }
        .details { margin-top: 8px; padding: 16px; }
        .details[hidden] { display: none; }
        h2 { margin: 0 0 14px; font-size: 18px; font-weight: 500; }
        dl { display: grid; grid-template-columns: minmax(130px, 1fr) 1fr; gap: 8px 16px; margin: 0; }
        dt { color: var(--secondary-text-color); }
        dd { margin: 0; overflow-wrap: anywhere; }
        .actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 18px; }
        ha-button { flex: 1 1 190px; }
        .status { min-height: 20px; margin-top: 10px; color: var(--secondary-text-color); }
        .status.error { color: var(--error-color); }
        @media (max-width: 450px) { dl { grid-template-columns: 1fr; gap: 2px; } dd { margin-bottom: 8px; } }
      </style>
      <div id="native"></div>
      <button class="menu-button" type="button"><ha-icon icon="mdi:menu"></ha-icon></button>
      <ha-card class="details" hidden>
        <h2></h2><dl></dl>
        <div class="actions"><ha-button class="reset" appearance="filled"></ha-button><ha-button class="reset-long"></ha-button></div>
        <div class="status" role="status" aria-live="polite"></div>
      </ha-card>`;
    this.shadowRoot.querySelector(".menu-button").addEventListener("click", () => {
      this._expanded = !this._expanded;
      this._update();
      this.dispatchEvent(new Event("iron-resize", { bubbles: true, composed: true }));
    });
    this.shadowRoot.querySelector(".reset").addEventListener("click", () => this._reset(false));
    this.shadowRoot.querySelector(".reset-long").addEventListener("click", () => this._reset(true));
  }

  async _ensureNativeCard() {
    const helpers = await window.loadCardHelpers();
    if (!this._config || this._nativeCard) return;
    const cardConfig = { type: "thermostat", entity: this._config.entity };
    if (this._config.name) cardConfig.name = this._config.name;
    this._nativeCard = await helpers.createCardElement(cardConfig);
    this.shadowRoot.querySelector("#native").replaceChildren(this._nativeCard);
    if (this._hass) this._nativeCard.hass = this._hass;
  }

  _formatDate(value) {
    if (!value) return this._t("none");
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value);
    return new Intl.DateTimeFormat(this._language(), { weekday: "short", hour: "2-digit", minute: "2-digit" }).format(date);
  }

  _number(value, suffix = "") {
    if (value === null || value === undefined) return this._t("none");
    const number = Number(value);
    if (!Number.isFinite(number)) return String(value);
    return `${new Intl.NumberFormat(this._language(), { maximumFractionDigits: 1 }).format(number)}${suffix}`;
  }

  _rows(attributes) {
    const confidence = attributes.prediction_confidence == null
      ? this._t("none") : this._number(Number(attributes.prediction_confidence) * 100, " %");
    return [
      ["controlState", attributes.control_state], ["heater", attributes.heater_available ? "available" : "unavailable", true],
      ["fault", attributes.fault_reason], ["pending", attributes.pending_command],
      ["outdoor", this._number(attributes.outdoor_temperature, " °C")],
      ["scheduleTarget", this._number(attributes.schedule_target_temperature, " °C")],
      ["nextTarget", this._number(attributes.next_target_temperature, " °C")],
      ["nextTime", this._formatDate(attributes.next_target_time)],
      ["predictedStart", this._formatDate(attributes.predicted_start_time)],
      ["predictedDuration", this._number(attributes.predicted_heating_minutes, ` ${this._t("minutes")}`)],
      ["confidence", confidence], ["predictionReason", attributes.prediction_reason],
      ["samples", this._number(attributes.learning_samples)],
      ["lastError", this._number(attributes.last_prediction_error_minutes, ` ${this._t("minutes")}`)],
      ["fallback", attributes.fallback_reason],
    ];
  }

  _update() {
    if (!this.shadowRoot || !this._config) return;
    const details = this.shadowRoot.querySelector(".details");
    const button = this.shadowRoot.querySelector(".menu-button");
    details.hidden = !this._expanded;
    button.title = this._t(this._expanded ? "close" : "menu");
    button.setAttribute("aria-label", button.title);
    button.setAttribute("aria-expanded", String(this._expanded));
    this.shadowRoot.querySelector("h2").textContent = this._t("menu");
    this.shadowRoot.querySelector(".reset").textContent = this._t("reset");
    this.shadowRoot.querySelector(".reset-long").textContent = this._t("resetLong");
    const state = this._hass?.states?.[this._config.entity];
    if (!state) return;
    const list = this.shadowRoot.querySelector("dl");
    list.replaceChildren();
    for (const [label, rawValue, translateValue] of this._rows(state.attributes)) {
      const term = document.createElement("dt");
      const value = document.createElement("dd");
      term.textContent = this._t(label);
      value.textContent = translateValue ? this._t(rawValue)
        : rawValue === null || rawValue === undefined || rawValue === "" ? this._t("none") : String(rawValue);
      list.append(term, value);
    }
  }

  async _reset(confirmedOffPeriod) {
    if (confirmedOffPeriod && !window.confirm(this._t("confirmLong"))) return;
    const status = this.shadowRoot.querySelector(".status");
    status.textContent = "";
    status.classList.remove("error");
    try {
      await this._hass.callService("predictive_thermostat", "reset_fault", {
        entity_id: this._config.entity, confirmed_off_period: confirmedOffPeriod,
      });
      status.textContent = this._t("success");
    } catch (error) {
      status.textContent = `${this._t("failed")}: ${error?.message || error}`;
      status.classList.add("error");
    }
  }
}

if (!customElements.get(CARD_TYPE)) {
  customElements.define(CARD_TYPE, PredictiveThermostatCard);
  window.customCards = window.customCards || [];
  window.customCards.push({ type: CARD_TYPE, name: "Predictive Thermostat", description: "Native thermostat controls with predictive heating details and fault reset actions." });
}
