import React, { useEffect, useState } from 'react';
import {
  Database,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Search,
  Code2,
  Copy,
  Check,
  Table,
  ChevronLeft,
  ChevronRight,
  Server,
} from 'lucide-react';
import { formatCurrency, formatNumber } from '../utils/formatters';

const TABLE_OPTIONS = [
  { id: 'tb_provisoes', prefix: '01 • dfm.tb_provisoes (Provisões Recebidas)' },
  { id: 'tb_saldo_material_mb', prefix: '02 • dfm.tb_saldo_material_mb (Saldo de Material)' },
  { id: 'tb_custos_atividade', prefix: '03 • dfm.tb_custos_atividade (Custos por Atividade)' },
  { id: 'tb_custos_ugr_na_liq', prefix: '04 • dfm.tb_custos_ugr_na_liq (Custos Liquidados por UGR)' },
  { id: 'tb_custos_atividade_mes', prefix: '05 • dfm.tb_custos_atividade_mes (Custos Mensais)' },
];

export default function ControleGovernancaView({ statusData, onDatabaseUpdated }) {
  const [selectedTable, setSelectedTable] = useState('tb_custos_atividade');
  const [search, setSearch] = useState('');
  const [ano, setAno] = useState('TODOS');
  const [page, setPage] = useState(0);
  const [explorerData, setExplorerData] = useState(null);
  const [ddlSql, setDdlSql] = useState('');
  const [copied, setCopied] = useState(false);

  // Estado de configuração PostgreSQL
  const [pgForm, setPgForm] = useState({
    enabled: false,
    host: 'localhost',
    port: 5432,
    database: 'DFM_70',
    user: 'postgres',
    password: '',
    schema: 'dfm',
  });
  const [pgStatusMsg, setPgStatusMsg] = useState(null);
  const [testingPg, setTestingPg] = useState(false);

  const countMap = statusData?.table_counts || {};
  const limit = 50;

  useEffect(() => {
    fetch('/api/schema-sql')
      .then((r) => r.text())
      .then(setDdlSql)
      .catch(console.error);

    fetch('/api/db-config')
      .then((r) => r.json())
      .then((cfg) => {
        setPgForm((prev) => ({
          ...prev,
          enabled: cfg.enabled ?? false,
          host: cfg.host || 'localhost',
          port: cfg.port || 5432,
          database: cfg.database || 'DFM_70',
          user: cfg.user || 'postgres',
          schema: cfg.schema || 'dfm',
        }));
      })
      .catch(console.error);
  }, []);

  useEffect(() => {
    let active = true;
    async function loadExplorer() {
      const params = new URLSearchParams({
        limit: String(limit),
        offset: String(page * limit),
        ano,
      });
      if (search.trim()) params.set('search', search.trim());
      const res = await fetch(`/api/explorer/${selectedTable}?${params.toString()}`);
      const json = await res.json();
      if (active) setExplorerData(json);
    }
    loadExplorer();
    return () => {
      active = false;
    };
  }, [selectedTable, search, ano, page, statusData]);

  async function handleSavePgConfig(e) {
    e.preventDefault();
    setTestingPg(true);
    setPgStatusMsg(null);
    try {
      const res = await fetch('/api/db-config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(pgForm),
      });
      const data = await res.json();
      setPgStatusMsg(data.connection_test);
      if (onDatabaseUpdated) onDatabaseUpdated();
    } catch (err) {
      setPgStatusMsg({ connected: false, message: err.message });
    } finally {
      setTestingPg(false);
    }
  }

  async function handleTestPgOnly() {
    setTestingPg(true);
    setPgStatusMsg(null);
    try {
      const res = await fetch('/api/db-config/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(pgForm),
      });
      const data = await res.json();
      setPgStatusMsg(data);
    } catch (err) {
      setPgStatusMsg({ connected: false, message: err.message });
    } finally {
      setTestingPg(false);
    }
  }

  function handleCopySql() {
    navigator.clipboard.writeText(ddlSql);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="space-y-6">
      {/* Conector Direto PostgreSQL (schema dfm) */}
      <div className="bg-white rounded-[20px] shadow-sm border-[1.5px] border-[#E2E8F0] p-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-100">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#EDF4FF] text-[#1351B4] flex items-center justify-center">
              <Server className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-extrabold text-[15px] text-[#071D41]">
                Conexão com o Banco de Dados PostgreSQL (<code className="text-[#1351B4]">schema dfm</code>)
              </h3>
              <p className="text-xs text-slate-500">
                O sistema mantém um banco local SQLite ativo automaticamente e pode sincronizar cada carga direto no PostgreSQL.
              </p>
            </div>
          </div>

          <label className="inline-flex items-center gap-2 cursor-pointer bg-[#F8FAFC] border border-[#E2E8F0] px-3.5 py-2 rounded-full">
            <input
              type="checkbox"
              checked={pgForm.enabled}
              onChange={(e) => setPgForm({ ...pgForm, enabled: e.target.checked })}
              className="rounded text-[#1351B4]"
            />
            <span className="text-xs font-bold text-[#071D41]">
              Ativar escrita direta no PostgreSQL
            </span>
          </label>
        </div>

        <form onSubmit={handleSavePgConfig} className="mt-4 grid grid-cols-1 sm:grid-cols-6 gap-3">
          <div>
            <label className="block text-[11px] font-bold text-slate-600 mb-1">Host</label>
            <input
              type="text"
              value={pgForm.host}
              onChange={(e) => setPgForm({ ...pgForm, host: e.target.value })}
              className="w-full rounded-xl border border-slate-300 px-3 py-2 text-xs font-semibold"
              placeholder="localhost"
            />
          </div>
          <div>
            <label className="block text-[11px] font-bold text-slate-600 mb-1">Porta</label>
            <input
              type="number"
              value={pgForm.port}
              onChange={(e) => setPgForm({ ...pgForm, port: Number(e.target.value) })}
              className="w-full rounded-xl border border-slate-300 px-3 py-2 text-xs font-semibold"
              placeholder="5432"
            />
          </div>
          <div>
            <label className="block text-[11px] font-bold text-slate-600 mb-1">Banco (Database)</label>
            <input
              type="text"
              value={pgForm.database}
              onChange={(e) => setPgForm({ ...pgForm, database: e.target.value })}
              className="w-full rounded-xl border border-slate-300 px-3 py-2 text-xs font-semibold"
              placeholder="DFM_70"
            />
          </div>
          <div>
            <label className="block text-[11px] font-bold text-slate-600 mb-1">Schema</label>
            <input
              type="text"
              value={pgForm.schema}
              onChange={(e) => setPgForm({ ...pgForm, schema: e.target.value })}
              className="w-full rounded-xl border border-slate-300 px-3 py-2 text-xs font-semibold"
              placeholder="dfm"
            />
          </div>
          <div>
            <label className="block text-[11px] font-bold text-slate-600 mb-1">Usuário</label>
            <input
              type="text"
              value={pgForm.user}
              onChange={(e) => setPgForm({ ...pgForm, user: e.target.value })}
              className="w-full rounded-xl border border-slate-300 px-3 py-2 text-xs font-semibold"
              placeholder="postgres"
            />
          </div>
          <div>
            <label className="block text-[11px] font-bold text-slate-600 mb-1">Senha</label>
            <input
              type="password"
              value={pgForm.password}
              onChange={(e) => setPgForm({ ...pgForm, password: e.target.value })}
              className="w-full rounded-xl border border-slate-300 px-3 py-2 text-xs font-semibold"
              placeholder="••••••••"
            />
          </div>

          <div className="sm:col-span-6 flex flex-wrap items-center justify-between gap-3 pt-2">
            <div>
              {pgStatusMsg && (
                <span
                  className={`inline-flex items-center gap-1.5 text-xs font-bold px-3 py-1.5 rounded-full ${
                    pgStatusMsg.connected
                      ? 'bg-[#E8F8EC] text-[#168821]'
                      : 'bg-amber-50 text-amber-800'
                  }`}
                >
                  ● {pgStatusMsg.message}
                </span>
              )}
            </div>

            <div className="flex items-center gap-2.5">
              <button
                type="button"
                disabled={testingPg}
                onClick={handleTestPgOnly}
                className="px-4 py-2 rounded-full bg-[#EDF4FF] hover:bg-blue-100 text-[#1351B4] text-xs font-bold"
              >
                Testar Conexão
              </button>
              <button
                type="submit"
                disabled={testingPg}
                className="px-5 py-2 rounded-full bg-[#1351B4] hover:bg-[#0C326F] text-white text-xs font-bold"
              >
                Salvar Configuração
              </button>
            </div>
          </div>
        </form>
      </div>

      {/* Histórico de Atualização das 5 Tabelas */}
      <div className="bg-white rounded-[20px] shadow-sm border-[1.5px] border-[#E2E8F0] overflow-hidden">
        <div className="px-6 py-4 bg-[#071D41] text-white flex items-center justify-between">
          <h3 className="font-bold text-sm flex items-center gap-2">
            <Database className="w-4 h-4 text-[#FFCD07]" />
            Histórico de Cargas no Banco (<code className="text-[#FFCD07]">dfm.controle_atualizacao</code>)
          </h3>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left whitespace-nowrap">
            <thead className="bg-[#F8FAFC] text-slate-700 border-b border-slate-200">
              <tr>
                <th className="py-3 px-4">Tabela (Schema dfm)</th>
                <th className="py-3 px-4">Arquivo Carregado</th>
                <th className="py-3 px-4">Protocolo</th>
                <th className="py-3 px-4">Data/Hora</th>
                <th className="py-3 px-4 text-center">Status</th>
                <th className="py-3 px-4 text-right">Registros Ativos</th>
                <th className="py-3 px-4 text-right">Volume Conciliado</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {(statusData?.controle_atualizacao || []).map((row) => (
                <tr key={row.nome_tabela} className="hover:bg-slate-50">
                  <td
                    className="py-3 px-4 font-bold text-[#1351B4]"
                    style={{ fontFamily: "'JetBrains Mono', monospace" }}
                  >
                    {row.nome_tabela}
                  </td>
                  <td className="py-3 px-4 text-slate-700">{row.arquivo_origem}</td>
                  <td
                    className="py-3 px-4 font-bold text-[#071D41]"
                    style={{ fontFamily: "'JetBrains Mono', monospace" }}
                  >
                    {row.protocolo_carga || '2026NL000100'}
                  </td>
                  <td className="py-3 px-4 text-slate-600">
                    {row.data_hora_fim || row.data_hora_inicio}
                  </td>
                  <td className="py-3 px-4 text-center">
                    <span
                      className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full font-bold text-[11px] ${
                        row.status === 'SUCESSO'
                          ? 'bg-[#E8F8EC] text-[#168821]'
                          : row.status === 'EM_ANDAMENTO'
                          ? 'bg-amber-100 text-amber-800'
                          : 'bg-red-100 text-red-800'
                      }`}
                    >
                      {row.status === 'SUCESSO' && <CheckCircle2 className="w-3 h-3" />}
                      {row.status === 'EM_ANDAMENTO' && <Clock className="w-3 h-3" />}
                      {row.status === 'ERRO' && <AlertTriangle className="w-3 h-3" />}
                      {row.status}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-right font-bold">
                    {formatNumber(row.total_linhas_carregadas)}
                  </td>
                  <td className="py-3 px-4 text-right font-bold text-[#071D41]">
                    {formatCurrency(row.soma_financeira_carregada)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Explorador de Registros das 5 Tabelas */}
      <div className="bg-white rounded-[20px] shadow-sm border-[1.5px] border-[#E2E8F0] overflow-hidden">
        <div className="p-4 bg-[#F8FAFC] border-b border-slate-200 flex flex-col lg:flex-row lg:items-center justify-between gap-3">
          <div className="flex items-center gap-2 font-extrabold text-sm text-[#071D41]">
            <Table className="w-4 h-4 text-[#1351B4]" />
            Explorador de Registros das 5 Tabelas (Arquivos 01 a 05)
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <select
              value={selectedTable}
              onChange={(e) => {
                setSelectedTable(e.target.value);
                setPage(0);
              }}
              className="rounded-xl border border-slate-300 bg-white px-3 py-1.5 text-xs font-bold text-[#071D41]"
            >
              {TABLE_OPTIONS.map((t) => {
                const cnt = countMap[t.id];
                const label =
                  cnt !== undefined ? `${t.prefix} (${formatNumber(cnt)} reg.)` : t.prefix;
                return (
                  <option key={t.id} value={t.id}>
                    {label}
                  </option>
                );
              })}
            </select>

            <select
              value={ano}
              onChange={(e) => {
                setAno(e.target.value);
                setPage(0);
              }}
              className="rounded-xl border border-slate-300 bg-white px-3 py-1.5 text-xs font-bold"
            >
              <option value="TODOS">Todos os Anos</option>
              <option value="2026">2026</option>
              <option value="2025">2025</option>
            </select>

            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2" />
              <input
                type="text"
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setPage(0);
                }}
                placeholder="Filtrar UG, Ação, Atividade, NE..."
                className="pl-8 pr-3 py-1.5 rounded-xl border border-slate-300 text-xs w-60"
              />
            </div>
          </div>
        </div>

        <div className="overflow-x-auto max-h-96">
          <table className="w-full text-xs text-left whitespace-nowrap">
            <thead className="bg-[#071D41] text-white sticky top-0">
              <tr>
                {(explorerData?.columns || []).map((c) => (
                  <th
                    key={c}
                    className="py-2.5 px-3 text-[11px]"
                    style={{ fontFamily: "'JetBrains Mono', monospace" }}
                  >
                    {c}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {(explorerData?.rows || []).map((row, idx) => (
                <tr key={idx} className="hover:bg-slate-50">
                  {(explorerData?.columns || []).map((c) => (
                    <td
                      key={c}
                      className="py-2 px-3 text-[11px] text-slate-700"
                      style={{ fontFamily: "'JetBrains Mono', monospace" }}
                    >
                      {row[c] === null || row[c] === '' ? (
                        <span className="italic text-slate-400">NULL</span>
                      ) : (
                        String(row[c])
                      )}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="px-4 py-3 bg-[#F8FAFC] border-t border-slate-200 flex items-center justify-between text-xs text-slate-600">
          <div>
            Total de registros na tabela: <strong>{formatNumber(explorerData?.total || 0)}</strong>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={page === 0}
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              className="p-1 rounded border border-slate-300 bg-white disabled:opacity-40"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span>Página {page + 1}</span>
            <button
              type="button"
              disabled={(page + 1) * limit >= (explorerData?.total || 0)}
              onClick={() => setPage((p) => p + 1)}
              className="p-1 rounded border border-slate-300 bg-white disabled:opacity-40"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Script DDL Oficial PostgreSQL (Tabelas 01 a 05) */}
      <div className="bg-white rounded-[20px] shadow-sm border-[1.5px] border-[#E2E8F0] overflow-hidden">
        <div className="px-6 py-4 bg-[#071D41] text-white flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <Code2 className="w-5 h-5 text-[#FFCD07]" />
            <div>
              <h3 className="font-bold text-sm">
                Script DDL Oficial PostgreSQL (<code className="text-[#FFCD07]">schema dfm</code> — Tabelas 01 a 05)
              </h3>
              <p className="text-[11px] text-slate-300">
                Inclui <code>tb_provisoes</code> (01), <code>tb_saldo_material_mb</code> (02),{' '}
                <code>tb_custos_atividade</code> (03), <code>tb_custos_ugr_na_liq</code> (04) e{' '}
                <code>tb_custos_atividade_mes</code> (05).
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={handleCopySql}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full bg-[#FFCD07] hover:bg-amber-400 text-[#071D41] font-extrabold text-xs transition-colors"
          >
            {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
            {copied ? 'DDL Copiado!' : 'Copiar DDL PostgreSQL'}
          </button>
        </div>
        <pre className="p-4 bg-slate-950 text-slate-200 text-xs font-mono overflow-x-auto max-h-96 leading-relaxed">
          {ddlSql}
        </pre>
      </div>
    </div>
  );
}
