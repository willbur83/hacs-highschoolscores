/** Slice 0 hello-world Lovelace card custom element (full UX is later slices). */

const CARD_TAG = "maxpreps-program-card";

class MaxPrepsProgramCard extends HTMLElement {
  connectedCallback(): void {
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
    }
    const root = this.shadowRoot;
    if (!root) {
      return;
    }
    root.innerHTML = `<div part="container">MaxPreps program card (Slice 0)</div>`;
  }
}

if (!customElements.get(CARD_TAG)) {
  customElements.define(CARD_TAG, MaxPrepsProgramCard);
}

declare global {
  interface Window {
    customCards?: Array<{
      type: string;
      name: string;
      description: string;
      preview?: boolean;
    }>;
  }
}

window.customCards = window.customCards ?? [];
window.customCards.push({
  type: "custom:maxpreps-program-card",
  name: "MaxPreps Program Card",
  description: "High school sports program card (Phase 4)",
  preview: true,
});
