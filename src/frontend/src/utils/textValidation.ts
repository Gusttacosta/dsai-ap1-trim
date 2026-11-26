// Regras de texto comuns aos formulários do painel.

/** Texto com 1 a `max` caracteres, sem contar os espaços das pontas (o backend apara). */
export const fitsTrimmed = (text: string, max: number) => {
  const length = text.trim().length;
  return length >= 1 && length <= max;
};
