import { existsSync, readFileSync, writeFileSync } from 'node:fs';

export const load = (path) => (existsSync(path) ? JSON.parse(readFileSync(path, 'utf8')) : []);
export const save = (path, contacts) => writeFileSync(path, JSON.stringify(contacts, null, 2) + '\n');
