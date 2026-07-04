import { test } from "node:test";
import assert from "node:assert/strict";
import { computeCandidateHours, accountPowerThresholdW } from "./scheduleUtils.js";

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

test("accountPowerThresholdW: no account loaded yet -> household default", () => {
  assert.equal(accountPowerThresholdW(null), 5000);
});

test("accountPowerThresholdW: household role -> household default", () => {
  assert.equal(accountPowerThresholdW({ role: "household" }), 5000);
});

test("accountPowerThresholdW: business without a business_profile -> household default", () => {
  assert.equal(accountPowerThresholdW({ role: "business" }), 5000);
});

test("accountPowerThresholdW: business with no contracted_power_kw declared -> household default", () => {
  assert.equal(
    accountPowerThresholdW({ role: "business", business_profile: { business_type: "production", contracted_power_kw: null } }),
    5000
  );
});

test("accountPowerThresholdW: business production -> full contracted power in W", () => {
  assert.equal(
    accountPowerThresholdW({ role: "business", business_profile: { business_type: "production", contracted_power_kw: 20 } }),
    20000
  );
});

test("accountPowerThresholdW: business commercial -> contracted power x 0.8 safety margin", () => {
  assert.equal(
    accountPowerThresholdW({ role: "business", business_profile: { business_type: "commercial", contracted_power_kw: 20 } }),
    16000
  );
});
