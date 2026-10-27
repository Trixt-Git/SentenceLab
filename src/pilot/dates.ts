// A new day starts at 4am local time (ARCHITECTURE.md section 7), so a late-night session still counts as "today".
const DAY_STARTS_AT_HOUR = 4;

const pad = (n: number) => String(n).padStart(2, '0');

/** The local day a moment belongs to, as "YYYY-MM-DD", with the 4am boundary applied. */
export function dayKey(moment: Date): string {
  const d = new Date(moment.getTime() - DAY_STARTS_AT_HOUR * 3_600_000);
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

/** `key` plus `days` calendar days. Noon avoids daylight-saving edges. */
export function addDays(key: string, days: number): string {
  const [y, m, d] = key.split('-').map(Number);
  const t = new Date(y, m - 1, d + days, 12);
  return `${t.getFullYear()}-${pad(t.getMonth() + 1)}-${pad(t.getDate())}`;
}
