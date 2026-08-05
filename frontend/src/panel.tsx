import { StrictMode } from "react";
import { createRoot, type Root } from "react-dom/client";
import { App } from "./App";
import type { Hass } from "./ha/types";
import "./styles/app.css";

class FH3XPanel extends HTMLElement {
  private root?: Root;
  private currentHass?: Hass;

  set hass(value: Hass) {
    this.currentHass = value;
    this.renderApp();
  }

  set panel(value: { config?: Record<string, unknown> }) {
    void value;
  }

  connectedCallback() {
    const css = document.head.querySelector<HTMLStyleElement>('style[data-fh3x="panel"]')?.textContent;
    if (css && !this.querySelector('style[data-fh3x-local]')) {
      const style = document.createElement("style");
      style.dataset.fh3xLocal = "true";
      style.textContent = css;
      this.appendChild(style);
    }
    this.renderApp();
  }

  disconnectedCallback() {
    this.root?.unmount();
    this.root = undefined;
  }

  private renderApp() {
    if (!this.root) {
      const mount = document.createElement("div");
      mount.className = "fh3x-react-root";
      this.appendChild(mount);
      this.root = createRoot(mount);
    }
    this.root.render(
      <StrictMode>
        <App hass={this.currentHass} />
      </StrictMode>,
    );
  }
}

if (!customElements.get("fh3x-energy-panel")) {
  customElements.define("fh3x-energy-panel", FH3XPanel);
}
