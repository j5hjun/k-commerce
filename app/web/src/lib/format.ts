function pad(n: number): string {
  return String(n).padStart(2, "0");
}

/** Format a date as `2026.01.01 14:00`. */
export function stamp(d: Date = new Date()): string {
  return `${d.getFullYear()}.${pad(d.getMonth() + 1)}.${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}
