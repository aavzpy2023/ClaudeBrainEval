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

describe("oracle: limit", () => {
  it("returns at most limit notes, newest first", async () => {
    const t = [1000, 2000, 3000];
    let i = 0;
    const s = createStore(() => new Date(t[i++]));
    for (const title of ["a", "b", "c"]) s.create({ title, body: "" });
    const srv = createServer(s);
    await new Promise<void>((resolve) => srv.listen(0, resolve));
    const b = `http://localhost:${(srv.address() as AddressInfo).port}`;
    try {
      const two = (await (await fetch(`${b}/notes?limit=2`)).json()) as { title: string }[];
      assert.deepEqual(two.map((n) => n.title), ["c", "b"]);
      assert.equal(((await (await fetch(`${b}/notes`)).json()) as unknown[]).length, 3);
      for (const bad of ["0", "101", "abc", "1.5", "-1"]) {
        const res = await fetch(`${b}/notes?limit=${bad}`);
        assert.equal(res.status, 422, bad);
        const json = (await res.json()) as { error: { code: string } };
        assert.equal(json.error.code, "validation_failed");
      }
    } finally {
      srv.close();
    }
  });
});
