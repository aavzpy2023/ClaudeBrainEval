import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { createStore } from "../src/store.ts";

function fileWith(notes: unknown[]): string {
  const f = join(mkdtempSync(join(tmpdir(), "oracle-")), "notes.json");
  writeFileSync(f, JSON.stringify(notes));
  return f;
}

describe("oracle: legacy notes file", () => {
  it("loads first-iteration timestamps keeping the instant they meant", () => {
    const f = fileWith([{ id: "a", title: "old", body: "", createdAt: "2026-03-04 09:05" }]);
    const [n] = createStore(() => new Date(), f).list();
    assert.equal(n.createdAt, new Date(2026, 2, 4, 9, 5).toISOString());
  });
  it("mixes legacy and current notes, newest first", () => {
    const f = fileWith([
      { id: "a", title: "old", body: "", createdAt: "2026-03-04 09:05" },
      { id: "b", title: "new", body: "", createdAt: new Date(2026, 5, 1).getTime() },
    ]);
    assert.deepEqual(createStore(() => new Date(), f).list().map((n) => n.id), ["b", "a"]);
  });
  it("writes the current representation back", () => {
    const f = fileWith([{ id: "a", title: "old", body: "", createdAt: "2026-03-04 09:05" }]);
    const s = createStore(() => new Date(), f);
    s.create({ title: "x", body: "" });
    const saved = JSON.parse(readFileSync(f, "utf8")) as Array<{ createdAt: unknown }>;
    assert.ok(saved.every((n) => typeof n.createdAt === "number"));
  });
});
