// Rows whose email is not already in the store.
export function newContacts(rows, existing) {
  return rows.filter((r) => !existing.some((c) => c.email === r.email));
}
