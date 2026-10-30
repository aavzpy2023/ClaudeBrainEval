import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { validateNoteInput, validateNotePatch } from '../src/validation.ts';

const EMOJI = '\u{1F600}'; // one code point, two UTF-16 code units

describe('oracle: lengths count Unicode code points', () => {
  it('accepts a title of 120 emoji and rejects 121', () => {
    assert.equal(validateNoteInput({ title: EMOJI.repeat(120) }).ok, true);
    assert.equal(validateNoteInput({ title: EMOJI.repeat(121) }).ok, false);
  });

  it('accepts a body of 10000 emoji and rejects 10001', () => {
    assert.equal(validateNoteInput({ title: 'a', body: EMOJI.repeat(10000) }).ok, true);
    assert.equal(validateNoteInput({ title: 'a', body: EMOJI.repeat(10001) }).ok, false);
  });

  it('applies the same rule to PATCH', () => {
    assert.equal(validateNotePatch({ title: EMOJI.repeat(120) }).ok, true);
    assert.equal(validateNotePatch({ title: EMOJI.repeat(121) }).ok, false);
    assert.equal(validateNotePatch({ body: EMOJI.repeat(10000) }).ok, true);
    assert.equal(validateNotePatch({ body: EMOJI.repeat(10001) }).ok, false);
  });

  it('plain ASCII limits are unchanged', () => {
    assert.equal(validateNoteInput({ title: 'x'.repeat(120) }).ok, true);
    assert.equal(validateNoteInput({ title: 'x'.repeat(121) }).ok, false);
  });
});
