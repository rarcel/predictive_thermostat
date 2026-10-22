const CARD_TYPE = "predictive-thermostat-card";

const TEXT = {
  en: {
    menu: "Predictive heating details", close: "Close", nativeInfo: "Home Assistant details",
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
    menu: "Détails de la chauffe prédictive", close: "Fermer", nativeInfo: "Informations Home Assistant",
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

  getCardSize() { return 7; }
  _language() { return this._hass?.language?.toLowerCase().startsWith("fr") ? "fr" : "en"; }
  _t(key) { return TEXT[this._language()][key]; }

  _build() {
    if (!this.shadowRoot || this.shadowRoot.childElementCount) return;
    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; }
        #native { min-height: 120px; }
        dialog { width: min(560px, calc(100vw - 32px)); max-height: calc(100vh - 48px); box-sizing: border-box; padding: 20px; border: 0; border-radius: var(--ha-card-border-radius, 12px); color: var(--primary-text-color); background: var(--card-background-color); box-shadow: var(--ha-card-box-shadow); overflow: auto; }
        dialog::backdrop { background: rgba(0, 0, 0, 0.48); }
        h2 { margin: 0 0 14px; font-size: 18px; font-weight: 500; }
        dl { display: grid; grid-template-columns: minmax(130px, 1fr) 1fr; gap: 8px 16px; margin: 0; }
        dt { color: var(--secondary-text-color); }
        dd { margin: 0; overflow-wrap: anywhere; }
        .actions, .footer { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 18px; }
        ha-button { flex: 1 1 190px; }
        .footer { justify-content: flex-end; border-top: 1px solid var(--divider-color); padding-top: 12px; }
        .footer ha-button { flex: 0 1 auto; }
        .status { min-height: 20px; margin-top: 10px; color: var(--secondary-text-color); }
        .status.error { color: var(--error-color); }
        @media (max-width: 450px) { dl { grid-template-columns: 1fr; gap: 2px; } dd { margin-bottom: 8px; } }
      </style>
      <div id="native"></div>
      <dialog class="details">
        <h2></h2><dl></dl>
        <div class="actions"><ha-button class="reset" appearance="filled"></ha-button><ha-button class="reset-long"></ha-button></div>
        <div class="status" role="status" aria-live="polite"></div>
        <div class="footer"><ha-button class="native-info"></ha-button><ha-button class="close"></ha-button></div>
      </dialog>`;
    this.shadowRoot.querySelector(".reset").addEventListener("click", () => this._reset(false));
    this.shadowRoot.querySelector(".reset-long").addEventListener("click", () => this._reset(true));
    this.shadowRoot.querySelector(".native-info").addEventListener("click", () => this._openNativeInfo());
    this.shadowRoot.querySelector(".close").addEventListener("click", () => this._closeDetails());
    this.shadowRoot.querySelector("dialog").addEventListener("click", (event) => {
      if (event.target === event.currentTarget) this._closeDetails();
    });
  }

  async _ensureNativeCard() {
    const helpers = await window.loadCardHelpers();
    if (!this._config || this._nativeCard) return;
    const cardConfig = { type: "thermostat", entity: this._config.entity };
    if (this._config.name) cardConfig.name = this._config.name;
    this._nativeCard = await helpers.createCardElement(cardConfig);
    this._nativeCard.addEventListener("hass-more-info", (event) => this._openDetails(event));
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
    this.shadowRoot.querySelector("h2").textContent = this._t("menu");
    this.shadowRoot.querySelector(".reset").textContent = this._t("reset");
    this.shadowRoot.querySelector(".reset-long").textContent = this._t("resetLong");
    this.shadowRoot.querySelector(".native-info").textContent = this._t("nativeInfo");
    this.shadowRoot.querySelector(".close").textContent = this._t("close");
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

  _openDetails(event) {
    event.preventDefault();
    event.stopPropagation();
    this._update();
    const dialog = this.shadowRoot.querySelector("dialog");
    if (!dialog.open) dialog.showModal();
  }

  _closeDetails() {
    const dialog = this.shadowRoot.querySelector("dialog");
    if (dialog.open) dialog.close();
  }

  _openNativeInfo() {
    this._closeDetails();
    this.dispatchEvent(new CustomEvent("hass-more-info", {
      detail: { entityId: this._config.entity }, bubbles: true, composed: true,
    }));
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
