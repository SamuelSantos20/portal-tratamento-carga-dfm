import React, { useEffect, useState } from 'react';
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  AreaChart,
  Area,
} from 'recharts';
import {
  Filter,
  MousePointerClick,
  RotateCcw,
  TrendingUp,
  Award,
  FileText,
  Layers,
} from 'lucide-react';
import {
  formatCompactCurrency,
  formatCurrency,
  formatNumber,
  formatPercent,
} from '../utils/formatters';

const MACRO_COLORS = [
  '#0B1E36',
  '#183B66',
  '#C5A059',
  '#0D9488',
  '#2563EB',
  '#7C3AED',
  '#D97706',
  '#059669',
  '#DC2626',
  '#475569',
];

export default function PainelCustosView({ filtersData }) {
  const [ano, setAno] = useState('2026');
  const [ugBeneficiada, setUgBeneficiada] = useState('TODAS');
  const [ugResponsavel, setUgResponsavel] = useState('TODAS');
  const [macroClick, setMacroClick] = useState('TODAS');
  const [atividadeClick, setAtividadeClick] = useState('TODAS');
  const [tipoCusto, setTipoCusto] = useState('TODOS');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    async function load() {
      setLoading(true);
      try {
        const params = new URLSearchParams();
        if (ano) params.set('ano', ano);
        if (ugBeneficiada) params.set('ug_beneficiada', ugBeneficiada);
        if (ugResponsavel) params.set('ug_responsavel', ugResponsavel);
        if (macroClick) params.set('macro_click', macroClick);
        if (atividadeClick) params.set('atividade_click', atividadeClick);
        if (tipoCusto) params.set('tipo_custo', tipoCusto);

        const res = await fetch(`/api/dashboard/custos?${params.toString()}`);
        const json = await res.json();
        if (active) setData(json);
      } catch (err) {
        console.error(err);
      } finally {
        if (active) setLoading(false);
      }
    }
    load();
    return () => {
      active = false;
    };
  }, [ano, ugBeneficiada, ugResponsavel, macroClick, atividadeClick, tipoCusto]);

  function resetInteractiveFilters() {
    setAno('2026');
    setUgBeneficiada('TODAS');
    setUgResponsavel('TODAS');
    setMacroClick('TODAS');
    setAtividadeClick('TODAS');
    setTipoCusto('TODOS');
  }

  const kpis = data?.kpis || {};
  const macros = data?.macroatividades_chart || [];
  const totalMacros = macros.reduce((acc, m) => acc + Number(m.valor || 0), 0);

  return (
    <div className="space-y-6">
      {/* Barra de Filtros Oficial da Seção 4 + Filtro Orçamentário vs Extraorçamentário (-8) */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-navy-900">
            <Filter className="w-4 h-4 text-gold-500" />
            Filtros
          </div>
          <button
            type="button"
            onClick={resetInteractiveFilters}
            className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold transition-colors"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Limpar Filtros e Cliques
          </button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-3">
          <div>
            <label className="block text-[11px] font-semibold text-slate-600 mb-1">
              Exercício (<code>Ano</code>)
            </label>
            <select
              value={ano}
              onChange={(e) => setAno(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-2.5 py-2 text-xs font-semibold bg-white"
            >
              <option value="TODOS">2025 + 2026</option>
              <option value="2026">2026</option>
              <option value="2025">2025</option>
            </select>
          </div>

          <div className="lg:col-span-2">
            <label className="block text-[11px] font-semibold text-slate-600 mb-1">
              Natureza Contábil do Custo (Tratamento de <code>'-8</code>)
            </label>
            <select
              value={tipoCusto}
              onChange={(e) => setTipoCusto(e.target.value)}
              className="w-full rounded-lg border border-navy-700 bg-navy-50/40 px-2.5 py-2 text-xs font-bold text-navy-900"
            >
              <option value="TODOS">Todos os Custos (Orçamentários + Patrimoniais/Estoque + Depreciação)</option>
              <option value="ORCAMENTARIO">Apenas Custos Orçamentários (Com Ação de Governo)</option>
              <option value="EXTRAORCAMENTARIO">Apenas Extraorçamentários / Consumo Estoque (acao_governo = -8)</option>
              <option value="DEPRECIACAO">Apenas Depreciação / Amortização Patrimonial (NDD = -8)</option>
            </select>
          </div>

          <div>
            <label className="block text-[11px] font-semibold text-slate-600 mb-1">
              <code>UG_Beneficiada</code>
            </label>
            <select
              value={ugBeneficiada}
              onChange={(e) => setUgBeneficiada(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-2.5 py-2 text-xs bg-white truncate"
            >
              <option value="TODAS">Todas as UGs Beneficiadas</option>
              {(filtersData?.ugs_beneficiadas || []).map((u) => (
                <option key={u.codigo} value={u.codigo}>
                  {u.codigo} — {u.nome}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-[11px] font-semibold text-slate-600 mb-1">
              <code>UG_Responsavel</code>
            </label>
            <select
              value={ugResponsavel}
              onChange={(e) => setUgResponsavel(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-2.5 py-2 text-xs bg-white truncate"
            >
              <option value="TODAS">Todas as UGs Responsáveis</option>
              {(filtersData?.ugs_responsaveis || []).map((u) => (
                <option key={u.codigo} value={u.codigo}>
                  {u.codigo} — {u.nome}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-[11px] font-semibold text-slate-600 mb-1">
              <code>Macro Click</code>
            </label>
            <select
              value={macroClick}
              onChange={(e) => {
                setMacroClick(e.target.value);
                setAtividadeClick('TODAS');
              }}
              className="w-full rounded-lg border border-slate-300 px-2.5 py-2 text-xs bg-white truncate"
            >
              <option value="TODAS">Todas as Macroatividades</option>
              {(filtersData?.macroatividades || []).map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Pílulas de filtros de clique ativos */}
        {(macroClick !== 'TODAS' || atividadeClick !== 'TODAS') && (
          <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-100 text-xs">
            <span className="text-slate-500 font-medium flex items-center gap-1">
              <MousePointerClick className="w-3.5 h-3.5 text-gold-600" />
              Filtros de Clique Ativos:
            </span>
            {macroClick !== 'TODAS' && (
              <button
                onClick={() => setMacroClick('TODAS')}
                className="px-2.5 py-1 rounded-full bg-navy-900 text-white font-semibold hover:bg-navy-700"
              >
                Macro Click: {macroClick} ✕
              </button>
            )}
            {atividadeClick !== 'TODAS' && (
              <button
                onClick={() => setAtividadeClick('TODAS')}
                className="px-2.5 py-1 rounded-full bg-gold-500 text-navy-950 font-bold hover:bg-gold-400"
              >
                Atividade_Click: {atividadeClick} ✕
              </button>
            )}
          </div>
        )}
      </div>

      {/* KPIs Contábeis de Custos */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-navy-900 text-white rounded-xl p-4 shadow-sm border border-navy-800">
          <div className="text-xs text-slate-300 font-medium">
            Custo Total Apurado (<code>tb_custos_atividade</code>)
          </div>
          <div className="text-2xl font-extrabold text-gold-400 mt-1">
            {formatCompactCurrency(kpis.custo_total)}
          </div>
          <div className="text-[11px] text-slate-400 mt-1">
            {formatCurrency(kpis.custo_total)} • {formatNumber(kpis.qtd_lancamentos)} lançamentos
          </div>
        </div>

        <div className="bg-white rounded-xl p-4 shadow-sm border border-slate-200">
          <div className="text-xs text-slate-500 font-semibold">
            Parcela Orçamentária (Com Ação de Governo)
          </div>
          <div className="text-xl font-bold text-emerald-700 mt-1">
            {formatCompactCurrency(kpis.custo_orcamentario)}
          </div>
          <div className="text-[11px] text-slate-500 mt-1">
            {formatPercent(kpis.custo_orcamentario, kpis.custo_total)} do custo selecionado
          </div>
        </div>

        <div className="bg-white rounded-xl p-4 shadow-sm border border-slate-200">
          <div className="text-xs text-slate-500 font-semibold">
            Parcela Extraorçamentária / Estoque (<code>acao = -8</code>)
          </div>
          <div className="text-xl font-bold text-amber-700 mt-1">
            {formatCompactCurrency(kpis.custo_extraorcamentario)}
          </div>
          <div className="text-[11px] text-slate-500 mt-1">
            Inclui Depreciação ({formatCompactCurrency(kpis.custo_depreciacao)})
          </div>
        </div>

        <div className="bg-white rounded-xl p-4 shadow-sm border border-slate-200">
          <div className="text-xs text-slate-500 font-semibold">
            Custo Liquidado por NE (<code>tb_custos_ugr_na_liq</code>)
          </div>
          <div className="text-xl font-bold text-navy-900 mt-1">
            {formatCompactCurrency(kpis.total_liq_ugr)}
          </div>
          <div className="text-[11px] text-slate-500 mt-1">
            {formatNumber(kpis.total_nes_distintas)} Notas de Empenho (NE) distintas
          </div>
        </div>
      </div>

      {/* Linha Principal: Macroatividade (Rosca com Macro Click) + Atividades (Barras Horizontais com Atividade_Click) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Rosca de Macroatividade (Seção 5) */}
        <div className="lg:col-span-5 bg-white rounded-xl shadow-sm border border-slate-200 p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-slate-900 text-base">
                Macroatividade (Gráfico de Rosca)
              </h3>
              <span className="text-[11px] bg-blue-50 text-blue-800 px-2 py-0.5 rounded font-semibold">
                Clique p/ Macro Click
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Origem: <code>dfm.tb_custos_atividade</code>. Clique em uma fatia ou item abaixo para filtrar as subatividades.
            </p>
          </div>

          <div className="h-64 my-2">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={macros.slice(0, 10)}
                  dataKey="valor"
                  nameKey="macroatividade"
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={90}
                  paddingAngle={2}
                  onClick={(entry) => {
                    if (entry && entry.macroatividade) {
                      setMacroClick(
                        macroClick === entry.macroatividade ? 'TODAS' : entry.macroatividade
                      );
                      setAtividadeClick('TODAS');
                    }
                  }}
                  className="cursor-pointer"
                >
                  {macros.slice(0, 10).map((entry, idx) => (
                    <Cell
                      key={entry.macroatividade}
                      fill={MACRO_COLORS[idx % MACRO_COLORS.length]}
                      opacity={
                        macroClick === 'TODAS' || macroClick === entry.macroatividade ? 1 : 0.35
                      }
                    />
                  ))}
                </Pie>
                <Tooltip formatter={(val) => formatCurrency(val)} />
              </PieChart>
            </ResponsiveContainer>
          </div>

          <div className="space-y-1 max-h-52 overflow-y-auto pr-1 border-t border-slate-100 pt-2 text-xs">
            {macros.map((m, idx) => {
              const active = macroClick === m.macroatividade;
              return (
                <button
                  key={m.macroatividade}
                  type="button"
                  onClick={() => {
                    setMacroClick(active ? 'TODAS' : m.macroatividade);
                    setAtividadeClick('TODAS');
                  }}
                  className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-left transition-colors ${
                    active ? 'bg-navy-900 text-white font-bold' : 'hover:bg-slate-100 text-slate-700'
                  }`}
                >
                  <div className="flex items-center gap-2 truncate pr-2">
                    <span
                      className="w-2.5 h-2.5 rounded-full shrink-0"
                      style={{ backgroundColor: MACRO_COLORS[idx % MACRO_COLORS.length] }}
                    />
                    <span className="truncate">{m.macroatividade}</span>
                  </div>
                  <div className="shrink-0 font-mono">
                    {formatCompactCurrency(m.valor)} ({formatPercent(m.valor, totalMacros)})
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Barras Horizontais de Atividades (Seção 5) */}
        <div className="lg:col-span-7 bg-white rounded-xl shadow-sm border border-slate-200 p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-slate-900 text-base">
                Atividades (Gráfico de Barras Horizontais)
              </h3>
              <span className="text-[11px] bg-amber-50 text-amber-800 px-2 py-0.5 rounded font-semibold">
                Clique p/ Atividade_Click
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Ranqueamento da maior para a menor subatividade (<code>atividade_geral</code>). Clique em uma barra para filtrar o Demonstrativo Mensal abaixo.
            </p>
          </div>

          <div className="h-[420px] mt-3">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={(data?.atividades_chart || []).slice(0, 12)}
                layout="vertical"
                margin={{ top: 5, right: 25, left: 10, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} />
                <XAxis
                  type="number"
                  tickFormatter={(v) => formatCompactCurrency(v)}
                  tick={{ fontSize: 11 }}
                />
                <YAxis
                  type="category"
                  dataKey="atividade"
                  width={230}
                  tick={{ fontSize: 10 }}
                  tickFormatter={(v) => (v.length > 36 ? `${v.slice(0, 36)}...` : v)}
                />
                <Tooltip formatter={(val) => formatCurrency(val)} />
                <Bar
                  dataKey="valor"
                  name="Custo Apurado (R$)"
                  fill="#0B1E36"
                  radius={[0, 4, 4, 0]}
                  className="cursor-pointer"
                  onClick={(entry) => {
                    if (entry && entry.atividade) {
                      setAtividadeClick(
                        atividadeClick === entry.atividade ? 'TODAS' : entry.atividade
                      );
                    }
                  }}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Demonstrativo Mensal dos Custos por Atividade (Seção 4 e 7.7 - dfm.tb_custos_atividade_mes) */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
          <div>
            <h3 className="font-bold text-slate-900 text-base flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-navy-800" />
              Demonstrativo Mensal dos Custos por Competência (<code>dfm.tb_custos_atividade_mes</code>)
            </h3>
            <p className="text-xs text-slate-500">
              Controlado pelo filtro <code>Atividade_Click</code> ({atividadeClick === 'TODAS' ? 'Todas as Atividades' : atividadeClick}).
              Ordenado por <code>mes_referencia_ordem</code> (capturando apropriações retroativas 2025 e rateios pro-rata 2027).
            </p>
          </div>
        </div>

        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={data?.evolucao_mensal || []}
              margin={{ top: 10, right: 20, left: 10, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="mes_ano_label" tick={{ fontSize: 11 }} />
              <YAxis tickFormatter={(v) => formatCompactCurrency(v)} tick={{ fontSize: 11 }} />
              <Tooltip formatter={(val) => formatCurrency(val)} />
              <Area
                type="monotone"
                dataKey="valor"
                name="Custo Mensal (R$)"
                stroke="#0B1E36"
                fill="#183B66"
                fillOpacity={0.2}
                strokeWidth={2.5}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Custo Liquidado por UG Responsável (04) + Natureza de Despesa (NDD) + SIORG Documentos Hábeis (06) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Custo Liquidado por UG Responsável */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
          <div className="px-4 py-3 bg-navy-900 text-white font-bold text-xs uppercase tracking-wider">
            Custo Liquidado por UG Responsável (<code>tb_custos_ugr_na_liq</code>)
          </div>
          <div className="overflow-x-auto max-h-80">
            <table className="w-full text-xs text-left whitespace-nowrap">
              <thead className="bg-slate-50 text-slate-600 sticky top-0 border-b border-slate-200">
                <tr>
                  <th className="py-2 px-3">UGR</th>
                  <th className="py-2 px-3">Nome da UG Responsável</th>
                  <th className="py-2 px-3 text-right">Custo Liquidado</th>
                  <th className="py-2 px-3 text-center">NEs</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {(data?.custo_por_ugr || []).map((u) => (
                  <tr
                    key={u.ug_responsavel}
                    onClick={() =>
                      setUgResponsavel(
                        ugResponsavel === u.ug_responsavel ? 'TODAS' : u.ug_responsavel
                      )
                    }
                    className="hover:bg-blue-50/50 cursor-pointer"
                  >
                    <td className="py-1.5 px-3 font-mono font-bold text-navy-900">
                      {u.ug_responsavel}
                    </td>
                    <td className="py-1.5 px-3 max-w-[180px] truncate text-slate-700">
                      {u.ug_responsavel_nome}
                    </td>
                    <td className="py-1.5 px-3 text-right font-mono font-semibold text-emerald-700">
                      {formatCompactCurrency(u.valor_liquidado)}
                    </td>
                    <td className="py-1.5 px-3 text-center font-mono text-slate-500">
                      {formatNumber(u.qtd_ne)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Top Natureza de Despesa Detalhada (NDD) */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
          <div className="px-4 py-3 bg-slate-100 border-b border-slate-200 font-bold text-xs text-slate-800 uppercase tracking-wider">
            Top Naturezas de Despesa Detalhada (NDD)
          </div>
          <div className="overflow-x-auto max-h-80">
            <table className="w-full text-xs text-left whitespace-nowrap">
              <thead className="bg-slate-50 text-slate-600 sticky top-0 border-b border-slate-200">
                <tr>
                  <th className="py-2 px-3">NDD</th>
                  <th className="py-2 px-3">Descrição</th>
                  <th className="py-2 px-3 text-right">Valor Apurado</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {(data?.top_ndd || []).map((n) => (
                  <tr key={n.codigo_ndd} className="hover:bg-slate-50">
                    <td className="py-1.5 px-3 font-mono font-bold text-navy-900">
                      {n.codigo_ndd}
                    </td>
                    <td className="py-1.5 px-3 max-w-[200px] truncate text-slate-700">
                      {n.nome_ndd}
                    </td>
                    <td className="py-1.5 px-3 text-right font-mono font-semibold">
                      {formatCompactCurrency(n.valor)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Documentos Hábeis SIORG (Planilha 06) */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
          <div className="px-4 py-3 bg-slate-100 border-b border-slate-200 font-bold text-xs text-slate-800 uppercase tracking-wider">
            Custos por Tipo de Documento Hábil (06 — SIORG <code>000185</code>)
          </div>
          <div className="overflow-x-auto max-h-80">
            <table className="w-full text-xs text-left whitespace-nowrap">
              <thead className="bg-slate-50 text-slate-600 sticky top-0 border-b border-slate-200">
                <tr>
                  <th className="py-2 px-3">Tipo DH</th>
                  <th className="py-2 px-3 text-right">Qtd. Documentos</th>
                  <th className="py-2 px-3 text-right">Valor Total (R$)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {(data?.siorg_por_tipo_dh || []).map((d) => (
                  <tr key={d.tipo_dh} className="hover:bg-slate-50">
                    <td className="py-2 px-3 font-mono font-bold text-navy-900">
                      <span className="px-2 py-0.5 rounded bg-navy-100 text-navy-900">
                        {d.tipo_dh}
                      </span>
                    </td>
                    <td className="py-2 px-3 text-right font-mono">
                      {formatNumber(d.qtd_registros)}
                    </td>
                    <td className="py-2 px-3 text-right font-mono font-semibold text-navy-900">
                      {formatCurrency(d.valor_total)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
