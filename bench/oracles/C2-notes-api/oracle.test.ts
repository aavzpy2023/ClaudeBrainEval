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

describe("oracle: search", () => {
  it("filters by case-insensitive substring in title or body, newest first", async () => {
    const t = [1000, 2000, 3000, 4000];
    let i = 0;
    const s = createStore(() => new Date(t[i++]));
    s.create({ title: "Alpha plan", body: "x" });
    s.create({ title: "other", body: "mentions ALPHA here" });
    s.create({ title: "unrelated", body: "nothing" });
    const srv = createServer(s);
    await new Promise<void>((resolve) => srv.listen(0, resolve));
    const b = `http://localhost:${(srv.address() as AddressInfo).port}`;
    try {
      const hits = (await (await fetch(`${b}/notes?q=alpha`)).json()) as { title: string }[];
      assert.deepEqual(hits.map((n) => n.title), ["other", "Alpha plan"]);
      assert.equal(((await (await fetch(`${b}/notes`)).json()) as unknown[]).length, 3);
      assert.deepEqual(await (await fetch(`${b}/notes?q=zzz`)).json(), []);
    } finally {
      srv.close();
    }
  });
});
