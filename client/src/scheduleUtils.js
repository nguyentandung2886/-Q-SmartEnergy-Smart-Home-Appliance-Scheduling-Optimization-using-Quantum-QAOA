/**
 * Compute the valid start hours for a self-scheduling appliance.
 *
 * Given a window [use_start, use_end) in which the appliance is ALLOWED to run
 * (wraps past midnight when use_end <= use_start, e.g. 22h->6h means the window
 * 22,23,0,1,2,3,4,5) and need_duration consecutive hours it must run, return
 * every start hour whose need_duration-hour block fits entirely inside the
 * window. Returns [] when the window is shorter than need_duration.
 */
export function computeCandidateHours(use_start, use_end, need_duration) {
  const windowLength = use_end > use_start ? use_end - use_start : use_end + 24 - use_start;
  const validStarts = windowLength - need_duration + 1;
  if (validStarts <= 0) return [];
  const hours = [];
  for (let i = 0; i < validStarts; i++) hours.push((use_start + i) % 24);
  return hours;
}

// Household default (W) when there's no business profile / contracted power declared.
// Must match DEFAULT_POWER_THRESHOLD_W in backend/core/qubo_builder.py.
const DEFAULT_POWER_THRESHOLD_W = 5000;

// Commercial businesses warn earlier than production at the same contracted power.
// Must match COMMERCIAL_SAFETY_MARGIN in backend/api/optimize_router.py.
const COMMERCIAL_SAFETY_MARGIN = 0.8;

/**
 * Mirrors backend's _power_threshold_for_user (api/optimize_router.py) so the client can show
 * the account's real concurrent-power threshold before an /optimize response exists (e.g. a
 * rehydrated schedule from history, which doesn't persist power_threshold_w).
 *
 * `me` is the GET /auth/me response shape ({ role, business_profile }); null while still loading.
 */
export function accountPowerThresholdW(me) {
  const profile = me?.business_profile;
  if (me?.role !== "business" || !profile || profile.contracted_power_kw == null) {
    return DEFAULT_POWER_THRESHOLD_W;
  }
  const contractedW = profile.contracted_power_kw * 1000;
  return profile.business_type === "commercial" ? contractedW * COMMERCIAL_SAFETY_MARGIN : contractedW;
}
