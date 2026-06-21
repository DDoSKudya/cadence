export function pluralRu(
  count: number,
  one: string,
  few: string,
  many: string,
): string {
  const n = Math.abs(count) % 100;
  const n1 = n % 10;
  if (n > 10 && n < 20) {
    return `${count} ${many}`;
  }
  if (n1 > 1 && n1 < 5) {
    return `${count} ${few}`;
  }
  if (n1 === 1) {
    return `${count} ${one}`;
  }
  return `${count} ${many}`;
}
