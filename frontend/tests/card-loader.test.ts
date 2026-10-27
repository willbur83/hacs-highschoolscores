import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { afterEach, describe, expect, it, vi } from "vitest";

const templatePath = resolve(
  dirname(fileURLToPath(import.meta.url)),
  "../../custom_components/high_school_sports_scores/card_loader.js.tpl",
);

declare global {
  interface Window {
    __hsssLoaderPromise?: { tag: string; promise: Promise<unknown> };
  }
}

function renderLoader(version: string, bundleUrl: string, tag: string): string {
  return readFileSync(templatePath, "utf8")
    .replaceAll("@@VERSION@@", version)
    .replaceAll("@@BUNDLE_URL@@", bundleUrl)
    .replaceAll("@@TAG@@", tag);
}

type ScriptResult = "ok" | "error" | "empty";

function stubBundleLoads(behavior: (src: string) => ScriptResult, tag: string) {
  const loads: string[] = [];
  const original = HTMLElement.prototype.appendChild;
  HTMLElement.prototype.appendChild = function appendChildStub<T extends Node>(node: T): T {
    if (node instanceof HTMLScriptElement && (this === document.head || this === document.documentElement)) {
      loads.push(node.src);
      queueMicrotask(() => {
        const result = behavior(node.src);
        if (result === "error") {
          node.onerror?.(new Event("error"));
          return;
        }
        if (result === "ok" && !customElements.get(tag)) {
          customElements.define(tag, class extends HTMLElement {});
        }
        node.onload?.(new Event("load"));
      });
      // Do not insert the script. happy-dom would fetch the URL and race the stub.
      return node;
    }
    return original.call(this, node) as T;
  };
  return {
    loads,
    restore() {
      HTMLElement.prototype.appendChild = original;
    },
  };
}

afterEach(() => {
  delete window.__hsssLoaderPromise;
});

describe("card loader", () => {
  it("retries a failed bundle fetch and then defines the card", async () => {
    const tag = "hsss-loader-retry";
    const bundle = "/high_school_sports_scores/high-school-sports-scores-card.js?v=0.1.0-beta.13&h=abc";
    const error = vi.spyOn(console, "error").mockImplementation(() => {});
    const info = vi.spyOn(console, "info").mockImplementation(() => {});
    const stub = stubBundleLoads((src) => (src.includes("r=") ? "ok" : "error"), tag);

    try {
      new Function(renderLoader("0.1.0-beta.13", bundle, tag))();
      await window.__hsssLoaderPromise?.promise;

      expect(stub.loads).toHaveLength(2);
      expect(stub.loads[1]).toContain("r=");
      expect(customElements.get(tag)).toBeTruthy();
      expect(info.mock.calls.some((call) => String(call[0]).includes("loader 0.1.0-beta.13"))).toBe(
        true,
      );
      expect(error).toHaveBeenCalled();
    } finally {
      stub.restore();
      error.mockRestore();
      info.mockRestore();
    }
  });

  it("defines a visible fallback when the bundle never registers the card", async () => {
    const tag = "hsss-loader-fallback";
    const bundle = "/high_school_sports_scores/high-school-sports-scores-card.js?v=0.1.0-beta.13&h=abc";
    const error = vi.spyOn(console, "error").mockImplementation(() => {});
    const stub = stubBundleLoads(() => "empty", tag);

    try {
      new Function(renderLoader("0.1.0-beta.13", bundle, tag))();
      await window.__hsssLoaderPromise?.promise;

      expect(stub.loads).toHaveLength(2);
      const element = document.createElement(tag);
      document.body.appendChild(element);
      expect(element.textContent).toContain("High School Sports Scores 0.1.0-beta.13 did not load");
      expect(element.textContent).toContain("did not register");
      expect(element.textContent).toContain("clear the browser cache");
      expect(error).toHaveBeenCalled();
    } finally {
      stub.restore();
      error.mockRestore();
    }
  });
});
