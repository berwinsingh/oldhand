import { emailKey } from './normalize.js';

// Splits rows into new contacts and duplicates (already stored, or earlier in the same file).
export function newContacts(rows, existing) {
  const seen = new Set(existing.map((c) => emailKey(c.email)));
  const added = [];
  let skipped = 0;
  for (const r of rows) {
    const key = emailKey(r.email);
    if (seen.has(key)) skipped += 1;
    else {
      seen.add(key);
      added.push(r);
    }
  }
  return { added, skipped };
}
