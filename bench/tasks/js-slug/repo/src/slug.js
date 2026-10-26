export function slugify(title) {
  return title
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

// The slug for a title, made unique against the slugs already in the store.
export function uniqueSlug(title, existing) {
  const base = slugify(title);
  const taken = existing.filter((s) => s === base || s.startsWith(base + '-')).length;
  return taken === 0 ? base : `${base}-${taken + 1}`;
}
