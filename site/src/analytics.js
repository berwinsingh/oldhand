// Opt-in Google Analytics. Nothing loads until a stored "granted" choice exists.
export const GA_MEASUREMENT_ID = "G-75YW6HE9FT";
export const ANALYTICS_CONSENT_KEY = "oldhand-analytics-consent";

export function readAnalyticsChoice(storage) {
  try {
    const store = storage || window.localStorage;
    const choice = store.getItem(ANALYTICS_CONSENT_KEY);
    return choice === "granted" || choice === "denied" ? choice : null;
  } catch {
    return null;
  }
}

export function saveAnalyticsChoice(choice, storage) {
  try {
    (storage || window.localStorage).setItem(ANALYTICS_CONSENT_KEY, choice);
  } catch {
    // The choice still applies for this page when storage is unavailable.
  }
}

export function loadAnalytics(win, doc) {
  const w = win || window;
  const d = doc || document;
  w.dataLayer = w.dataLayer || [];
  w.gtag =
    w.gtag ||
    function gtag() {
      w.dataLayer.push(arguments);
    };

  if (d.querySelector("script[data-oldhand-analytics]")) {
    w.gtag("consent", "update", { analytics_storage: "granted" });
    return;
  }

  w.gtag("consent", "default", {
    analytics_storage: "denied",
    ad_storage: "denied",
    ad_user_data: "denied",
    ad_personalization: "denied",
  });
  w.gtag("consent", "update", { analytics_storage: "granted" });
  w.gtag("js", new Date());
  w.gtag("config", GA_MEASUREMENT_ID);

  const script = d.createElement("script");
  script.async = true;
  script.dataset.oldhandAnalytics = "true";
  script.src = `https://www.googletagmanager.com/gtag/js?id=${GA_MEASUREMENT_ID}`;
  d.head.appendChild(script);
}

// Expire the cookies Google Analytics sets (_ga and _ga_<id>) on this host.
export function clearAnalyticsCookies(doc) {
  const d = doc || document;
  const names = (d.cookie || "")
    .split(";")
    .map((part) => part.split("=")[0].trim())
    .filter((name) => name === "_ga" || name.startsWith("_ga_"));
  for (const name of names) d.cookie = `${name}=; Max-Age=0; path=/`;
  return names;
}

// Apply a choice: only "granted" loads anything; "denied" tells an already
// loaded gtag to stop and removes its cookies; null (no choice yet) does nothing.
export function applyAnalyticsChoice(choice, win, doc) {
  const w = win || window;
  if (choice === "granted") loadAnalytics(w, doc);
  else if (choice === "denied") {
    if (typeof w.gtag === "function") w.gtag("consent", "update", { analytics_storage: "denied" });
    clearAnalyticsCookies(doc);
  }
}
