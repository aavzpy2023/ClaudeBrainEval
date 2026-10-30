import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, mkdtempSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createStore } from '../src/store.ts';

const tempFile = () => join(mkdtempSync(join(tmpdir(), 'oracle-')), 'notes.json');

describe('oracle: corrupt NOTES_FILE', () => {
  it('does not throw, moves the bad file to <file>.corrupt and starts empty', () => {
    const file = tempFile();
    writeFileSync(file, '{not json');
    const store = createStore(undefined, file);
    assert.deepEqual(store.list(), []);
    assert.equal(readFileSync(`${file}.corrupt`, 'utf8'), '{not json');
  });

  it('the store keeps working and persists after recovering', () => {
    const file = tempFile();
    writeFileSync(file, 'garbage');
    const store = createStore(undefined, file);
    const note = store.create({ title: 'a', body: '' });
    assert.equal(createStore(undefined, file).list()[0].id, note.id);
  });

  it('a valid file loads normally and leaves no .corrupt file', () => {
    const file = tempFile();
    const first = createStore(undefined, file);
    const note = first.create({ title: 'ok', body: '' });
    assert.equal(createStore(undefined, file).get(note.id)?.title, 'ok');
    assert.equal(existsSync(`${file}.corrupt`), false);
  });
});
