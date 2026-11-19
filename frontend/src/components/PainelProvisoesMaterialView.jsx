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
  Legend,
} from 'recharts';
import {
  Filter,
  Landmark,
  Package,
  ShieldAlert,
  Layers,
  CheckCircle2,
  Clock,
} from 'lucide-react';
import {
  formatCompactCurrency,
  formatCurrency,
  formatNumber,
  formatPercent,
} from '../utils/formatters';

const DONUT_COLORS_RCB = ['#0B1E36', '#214E85', '#C5A059'];
const DONUT_COLORS_LIQ = ['#059669', '#10B981', '#6EE7B7'];
const DONUT_COLORS_ALIQ = ['#D97706', '#F59E0B', '#FCD34D'];
const MATERIAL_COLORS = ['#1E40AF', '#0D9488'];

function DonutCard({ title, subtitle, total, slices, colors, badgeText }) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5 flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between gap-2 mb-1">
          <h3 className="font-bold text-slate-900 text-sm">{title}</h3>
          {badgeText && (
            <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 font-semibold text-[11px]">
              {badgeText}
            </span>
          )}
        </div>
        <p className="text-xs text-slate-500 mb-3">{subtitle}</p>
      </div>

      <div className="relative h-56">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={slices}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              innerRadius={58}
              outerRadius={82}
              paddingAngle={2}
            >
              {slices.map((entry, idx) => (
                <Cell key={entry.name} fill={colors[idx % colors.length]} />
              ))}
            </Pie>
            <Tooltip formatter={(val) => formatCurrency(val)} />
          </PieChart>
        </ResponsiveContainer>
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none text-center px-4">
          <span className="text-[10px] uppercase tracking-wider font-semibold text-slate-400">
            Total Consolidado
          </span>
          <span className="text-sm font-extrabold text-navy-900">
            {formatCompactCurrency(total)}
          </span>
        </div>
      </div>

      <div className="space-y-1.5 pt-3 border-t border-slate-100 text-xs">
        {slices.map((s, idx) => (
          <div key={s.name} className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span
                className="w-2.5 h-2.5 rounded-full shrink-0"
                style={{ backgroundColor: colors[idx % colors.length] }}
              />
              <span className="text-slate-600 font-medium">{s.name}</span>
            </div>
            <div className="font-semibold text-slate-900">
              {formatCompactCurrency(s.value)}{' '}
              <span className="text-slate-400 font-normal">
                ({formatPercent(s.value, total)})
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function PainelProvisoesMaterialView({ filtersData }) {
  const [ano, setAno] = useState('2026');
  const [ugBeneficiada, setUgBeneficiada] = useState('TODAS');
  const [acaoGoverno, setAcaoGoverno] = useState('TODAS');
  const [ugSearch, setUgSearch] = useState('');
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
        if (acaoGoverno) params.set('acao_governo', acaoGoverno);
        const res = await fetch(`/api/dashboard/provisoes-material?${params.toString()}`);
        const json = await res.json();
        if (active) setData(json);
      } catch (e) {
        console.error(e);
      } finally {
        if (active) setLoading(false);
      }
    }
    load();
    return () => {
      active = false;
    };
  }, [ano, ugBeneficiada, acaoGoverno]);

  const ugsFiltered = (filtersData?.ugs_beneficiadas || []).filter(
    (u) =>
      !ugSearch ||
      u.codigo.toLowerCase().includes(ugSearch.toLowerCase()) ||
      u.nome.toLowerCase().includes(ugSearch.toLowerCase())
  );

  const pt = data?.provisoes_totals || {};
  const mt = data?.material_totals || {};

  const totalRecebidas =
    Number(pt.provisao_rcb || 0) +
    Number(pt.destaque_rcb || 0) +
    Number(pt.rpnp_insc || 0);
  const totalLiquidadas =
    Number(pt.provisao_liquidada || 0) +
    Number(pt.destaque_liquidado || 0) +
    Number(pt.rpnp_liq || 0);
  const totalALiquidar =
    Number(pt.provisao_a_liquidar || 0) +
    Number(pt.destaque_a_liquidar || 0) +
    Number(pt.rpnp_a_liq || 0);

  const totalPatrimonio =
    Number(mt.saldo_material_estoque || 0) +
    Number(mt.saldo_material_permanente || 0);

  return (
    <div className="space-y-6">
      {/* Barra de Filtros do Manual (Seção 4) */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4">
        <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-navy-800 mb-3">
          <Filter className="w-4 h-4 text-gold-500" />
          Filtros
        </div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">
              Exercício (<code className="text-navy-800">Ano</code>)
            </label>
            <select
              value={ano}
              onChange={(e) => setAno(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-xs font-semibold bg-white"
            >
              <option value="TODOS">Todos os Exercícios (2025 + 2026)</option>
              <option value="2026">2026</option>
              <option value="2025">2025</option>
            </select>
          </div>

          <div className="md:col-span-2">
            <label className="block text-xs font-semibold text-slate-600 mb-1">
              UG Beneficiada (<code className="text-navy-800">dfm.vw_ug_custos</code>)
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={ugSearch}
                onChange={(e) => setUgSearch(e.target.value)}
                placeholder="Buscar código ou nome da OM..."
                className="w-44 rounded-lg border border-slate-300 px-2.5 py-2 text-xs"
              />
              <select
                value={ugBeneficiada}
                onChange={(e) => setUgBeneficiada(e.target.value)}
                className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-xs bg-white truncate"
              >
                <option value="TODAS">Todas as UGs Beneficiadas ({ugsFiltered.length})</option>
                {ugsFiltered.map((u) => (
                  <option key={u.codigo} value={u.codigo}>
                    {u.codigo} — {u.nome}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">
              Ação de Governo
            </label>
            <select
              value={acaoGoverno}
              onChange={(e) => setAcaoGoverno(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-xs bg-white"
            >
              <option value="TODAS">Todas as Ações</option>
              {(filtersData?.acoes_governo || []).map((a) => (
                <option key={a.codigo} value={a.codigo}>
                  {a.codigo} — {a.nome}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* 6.1 Visão Geral de Provisões + 6.2 Composição do Material (4 Gráficos de Rosca do Manual) */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-5">
        <DonutCard
          title="Composição das Provisões (Recebidas)"
          subtitle="Créditos disponíveis (Provisão, Destaque e RPNP Inscrito)"
          total={totalRecebidas}
          colors={DONUT_COLORS_RCB}
          badgeText={`${formatNumber(pt.ugs_distintas)} UGs`}
          slices={[
            { name: 'Provisão Recebida', value: Number(pt.provisao_rcb || 0) },
            { name: 'RPNP Inscrito', value: Number(pt.rpnp_insc || 0) },
            { name: 'Destaque Recebido', value: Number(pt.destaque_rcb || 0) },
          ]}
        />

        <DonutCard
          title="Composição das Provisões Liquidadas"
          subtitle="Execução efetiva do orçamento cuyo fato gerador ocorreu"
          total={totalLiquidadas}
          colors={DONUT_COLORS_LIQ}
          badgeText={`Execução: ${formatPercent(totalLiquidadas, totalRecebidas)}`}
          slices={[
            { name: 'Provisão Liquidada', value: Number(pt.provisao_liquidada || 0) },
            { name: 'RPNP Liquidado', value: Number(pt.rpnp_liq || 0) },
            { name: 'Destaque Liquidado', value: Number(pt.destaque_liquidado || 0) },
          ]}
        />

        <DonutCard
          title="Composição das Provisões a Liquidar"
          subtitle="Saldo pendente com potencialidade de se transformar em custo"
          total={totalALiquidar}
          colors={DONUT_COLORS_ALIQ}
          badgeText="Saldos Pendentes"
          slices={[
            { name: 'Provisão a Liquidar', value: Number(pt.provisao_a_liquidar || 0) },
            { name: 'RPNP a Liquidar', value: Number(pt.rpnp_a_liq || 0) },
            { name: 'Destaque a Liquidar', value: Number(pt.destaque_a_liquidar || 0) },
          ]}
        />

        <DonutCard
          title="Composição do Material da MB"
          subtitle="Situação patrimonial: Estoque vs. Permanente (dfm.tb_saldo_material_mb)"
          total={totalPatrimonio}
          colors={MATERIAL_COLORS}
          badgeText={`${formatNumber(mt.ugs_com_material)} OMs`}
          slices={[
            { name: 'Material Permanente', value: Number(mt.saldo_material_permanente || 0) },
            { name: 'Material em Estoque', value: Number(mt.saldo_material_estoque || 0) },
          ]}
        />
      </div>

      {/* Seção 6.2 e 7.2: Provisões - Tabela Analítica Pivot (dfm.vw_provisoes_pivot) */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="px-6 py-4 bg-navy-900 text-white flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h3 className="font-bold text-base flex items-center gap-2">
              <Layers className="w-4 h-4 text-gold-400" />
              Provisões por Ação de Governo
            </h3>
          </div>
          <div className="flex items-center gap-3 text-xs bg-navy-950/80 px-3.5 py-2 rounded-lg border border-navy-700">
            <div>
              <span className="text-slate-400">Estoque (Sem Duplicar): </span>
              <strong className="text-emerald-400">{formatCompactCurrency(mt.saldo_material_estoque)}</strong>
            </div>
            <span className="text-slate-600">|</span>
            <div>
              <span className="text-slate-400">Permanente: </span>
              <strong className="text-gold-400">{formatCompactCurrency(mt.saldo_material_permanente)}</strong>
            </div>
          </div>
        </div>

        <div className="overflow-x-auto max-h-96">
          <table className="w-full text-xs text-left whitespace-nowrap">
            <thead className="bg-slate-100 text-slate-700 sticky top-0 border-b border-slate-200">
              <tr>
                <th className="py-2.5 px-3">Ação Governo</th>
                <th className="py-2.5 px-3">Descrição da Ação</th>
                <th className="py-2.5 px-3 text-right">Provisão Recebida</th>
                <th className="py-2.5 px-3 text-right">Destaque Recebido</th>
                <th className="py-2.5 px-3 text-right">RPNP Inscrito</th>
                <th className="py-2.5 px-3 text-right text-emerald-800">Provisão Liquidada</th>
                <th className="py-2.5 px-3 text-right text-emerald-800">RPNP Liquidado</th>
                <th className="py-2.5 px-3 text-right text-amber-800">Provisão a Liquidar</th>
                <th className="py-2.5 px-3 text-right text-amber-800">RPNP a Liquidar</th>
                <th className="py-2.5 px-3 text-center">Qtd. PIs</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {(data?.pivot_acao || []).map((row) => (
                <tr
                  key={row.acao_governo}
                  onClick={() =>
                    setAcaoGoverno(acaoGoverno === row.acao_governo ? 'TODAS' : row.acao_governo)
                  }
                  className="hover:bg-blue-50/60 cursor-pointer transition-colors"
                >
                  <td className="py-2 px-3 font-mono font-bold text-navy-900">
                    {row.acao_governo}
                  </td>
                  <td className="py-2 px-3 max-w-xs truncate font-medium text-slate-800">
                    {row.acao_governo_nome}
                  </td>
                  <td className="py-2 px-3 text-right font-mono">{formatCurrency(row.provisao_rcb)}</td>
                  <td className="py-2 px-3 text-right font-mono">{formatCurrency(row.destaque_rcb)}</td>
                  <td className="py-2 px-3 text-right font-mono">{formatCurrency(row.rpnp_insc)}</td>
                  <td className="py-2 px-3 text-right font-mono font-semibold text-emerald-700">
                    {formatCurrency(row.provisao_liquidada)}
                  </td>
                  <td className="py-2 px-3 text-right font-mono text-emerald-700">
                    {formatCurrency(row.rpnp_liq)}
                  </td>
                  <td className="py-2 px-3 text-right font-mono font-semibold text-amber-700">
                    {formatCurrency(row.provisao_a_liquidar)}
                  </td>
                  <td className="py-2 px-3 text-right font-mono text-amber-700">
                    {formatCurrency(row.rpnp_a_liq)}
                  </td>
                  <td className="py-2 px-3 text-center font-mono text-slate-500">
                    {row.qtd_pi}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Top Planos Internos (PI) e Top OMs por Patrimônio de Material */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
          <div className="px-5 py-3.5 bg-slate-100 border-b border-slate-200 font-bold text-xs text-slate-800 uppercase tracking-wider">
            Detalhamento por Plano Interno (PI — Top 25 em Execução)
          </div>
          <div className="overflow-x-auto max-h-80">
            <table className="w-full text-xs text-left whitespace-nowrap">
              <thead className="bg-slate-50 text-slate-600 sticky top-0 border-b border-slate-200">
                <tr>
                  <th className="py-2 px-3">PI</th>
                  <th className="py-2 px-3">Título do Plano Interno</th>
                  <th className="py-2 px-3 text-right">Provisão Recebida</th>
                  <th className="py-2 px-3 text-right">Provisão Liquidada</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {(data?.top_pis || []).map((p) => (
                  <tr key={p.pi} className="hover:bg-slate-50">
                    <td className="py-1.5 px-3 font-mono font-bold text-navy-900">{p.pi}</td>
                    <td className="py-1.5 px-3 max-w-xs truncate text-slate-700">{p.pi_nome}</td>
                    <td className="py-1.5 px-3 text-right font-mono">{formatCurrency(p.provisao_rcb)}</td>
                    <td className="py-1.5 px-3 text-right font-mono font-semibold text-emerald-700">
                      {formatCurrency(p.provisao_liquidada)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
          <div className="px-5 py-3.5 bg-slate-100 border-b border-slate-200 font-bold text-xs text-slate-800 uppercase tracking-wider">
            Posição Patrimonial por OM (<code className="text-navy-900">dfm.tb_saldo_material_mb</code>)
          </div>
          <div className="overflow-x-auto max-h-80">
            <table className="w-full text-xs text-left whitespace-nowrap">
              <thead className="bg-slate-50 text-slate-600 sticky top-0 border-b border-slate-200">
                <tr>
                  <th className="py-2 px-3">Ano</th>
                  <th className="py-2 px-3">UG Beneficiada</th>
                  <th className="py-2 px-3 text-right">Material em Estoque</th>
                  <th className="py-2 px-3 text-right">Material Permanente</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {(data?.top_material_oms || []).map((m, idx) => (
                  <tr
                    key={`${m.ano}-${m.ug_beneficiada_acc}-${idx}`}
                    onClick={() => setUgBeneficiada(m.ug_beneficiada_acc)}
                    className="hover:bg-blue-50/50 cursor-pointer"
                  >
                    <td className="py-1.5 px-3 font-mono">{m.ano}</td>
                    <td className="py-1.5 px-3 max-w-xs truncate font-medium text-navy-900">
                      {m.ug_beneficiada_acc} — {m.ug_beneficiada_nome}
                    </td>
                    <td className="py-1.5 px-3 text-right font-mono">
                      {m.saldo_material_estoque === null ? (
                        <span className="italic text-slate-400">NULL</span>
                      ) : (
                        formatCurrency(m.saldo_material_estoque)
                      )}
                    </td>
                    <td className="py-1.5 px-3 text-right font-mono font-semibold text-navy-900">
                      {m.saldo_material_permanente === null ? (
                        <span className="italic text-slate-400">NULL</span>
                      ) : (
                        formatCurrency(m.saldo_material_permanente)
                      )}
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
