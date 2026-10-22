const CARD_TYPE = "predictive-thermostat-card";

const TEXT = {
  en: {
    menu: "Predictive heating details", details: "Predictive details", close: "Close",
    controlState: "Control state", heater: "Heater", available: "Available",
    unavailable: "Unavailable", outdoor: "Outdoor temperature",
    predictionOutdoor: "Outdoor temperature used", outdoorSource: "Outdoor data source",
    forecast: "Weather forecast", sensor: "Outdoor sensor",
    scheduleTarget: "Schedule target", nextTarget: "Next target", nextTime: "Target time",
    predictedStart: "Predicted start", predictedDuration: "Predicted heating time",
    confidence: "Prediction confidence", predictionReason: "Prediction source",
    samples: "Learning samples", lastError: "Last prediction error",
    learnedRate: "Learned heating rate", learnedLoss: "Learned outdoor loss",
    ignitionPart: "Ignition delay", gainPart: "Temperature rise",
    outdoorPart: "Outdoor correction", marginPart: "Safety margin",
    arrivalPart: "Arrival correction", rawDuration: "Duration before limits",
    fallback: "Fallback reason", fault: "Fault", pending: "Pending command",
    none: "None", reset: "Acknowledge fault", resetLong: "Resume after long outage",
    confirmLong: "Confirm that the heater has actually remained off for at least the minimum off time and cooldown?",
    success: "Reset request accepted.", failed: "Reset failed", minutes: "min",
  },
  fr: {
    menu: "Détails de la chauffe prédictive", details: "Détails prédictifs", close: "Fermer",
    controlState: "État du contrôle", heater: "Chauffage", available: "Disponible",
    unavailable: "Indisponible", outdoor: "Température extérieure",
    predictionOutdoor: "Température extérieure utilisée", outdoorSource: "Source extérieure utilisée",
    forecast: "Prévision météo", sensor: "Sonde extérieure",
    scheduleTarget: "Consigne planifiée", nextTarget: "Prochaine consigne", nextTime: "Heure cible",
    predictedStart: "Démarrage prévu", predictedDuration: "Durée de chauffe prévue",
    confidence: "Confiance de la prédiction", predictionReason: "Source de la prédiction",
    samples: "Cycles appris", lastError: "Dernière erreur de prédiction",
    learnedRate: "Vitesse de chauffe apprise", learnedLoss: "Perte extérieure apprise",
    ignitionPart: "Délai d’allumage", gainPart: "Montée en température",
    outdoorPart: "Correction extérieure", marginPart: "Marge de sécurité",
    arrivalPart: "Correction d’arrivée", rawDuration: "Durée avant bornage",
    fallback: "Motif du repli", fault: "Défaut", pending: "Commande en attente",
    none: "Aucun", reset: "Acquitter le défaut", resetLong: "Reprendre après coupure longue",
    confirmLong: "Confirmer que le chauffage est réellement resté éteint pendant au moins la durée minimale d’arrêt et le cooldown ?",
    success: "Demande de réinitialisation acceptée.", failed: "Échec de la réinitialisation", minutes: "min",
  },
};

const language = (hass) => hass?.language?.toLowerCase().startsWith("fr") ? "fr" : "en";

class PredictiveDetailsCardFeature extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this.shadowRoot.innerHTML = `
      <style>
        button { width: 100%; height: var(--feature-height, 42px); border: 0; border-radius: var(--feature-border-radius, 12px); color: var(--primary-text-color); background: var(--secondary-background-color); font: inherit; font-weight: 500; cursor: pointer; }
        button:hover { background: var(--ha-color-fill-primary-loud-resting, var(--divider-color)); }
        button:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 2px; }
      </style><button type="button"></button>`;
    this.shadowRoot.querySelector("button").addEventListener("click", (event) => {
      event.stopPropagation();
      this.dispatchEvent(new CustomEvent("predictive-thermostat-show-details", {
        bubbles: true, composed: true,
      }));
    });
  }

  setConfig(config) { this._config = config; }
  set context(context) { this._context = context; }
  set hass(hass) {
    this._hass = hass;
    this.shadowRoot.querySelector("button").textContent = TEXT[language(hass)].details;
  }
}

class PredictiveThermostatCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._nativeCard = null;
    this._nativeCardPromise = null;
  }

  setConfig(config) {
    if (!config.entity || !config.entity.startsWith("climate.")) {
      throw new Error("Predictive Thermostat card requires a climate entity");
    }
    this._config = { ...config };
    this._build();
    if (this._hass) this._ensureNativeCard();
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._nativeCard) this._ensureNativeCard();
    if (this._nativeCard) this._nativeCard.hass = hass;
    this._update();
  }

  getCardSize() { return 7; }
  _language() { return language(this._hass); }
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
        <div class="footer"><ha-button class="close"></ha-button></div>
      </dialog>`;
    this.shadowRoot.querySelector(".reset").addEventListener("click", () => this._reset(false));
    this.shadowRoot.querySelector(".reset-long").addEventListener("click", () => this._reset(true));
    this.shadowRoot.querySelector(".close").addEventListener("click", () => this._closeDetails());
    this.shadowRoot.querySelector("dialog").addEventListener("click", (event) => {
      if (event.target === event.currentTarget) this._closeDetails();
    });
  }

  async _ensureNativeCard() {
    if (!this._config || !this._hass || this._nativeCard) return;
    if (!this._hass.states?.[this._config.entity]) return;
    if (this._nativeCardPromise) return this._nativeCardPromise;
    this._nativeCardPromise = (async () => {
      const helpers = await window.loadCardHelpers();
      if (!this._config || !this._hass || this._nativeCard) return;
      if (!this._hass.states?.[this._config.entity]) return;
      const cardConfig = {
        type: "thermostat",
        entity: this._config.entity,
        features: [
          ...(this._config.features || []),
          { type: "custom:predictive-details-card-feature" },
        ],
      };
      if (this._config.name) cardConfig.name = this._config.name;
      const nativeCard = await helpers.createCardElement(cardConfig);
      if (nativeCard.localName === "hui-error-card") return;
      nativeCard.hass = this._hass;
      nativeCard.addEventListener("predictive-thermostat-show-details", (event) => this._openDetails(event));
      this._nativeCard = nativeCard;
      this.shadowRoot.querySelector("#native").replaceChildren(nativeCard);
    })().finally(() => { this._nativeCardPromise = null; });
    return this._nativeCardPromise;
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
      ["predictionOutdoor", this._number(attributes.prediction_outdoor_temperature, " °C")],
      ["outdoorSource", attributes.prediction_outdoor_source, true],
      ["scheduleTarget", this._number(attributes.schedule_target_temperature, " °C")],
      ["nextTarget", this._number(attributes.next_target_temperature, " °C")],
      ["nextTime", this._formatDate(attributes.next_target_time)],
      ["predictedStart", this._formatDate(attributes.predicted_start_time)],
      ["predictedDuration", this._number(attributes.predicted_heating_minutes, ` ${this._t("minutes")}`)],
      ["confidence", confidence], ["predictionReason", attributes.prediction_reason],
      ["ignitionPart", this._number(attributes.prediction_ignition_minutes, ` ${this._t("minutes")}`)],
      ["gainPart", this._number(attributes.prediction_temperature_gain_minutes, ` ${this._t("minutes")}`)],
      ["outdoorPart", this._number(attributes.prediction_outdoor_loss_minutes, ` ${this._t("minutes")}`)],
      ["marginPart", this._number(attributes.prediction_margin_minutes, ` ${this._t("minutes")}`)],
      ["arrivalPart", this._number(attributes.prediction_arrival_correction_minutes, ` ${this._t("minutes")}`)],
      ["rawDuration", this._number(attributes.prediction_unbounded_minutes, ` ${this._t("minutes")}`)],
      ["learnedRate", this._number(attributes.learned_heating_rate, " °C/min")],
      ["learnedLoss", this._number(attributes.learned_loss_factor, " min/°C")],
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
    this.shadowRoot.querySelector(".close").textContent = this._t("close");
    const state = this._hass?.states?.[this._config.entity];
    if (!state) return;
    const list = this.shadowRoot.querySelector("dl");
    list.replaceChildren();
    for (const [label, rawValue, translateValue] of this._rows(state.attributes)) {
      const term = document.createElement("dt");
      const value = document.createElement("dd");
      term.textContent = this._t(label);
      value.textContent = translateValue ? (this._t(rawValue) || rawValue || this._t("none"))
        : rawValue === null || rawValue === undefined || rawValue === "" ? this._t("none") : String(rawValue);
      list.append(term, value);
    }
  }

  _openDetails(event) {
    event.stopPropagation();
    this._update();
    const dialog = this.shadowRoot.querySelector("dialog");
    if (!dialog.open) dialog.showModal();
  }

  _closeDetails() {
    const dialog = this.shadowRoot.querySelector("dialog");
    if (dialog.open) dialog.close();
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

if (!customElements.get("predictive-details-card-feature")) {
  customElements.define("predictive-details-card-feature", PredictiveDetailsCardFeature);
  window.customCardFeatures = window.customCardFeatures || [];
  window.customCardFeatures.push({
    type: "predictive-details-card-feature",
    name: "Predictive Thermostat details",
    isSupported: (hass, context) => Boolean(
      context?.entity_id && hass?.states?.[context.entity_id]?.attributes?.control_state,
    ),
  });
}

if (!customElements.get(CARD_TYPE)) {
  customElements.define(CARD_TYPE, PredictiveThermostatCard);
  window.customCards = window.customCards || [];
  window.customCards.push({ type: CARD_TYPE, name: "Predictive Thermostat", description: "Native thermostat controls with predictive heating details and fault reset actions." });
}
