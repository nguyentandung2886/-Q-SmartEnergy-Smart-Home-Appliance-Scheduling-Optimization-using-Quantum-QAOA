import { useEffect, useState } from "react";

/**
 * Animates a number from 0 to targetValue over durationMs milliseconds.
 * Returns the current animated value (updates each animation frame).
 */
export function useCountUp(targetValue, durationMs = 800) {
  const [value, setValue] = useState(0);

  useEffect(() => {
    let startTime = null;
    let frameId;

    function step(timestamp) {
      if (startTime === null) startTime = timestamp;
      const progress = Math.min((timestamp - startTime) / durationMs, 1);
      setValue(Math.round(targetValue * progress));
      if (progress < 1) frameId = requestAnimationFrame(step);
    }

    frameId = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frameId);
  }, [targetValue, durationMs]);

  return value;
}
