import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createStore } from '../src/store.ts';

describe('oracle: stale temp files from a crashed write', () => {
  it('removes <file>.<pid>.tmp leftovers at startup and keeps the data', () => {
    const dir = mkdtempSync(join(tmpdir(), 'oracle-'));
    const file = join(dir, 'notes.json');
    const note = createStore(undefined, file).create({ title: 'keep me', body: '' });
    writeFileSync(`${file}.99999.tmp`, '[{"half written');
    writeFileSync(`${file}.123.tmp`, '');
    writeFileSync(join(dir, 'unrelated.tmp'), 'x');
    const store = createStore(undefined, file);
    assert.equal(existsSync(`${file}.99999.tmp`), false);
    assert.equal(existsSync(`${file}.123.tmp`), false);
    assert.equal(existsSync(join(dir, 'unrelated.tmp')), true);
    assert.equal(store.get(note.id)?.title, 'keep me');
  });

  it('works when there is nothing to clean', () => {
    const file = join(mkdtempSync(join(tmpdir(), 'oracle-')), 'notes.json');
    assert.deepEqual(createStore(undefined, file).list(), []);
  });
});
