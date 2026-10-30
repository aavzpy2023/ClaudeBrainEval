import { after, before, describe, it } from "node:test";
import assert from "node:assert/strict";
import type { AddressInfo } from "node:net";
import type { Server } from "node:http";
import { createServer } from "../src/server.ts";
import { createStore } from "../src/store.ts";

let server: Server;
let base: string;
const store = createStore();
before(async () => {
  server = createServer(store);
  await new Promise<void>((resolve) => server.listen(0, resolve));
  base = `http://localhost:${(server.address() as AddressInfo).port}`;
});
after(() => server.close());

describe("oracle: health", () => {
  it("GET /health returns 200 {ok:true}", async () => {
    const res = await fetch(`${base}/health`);
    assert.equal(res.status, 200);
    assert.deepEqual(await res.json(), { ok: true });
  });
  it("other methods on /health get 405", async () => {
    assert.equal((await fetch(`${base}/health`, { method: "POST" })).status, 405);
  });
  it("notes routes are unaffected", async () => {
    assert.equal((await fetch(`${base}/notes`)).status, 200);
  });
});
