const COMPACT_DATETIME: Intl.DateTimeFormatOptions = {
  day: "numeric",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
};

const LONG_DATETIME: Intl.DateTimeFormatOptions = {
  day: "numeric",
  month: "long",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
};

const DATE_TIME_LOCALES = {
  en: "en-US",
  ru: "ru-RU",
} as const;

function parseDate(value: string): Date | null {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return null;
  }
  return date;
}

function activeDateTimeLocale(): string {
  return document.documentElement.lang === "ru" ? DATE_TIME_LOCALES.ru : DATE_TIME_LOCALES.en;
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return "—";
  }
  const date = parseDate(value);
  if (!date) {
    return value;
  }
  return new Intl.DateTimeFormat(activeDateTimeLocale(), COMPACT_DATETIME).format(date);
}

export function formatDateTimeLong(value: string | null | undefined): string {
  if (!value) {
    return "—";
  }
  const date = parseDate(value);
  if (!date) {
    return value;
  }
  return new Intl.DateTimeFormat(activeDateTimeLocale(), LONG_DATETIME).format(date);
}
