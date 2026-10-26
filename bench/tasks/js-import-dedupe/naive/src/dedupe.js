// Rows whose email is not already in the store.
export function newContacts(rows, existing) {
  const key = (e) => e.trim().toLowerCase();
  return rows.filter((r) => !existing.some((c) => key(c.email) === key(r.email)));
}
