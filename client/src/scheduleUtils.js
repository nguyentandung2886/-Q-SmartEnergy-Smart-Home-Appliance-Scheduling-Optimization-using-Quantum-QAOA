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
