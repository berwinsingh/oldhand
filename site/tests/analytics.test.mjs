import assert from "node:assert/strict";
import test from "node:test";
import {
  ANALYTICS_CONSENT_KEY,
  GA_MEASUREMENT_ID,
  applyAnalyticsChoice,
  readAnalyticsChoice,
  saveAnalyticsChoice,
} from "../src/analytics.js";

function fakeDom() {
  const head = { children: [], appendChild(node) { this.children.push(node); } };
  const doc = {
    head,
    createElement: () => ({ dataset: {} }),
    querySelector: () => head.children.find((n) => n.dataset.oldhandAnalytics) || null,
  };
  return { win: {}, doc };
}

function fakeStorage(initial = {}) {
  const data = { ...initial };
  return { getItem: (k) => (k in data ? data[k] : null), setItem: (k, v) => { data[k] = v; }, data };
}

test("no choice loads nothing", () => {
  const { win, doc } = fakeDom();
  applyAnalyticsChoice(null, win, doc);
  assert.equal(doc.head.children.length, 0);
  assert.equal(win.gtag, undefined);
});

test("denied without a loaded gtag loads nothing", () => {
  const { win, doc } = fakeDom();
  applyAnalyticsChoice("denied", win, doc);
  assert.equal(doc.head.children.length, 0);
});

test("granted sets consent default denied before granting, then injects one script", () => {
  const { win, doc } = fakeDom();
  applyAnalyticsChoice("granted", win, doc);
  const calls = win.dataLayer.map((args) => Array.from(args));
  assert.deepEqual(calls[0], ["consent", "default", {
    analytics_storage: "denied", ad_storage: "denied", ad_user_data: "denied", ad_personalization: "denied",
  }]);
  assert.deepEqual(calls[1], ["consent", "update", { analytics_storage: "granted" }]);
  assert.equal(doc.head.children.length, 1);
  assert.match(doc.head.children[0].src, new RegExp(`id=${GA_MEASUREMENT_ID}$`));
  applyAnalyticsChoice("granted", win, doc);
  assert.equal(doc.head.children.length, 1, "a second grant does not inject a second script");
});

test("denied after a load updates consent to denied", () => {
  const { win, doc } = fakeDom();
  applyAnalyticsChoice("granted", win, doc);
  applyAnalyticsChoice("denied", win, doc);
  const last = Array.from(win.dataLayer.at(-1));
  assert.deepEqual(last, ["consent", "update", { analytics_storage: "denied" }]);
});

test("denied expires the Google Analytics cookies and nothing else", () => {
  const { win } = fakeDom();
  const writes = [];
  const doc = {
    get cookie() { return "_ga=GA1.1.1; theme=dark; _ga_75YW6HE9FT=GS1.1.2"; },
    set cookie(value) { writes.push(value); },
  };
  applyAnalyticsChoice("denied", win, doc);
  assert.deepEqual(writes, ["_ga=; Max-Age=0; path=/", "_ga_75YW6HE9FT=; Max-Age=0; path=/"]);
});

test("stored choice round-trips and junk or a throwing store reads as null", () => {
  const store = fakeStorage();
  saveAnalyticsChoice("granted", store);
  assert.equal(store.data[ANALYTICS_CONSENT_KEY], "granted");
  assert.equal(readAnalyticsChoice(store), "granted");
  assert.equal(readAnalyticsChoice(fakeStorage({ [ANALYTICS_CONSENT_KEY]: "maybe" })), null);
  assert.equal(readAnalyticsChoice({ getItem() { throw new Error("blocked"); } }), null);
});
