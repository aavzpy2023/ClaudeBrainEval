import { after, before, describe, it } from "node:test";
import assert from "node:assert/strict";
import type { AddressInfo } from "node:net";
import type { Server } from "node:http";
import { createServer } from "../src/server.ts";
import { createStore } from "../src/store.ts";

let server: Server;
let base: string;
before(async () => {
  server = createServer(createStore());
  await new Promise<void>((resolve) => server.listen(0, resolve));
  base = `http://localhost:${(server.address() as AddressInfo).port}`;
});
after(() => server.close());

describe("oracle: limits", () => {
  it("GET /limits reports the current limits", async () => {
    const res = await fetch(`${base}/limits`);
    assert.equal(res.status, 200);
    assert.deepEqual(await res.json(), { titleMax: 200, bodyMax: 10000 });
  });
  it("a title of exactly titleMax characters is accepted and one more is rejected", async () => {
    const { titleMax } = (await (await fetch(`${base}/limits`)).json()) as { titleMax: number };
    const post = (title: string) =>
      fetch(`${base}/notes`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ title, body: "" }) });
    assert.equal((await post("a".repeat(titleMax))).status, 201);
    assert.equal((await post("a".repeat(titleMax + 1))).status, 422);
  });
  it("other methods get 405", async () => {
    assert.equal((await fetch(`${base}/limits`, { method: "POST" })).status, 405);
  });
});
