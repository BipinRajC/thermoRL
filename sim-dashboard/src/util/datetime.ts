import { format, addSeconds, differenceInSeconds, } from "date-fns";

export type DateLike = Date|number|string


export function formatDate(datetime: DateLike|null|undefined) {
  if (!datetime) {
    return "-"
  } else {
    return format(datetime, "yyyy-MM-dd HH:mm:ss z");
  }
}

export const floorDate = (d: DateLike, interval: number, origin: DateLike) => {
  let secs = differenceInSeconds(d, origin)
  secs = secs - (secs % interval)
  return addSeconds(origin, secs)
}

export const ceilDate = (d: DateLike, interval: number, origin: DateLike) => {
  let secs = differenceInSeconds(d, origin)
  const remainder = secs % interval
  if (remainder > 0) {
    secs = secs + (interval - remainder)
  }
  return addSeconds(origin, secs)
}

/**
 * Rounds a date to interval, also clamping it within the range (start, end]
 */
export const snapDate = (d: DateLike, start: DateLike, end: DateLike, interval: number) => {
  const secsEnd = differenceInSeconds(end, start);
  let secs = differenceInSeconds(d, start);
  secs = Math.min(Math.max(0, secs), secsEnd - 1); // clamp to range

  const remainder = secs % interval;
  if (remainder < interval / 2 || secs + interval >= secsEnd) {
    secs = secs - remainder;
  } else {
    secs = secs + (interval - remainder);
  }

  return addSeconds(start, secs);
}
