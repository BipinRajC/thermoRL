import { useEffect, useRef } from "react";

/**
 * Hook for setInterval, handles "dynamic" callback and delay.
 * See https://overreacted.io/making-setinterval-declarative-with-react-hooks/
 * @param callback Callback to call every interval
 * @param delay Delay in milliseconds. If null, clears the interval.
 */
export function useInterval(callback: () => void, delay: number|null) {
    const savedCallback = useRef(callback);
    useEffect(() => { savedCallback.current = callback }, [callback]);

    useEffect(() => {
        if (delay != null) {
            const id = setInterval(() => { savedCallback.current() }, delay);
            return () => clearInterval(id);
        }
    }, [delay]);
}
