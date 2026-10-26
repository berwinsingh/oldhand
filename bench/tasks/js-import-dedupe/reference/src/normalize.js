export function normalize(row) {
  return { name: row.name.trim(), email: (row.email || '').trim(), company: (row.company || '').trim() };
}

// The identity used to spot duplicates: trimmed and lowercased.
export const emailKey = (email) => email.trim().toLowerCase();
export const validEmail = (email) => email.includes('@');
