import { test } from 'node:test';
import assert from 'node:assert/strict';
import { slugify, uniqueSlug } from '../src/slug.js';

test('lowercases and joins words with hyphens', () => {
  assert.equal(slugify('Hello World'), 'hello-world');
  assert.equal(slugify('  Ten  Tips: for 2026! '), 'ten-tips-for-2026');
});

test('a repeat gets -2', () => {
  assert.equal(uniqueSlug('Hello World', ['hello-world']), 'hello-world-2');
});
