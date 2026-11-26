// Regras de texto comuns aos formulários do painel.

/** Texto com 1 a `max` caracteres, sem contar os espaços das pontas (o backend apara). */
export const fitsTrimmed = (text: string, max: number) => {
  const length = text.trim().length;
  return length >= 1 && length <= max;
};

/** Inteiro de 1 a `max` escrito só com algarismos (sem sinal, vírgula ou espaço no meio), ou null. */
export function parsePositiveInt(text: string, max: number): number | null {
  const value = text.trim();
  if (!/^\d+$/.test(value)) return null;
  const number = Number(value);
  return number >= 1 && number <= max ? number : null;
}
