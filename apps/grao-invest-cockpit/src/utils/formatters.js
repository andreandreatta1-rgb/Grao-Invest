const BR_NUMBER = new Intl.NumberFormat("pt-BR", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const BR_INTEGER = new Intl.NumberFormat("pt-BR", {
  maximumFractionDigits: 0,
});

function toFiniteNumber(value) {
  if (value === null || value === undefined || value === "") return null;

  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

export function fmtMoney(value) {
  const number = toFiniteNumber(value);
  if (number === null) return "R$ --";

  return `R$ ${BR_NUMBER.format(number)}`;
}

export function fmtPct(value) {
  const number = toFiniteNumber(value);
  if (number === null) return "--%";

  const sign = number > 0 ? "+" : "";
  return `${sign}${BR_NUMBER.format(number)}%`;
}

export function fmtInteger(value) {
  const number = toFiniteNumber(value);
  if (number === null) return "--";

  return BR_INTEGER.format(number);
}

export function fmtDays(value) {
  const number = toFiniteNumber(value);
  if (number === null) return "-- d";

  return `${BR_INTEGER.format(Math.round(number))} d`;
}

export function fmtDate(value) {
  if (!value) return "--/--/----";

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "--/--/----";

  return new Intl.DateTimeFormat("pt-BR", { timeZone: "America/Sao_Paulo" }).format(date);
}
