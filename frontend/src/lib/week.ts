export interface WeekParts {
  isoYear: number;
  isoWeek: number;
}

export function formatWeekKey(parts: WeekParts): string {
  return `${parts.isoYear}-W${String(parts.isoWeek).padStart(2, "0")}`;
}

export function parseWeekKey(value: string): WeekParts {
  const match = /^(\d{4})-W(\d{2})$/.exec(value.trim());
  if (!match) {
    throw new Error("Invalid week key");
  }
  return {
    isoYear: Number(match[1]),
    isoWeek: Number(match[2]),
  };
}

export function toWeekParts(date: Date): WeekParts {
  const copy = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  const dayNum = copy.getUTCDay() || 7;
  copy.setUTCDate(copy.getUTCDate() + 4 - dayNum);
  const yearStart = new Date(Date.UTC(copy.getUTCFullYear(), 0, 1));
  const isoWeek = Math.ceil(((copy.getTime() - yearStart.getTime()) / 86400000 + 1) / 7);
  return { isoYear: copy.getUTCFullYear(), isoWeek };
}

export function getCurrentWeekKey(date = new Date()): string {
  return formatWeekKey(toWeekParts(date));
}

export function shiftWeekKey(key: string, delta: number): string {
  const { isoYear, isoWeek } = parseWeekKey(key);
  const jan4 = new Date(isoYear, 0, 4);
  const jan4Day = jan4.getDay() || 7;
  const week1Monday = new Date(jan4);
  week1Monday.setDate(jan4.getDate() - jan4Day + 1);
  const monday = new Date(week1Monday);
  monday.setDate(week1Monday.getDate() + (isoWeek - 1) * 7 + delta * 7);
  return formatWeekKey(toWeekParts(monday));
}

export function weekLabel(key: string): string {
  const { isoYear, isoWeek } = parseWeekKey(key);
  return `${isoYear} · W${String(isoWeek).padStart(2, "0")}`;
}
