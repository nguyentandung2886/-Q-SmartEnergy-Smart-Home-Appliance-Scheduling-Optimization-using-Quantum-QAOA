import { test } from "node:test";
import assert from "node:assert/strict";
import { computeCandidateHours } from "./scheduleUtils.js";

test("wrap-around window 22h->6h, need 4h -> starts stay fully inside window", () => {
  assert.deepEqual(computeCandidateHours(22, 6, 4), [22, 23, 0, 1, 2]);
});

test("same-day window 8h->18h, need 3h -> starts 8..15", () => {
  assert.deepEqual(computeCandidateHours(8, 18, 3), [8, 9, 10, 11, 12, 13, 14, 15]);
});

test("block exactly fills the window -> single valid start", () => {
  assert.deepEqual(computeCandidateHours(22, 2, 4), [22]);
});

test("window shorter than need_duration -> empty (blocked)", () => {
  assert.deepEqual(computeCandidateHours(1, 3, 4), []);
});
