export function formatCurrency(value) {
  if (value === null || value === undefined || value === '' || isNaN(Number(value))) {
    return 'R$ 0,00';
  }
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(Number(value));
}

export function formatCompactCurrency(value) {
  const num = Number(value || 0);
  const abs = Math.abs(num);
  if (abs >= 1e9) {
    return `R$ ${(num / 1e9).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} Bi`;
  }
  if (abs >= 1e6) {
    return `R$ ${(num / 1e6).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} Mi`;
  }
  if (abs >= 1e3) {
    return `R$ ${(num / 1e3).toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })} Mil`;
  }
  return formatCurrency(num);
}

export function formatNumber(value) {
  if (value === null || value === undefined || isNaN(Number(value))) return '0';
  return new Intl.NumberFormat('pt-BR').format(Number(value));
}

export function formatPercent(value, total) {
  if (!total || total === 0) return '0,0%';
  return `${((Number(value) / Number(total)) * 100).toLocaleString('pt-BR', {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  })}%`;
}
