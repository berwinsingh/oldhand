export function normalize(row) {
  return { name: row.name.trim(), email: row.email, company: (row.company || '').trim() };
}
