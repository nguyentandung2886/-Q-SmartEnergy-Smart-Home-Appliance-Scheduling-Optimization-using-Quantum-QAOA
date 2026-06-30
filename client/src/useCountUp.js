import { useEffect, useState } from "react";

/**
 * Animates a number from 0 to targetValue over durationMs milliseconds.
 * decimals: number of decimal places preserved (default 0 = integer).
 */
export function useCountUp(targetValue, durationMs = 800, decimals = 0) {
  const [value, setValue] = useState(0);

  useEffect(() => {
    let startTime = null;
    let frameId;
    const factor = Math.pow(10, decimals);

    function step(timestamp) {
      if (startTime === null) startTime = timestamp;
      const progress = Math.min((timestamp - startTime) / durationMs, 1);
      setValue(Math.round(targetValue * progress * factor) / factor);
      if (progress < 1) frameId = requestAnimationFrame(step);
    }

    frameId = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frameId);
  }, [targetValue, durationMs, decimals]);

  return value;
}
