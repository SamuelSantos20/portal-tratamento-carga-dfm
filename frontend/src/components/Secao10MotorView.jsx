import React, { useState } from 'react';
import {
  AlertTriangle,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Sparkles,
} from 'lucide-react';
import { formatCurrency, formatNumber } from '../utils/formatters';

const BASES_OFICIAIS = [
  {
    code: '01',
    table: 'tb_provisoes',
    name: 'Provisões Recebidas',
    schemaLabel: 'dfm.tb_provisoes',
  },
  {
    code: '02',
    table: 'tb_saldo_material_mb',
    name: 'Saldo de Material e Patrimônio',
    schemaLabel: 'dfm.tb_saldo_material_mb',
  },
  {
    code: '03',
    table: 'tb_custos_atividade',
    name: 'Custos por Atividade',
    schemaLabel: 'dfm.tb_custos_atividade',
  },
  {
    code: '04',
    table: 'tb_custos_ugr_na_liq',
    name: 'Custos Liquidados por UGR',
    schemaLabel: 'dfm.tb_custos_ugr_na_liq',
  },
  {
    code: '05',
    table: 'tb_custos_atividade_mes',
    name: 'Custos Mensais por Atividade',
    schemaLabel: 'dfm.tb_custos_atividade_mes',
  },
];

export default function Secao10MotorView({
  statusData,
  onDatabaseUpdated,
  onOpenDatabaseTab,
  sessionId,
  onAnalysisUpdated,
}) {
  const [step, setStep] = useState(1);
  const [targetTable, setTargetTable] = useState('AUTO');
  const [isDragging, setIsDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [committing, setCommitting] = useState(false);
  const [result, setResult] = useState(null);
  const [commitData, setCommitData] = useState(null);
  const [error, setError] = useState(null);
  const [showFullTable, setShowFullTable] = useState(false);

  const tableCounts = statusData?.table_counts || {};

  // Etapa 1 -> Etapa 2: Trata a planilha e exibe a prévia
  async function handleFileUpload(file) {
    if (!file) return;
    if (!sessionId) { setError('Aguarde a abertura da sessão de análise.'); return; }
    setLoading(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('target_table', targetTable);
      formData.append('apply_to_db', 'false');
      formData.append('session_id', sessionId);

      const res = await fetch('/api/secao10/process', {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Falha ao tratar a planilha.');
      }
      setResult(data);
      onAnalysisUpdated?.();
      setStep(2);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  // Simulação com 1 clique para testar qualquer uma das 5 tabelas
  async function handleSimulateTable(tableName) {
    if (!sessionId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/secao10/simulate/${tableName}?session_id=${sessionId}`, {
        method: 'POST',
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Falha ao simular planilha.');
      }
      setResult(data);
      onAnalysisUpdated?.();
      setStep(2);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  // Etapa 2 -> Etapa 3: Confirma e envia para o banco (SQLite + PostgreSQL dfm)
  async function handleConfirmCommit() {
    if (!result?.table_name) return;
    setCommitting(true);
    setError(null);
    try {
      const res = await fetch(`/api/secao10/commit/${result.table_name}?session_id=${sessionId}`, {
        method: 'POST',
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Falha ao gravar no banco de dados.');
      }
      setCommitData(data);
      onAnalysisUpdated?.();
      setStep(3);
      if (onDatabaseUpdated) {
        onDatabaseUpdated();
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setCommitting(false);
    }
  }

  function handleDrop(e) {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer?.files?.[0];
    if (file) {
      handleFileUpload(file);
    }
  }

  // Calcula soma financeira total do lote tratado
  const totalConciliado = (result?.reconciliation || []).reduce(
    (acc, r) => acc + Number(r.soma_tratada || 0),
    0
  );
  const diffTotal = (result?.reconciliation || []).reduce(
    (acc, r) => acc + Math.abs(Number(r.diferenca || 0)),
    0
  );

  // Extrai 3 linhas resumidas amigáveis para a Etapa 2
  function getFriendlySampleRows() {
    if (!result?.preview_rows || !result?.preview_headers) return [];
    const headers = result.preview_headers;
    const rows = result.preview_rows.slice(0, 4);

    return rows.map((r) => {
      const obj = {};
      headers.forEach((h, i) => {
        obj[h] = r[i];
      });

      const ugCode =
        obj.ug_beneficiada_acc || obj.ug_emitente || obj.ug_responsavel || obj.ug_executora || '';
      const ugName =
        obj.ug_beneficiada_nome ||
        obj.ug_emitente_nome ||
        obj.ug_responsavel_nome ||
        obj.ug_executora_nome ||
        'UNIDADE GESTORA';

      const contextLabel =
        obj.macroatividades_mb ||
        obj.acao_governo_nome ||
        obj.ne ||
        (obj.mes_referencia_acc ? `${obj.mes_referencia_acc}/${obj.ano_referencia_acc}` : '') ||
        `ANO ${obj.ano_emissao || obj.ano || '2026'}`;

      const rawVal =
        obj.valor_dh ??
        obj.detacusto_dh_rs ??
        obj.provisao_rcb ??
        obj.saldo_material_permanente ??
        0;

      return {
        left: `UG ${ugCode} • ${ugName}`,
        middle: contextLabel,
        right: formatCurrency(Number(rawVal || 0)),
      };
    });
  }

  return (
    <div className="flex flex-col items-center gap-6">
      {/* STEPPER EM PÍLULA — 3 PASSOS */}
      <nav className="bg-white border-[1.5px] border-[#E2E8F0] rounded-full px-5 py-3 inline-flex flex-wrap items-center gap-3.5 shadow-sm">
        <button
          type="button"
          onClick={() => setStep(1)}
          className={`px-5 py-2.5 rounded-full text-xs font-bold transition-all ${
            step === 1
              ? 'bg-[#1351B4] text-white'
              : 'bg-[#E8F8EC] text-[#168821]'
          }`}
        >
          {step > 1 ? '✓ 1. Importar Planilha' : '1. Importar Planilha'}
        </button>

        <button
          type="button"
          disabled={!result}
          onClick={() => result && setStep(2)}
          className={`px-5 py-2.5 rounded-full text-xs font-bold transition-all disabled:opacity-60 ${
            step === 2
              ? 'bg-[#1351B4] text-white'
              : step > 2
              ? 'bg-[#E8F8EC] text-[#168821]'
              : 'bg-[#F8FAFC] text-[#64748B]'
          }`}
        >
          {step > 2 ? '✓ 2. Tratamento Automático' : '2. Tratamento Automático'}
        </button>

        <button
          type="button"
          disabled={!commitData}
          onClick={() => commitData && setStep(3)}
          className={`px-5 py-2.5 rounded-full text-xs font-bold transition-all disabled:opacity-60 ${
            step === 3
              ? 'bg-[#1351B4] text-white'
              : 'bg-[#F8FAFC] text-[#64748B]'
          }`}
        >
          3. Enviado ao Banco
        </button>
      </nav>

      {/* ALERTA DE ERRO SE HOUVER */}
      {error && (
        <div className="w-full max-w-[1120px] bg-red-50 border-l-4 border-red-600 p-4 rounded-xl flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
          <div>
            <h4 className="text-sm font-bold text-red-900">Atenção no Processamento</h4>
            <p className="text-xs text-red-700 mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {/* =================================================================== */}
      {/* PASSO 1: IMPORTAR PLANILHA                                          */}
      {/* =================================================================== */}
      {step === 1 && (
        <div className="w-full grid grid-cols-1 lg:grid-cols-12 gap-7">
          {/* Card Esquerdo: Diagrama + Área de Upload */}
          <div className="lg:col-span-7 bg-white border-[1.5px] border-[#E2E8F0] rounded-[20px] p-8 sm:p-9 flex flex-col justify-between">
            {/* Diagrama Visual de 3 Etapas */}
            <div className="w-full bg-[#F8FAFC] rounded-[14px] py-3 px-4 mb-6">
              <svg width="100%" height="76" viewBox="0 0 700 84" fill="none">
                <circle cx="115" cy="42" r="22" fill="#EDF4FF" stroke="#1351B4" strokeWidth="1.5" />
                <rect x="107" y="34" width="16" height="16" rx="2" stroke="#1351B4" strokeWidth="1.8" />
                <line x1="111" y1="39" x2="119" y2="39" stroke="#1351B4" strokeWidth="1.5" />
                <line x1="111" y1="44" x2="119" y2="44" stroke="#1351B4" strokeWidth="1.5" />
                <path d="M160 42 H300" stroke="#1351B4" strokeWidth="2" strokeDasharray="4 4" />
                <circle cx="230" cy="42" r="4" fill="#FFCD07" />
                <circle cx="350" cy="42" r="24" fill="#FFFBEB" stroke="#FFCD07" strokeWidth="2" />
                <path
                  d="M350 30 L353 39 L362 42 L353 45 L350 54 L347 45 L338 42 L347 39 Z"
                  fill="#1351B4"
                />
                <path d="M400 42 H540" stroke="#168821" strokeWidth="2" strokeDasharray="4 4" />
                <circle cx="470" cy="42" r="4" fill="#168821" />
                <circle cx="585" cy="42" r="22" fill="#E8F8EC" stroke="#168821" strokeWidth="1.5" />
                <ellipse cx="585" cy="36" rx="9" ry="4" stroke="#168821" strokeWidth="1.8" />
                <path
                  d="M576 36 V48 C576 50 594 50 594 48 V36"
                  stroke="#168821"
                  strokeWidth="1.8"
                />
              </svg>
            </div>

            {/* Seletor de Destino (Automático ou Manual 01..05) */}
            <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
              <label className="text-xs font-bold text-[#334155]">
                Modo de Identificação da Tabela:
              </label>
              <select
                value={targetTable}
                onChange={(e) => setTargetTable(e.target.value)}
                className="rounded-xl border border-[#CBD5E1] bg-[#F8FAFC] px-3.5 py-2 text-xs font-bold text-[#071D41]"
              >
                <option value="AUTO">✦ Reconhecimento Automático (01 a 05)</option>
                {BASES_OFICIAIS.map((b) => (
                  <option key={b.table} value={b.table}>
                    Arquivo {b.code} • {b.name} ({b.schemaLabel})
                  </option>
                ))}
              </select>
            </div>

            {/* Dropzone Ilustrada */}
            <label
              onDragOver={(e) => {
                e.preventDefault();
                setIsDragging(true);
              }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleDrop}
              className={`cursor-pointer border-2 rounded-2xl p-9 text-center flex flex-col items-center justify-center gap-3.5 transition-all ${
                isDragging
                  ? 'border-[#FFCD07] bg-[#FFFBEB]'
                  : 'border-[#1351B4] bg-[#EDF4FF] hover:bg-[#e3eeff]'
              }`}
            >
              <input
                type="file"
                accept=".csv,.xlsx,.xls,.txt"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) handleFileUpload(f);
                  e.target.value = '';
                }}
                className="hidden"
              />

              {loading ? (
                <div className="py-6 flex flex-col items-center gap-3">
                  <RefreshCw className="w-11 h-11 text-[#1351B4] animate-spin" />
                  <div className="text-base font-extrabold text-[#071D41]">
                    Identificando estrutura e higienizando dados...
                  </div>
                </div>
              ) : (
                <>
                  <svg width="88" height="72" viewBox="0 0 88 72" fill="none">
                    <rect
                      x="14"
                      y="10"
                      width="48"
                      height="54"
                      rx="8"
                      fill="#FFFFFF"
                      stroke="#1351B4"
                      strokeWidth="2"
                    />
                    <rect x="22" y="20" width="14" height="8" rx="2" fill="#EDF4FF" />
                    <rect x="40" y="20" width="14" height="8" rx="2" fill="#EDF4FF" />
                    <rect x="22" y="32" width="14" height="8" rx="2" fill="#EDF4FF" />
                    <rect x="40" y="32" width="14" height="8" rx="2" fill="#FFFBEB" />
                    <rect x="22" y="44" width="32" height="8" rx="2" fill="#E8F8EC" />
                    <circle cx="62" cy="48" r="18" fill="#1351B4" />
                    <path
                      d="M62 55V41M62 41L56 47M62 41L68 47"
                      stroke="#FFFFFF"
                      strokeWidth="2.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                    <circle cx="20" cy="14" r="6" fill="#FFCD07" />
                  </svg>

                  <h2 className="text-lg font-extrabold text-[#071D41]">
                    Arraste a planilha para cá ou selecione do computador
                  </h2>
                  <p className="text-[13px] font-medium text-[#334155] max-w-lg">
                    O sistema identifica o modelo (.CSV ou .XLSX), separa códigos e nomes de UG,
                    remove linhas de total e prepara para envio ao banco.
                  </p>
                  <span className="mt-1 inline-flex items-center justify-center bg-[#1351B4] hover:bg-[#0C326F] text-white font-bold text-sm px-7 py-3 rounded-full shadow-sm transition-transform hover:-translate-y-0.5">
                    Selecionar Planilha no Computador
                  </span>
                </>
              )}
            </label>

            {/* Barra de Teste Rápido (Simular Planilha Bruta 01 a 05) */}
            <div className="mt-5 pt-4 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2">
              <span className="text-[11px] font-bold text-slate-500 flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-[#1351B4]" />
                Testar com amostra bruta:
              </span>
              <div className="flex flex-wrap items-center gap-1.5">
                {BASES_OFICIAIS.map((b) => (
                  <button
                    key={b.table}
                    type="button"
                    disabled={loading}
                    onClick={() => handleSimulateTable(b.table)}
                    className="px-2.5 py-1 rounded-lg bg-[#F8FAFC] hover:bg-[#EDF4FF] border border-[#E2E8F0] text-[11px] font-bold text-[#1351B4] transition-colors"
                  >
                    Simular {b.code}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Card Direito: As 5 Bases do Banco de Dados */}
          <div className="lg:col-span-5 bg-white border-[1.5px] border-[#E2E8F0] rounded-[20px] p-7 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between gap-2 mb-4">
                <h3 className="text-[15px] font-extrabold text-[#071D41]">
                  Bases do Banco de Dados (Arquivos 01 a 05)
                </h3>
                <button
                  type="button"
                  onClick={onOpenDatabaseTab}
                  className="text-[11px] font-bold text-[#1351B4] hover:underline"
                >
                  Configurar Banco →
                </button>
              </div>

              <div className="space-y-3">
                {BASES_OFICIAIS.map((b) => {
                  const cnt = tableCounts[b.table] ?? 0;
                  return (
                    <div
                      key={b.table}
                      className="bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl px-4 py-3.5 flex items-center justify-between gap-3"
                    >
                      <div className="flex items-center gap-3">
                        <span
                          className="bg-[#EDF4FF] text-[#1351B4] font-bold text-xs px-2.5 py-1.5 rounded-lg"
                          style={{ fontFamily: "'JetBrains Mono', monospace" }}
                        >
                          {b.code}
                        </span>
                        <div>
                          <div className="text-[13px] font-bold text-[#071D41]">{b.name}</div>
                          <div
                            className="text-[11px] text-slate-500"
                            style={{ fontFamily: "'JetBrains Mono', monospace" }}
                          >
                            {b.schemaLabel}
                          </div>
                        </div>
                      </div>

                      <span className="bg-[#E8F8EC] text-[#168821] text-[11px] font-bold px-3 py-1 rounded-full shrink-0">
                        ✓ {formatNumber(cnt)} registros
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="mt-6 bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl p-4 text-xs text-slate-600">
              <div className="font-bold text-[#071D41] mb-1">
                Mapeamento Oficial das Tabelas (<code className="text-[#1351B4]">schema dfm</code>)
              </div>
              <p>
                Ao confirmar o envio na Etapa 2, os registros anteriores da tabela identificada são
                substituídos pelo novo lote higienizado e conciliado.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* =================================================================== */}
      {/* PASSO 2: CONFERIR TRATAMENTO E ENVIAR AO BANCO                      */}
      {/* =================================================================== */}
      {step === 2 && result && (
        <div className="w-full max-w-[1120px] bg-white border-[1.5px] border-[#E2E8F0] rounded-[20px] p-8 sm:p-10 space-y-7">
          {/* Topo: Arquivo + Destino + Botão Verde de Confirmação */}
          {result.validation_errors?.length > 0 && <div role="alert" className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-sm text-amber-900">{result.validation_errors.map((error, index) => <p key={index}>{error}</p>)}</div>}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <h2 className="text-[22px] font-extrabold text-[#071D41]">
                {result.status === 'SUCESSO' ? 'Planilha tratada e pronta para envio' : 'Revise as pendências antes do envio'}
              </h2>
              <p className="text-[13px] font-semibold text-[#1351B4] mt-1">
                Arquivo: {result.filename} ➔ Destino: Base {result.file_code} ({result.short_name} •{' '}
                <code>dfm.{result.table_name}</code>)
              </p>
            </div>

            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => setStep(1)}
                className="px-5 py-3 rounded-full bg-[#F8FAFC] hover:bg-slate-200 text-xs font-bold text-slate-700 transition-colors"
              >
                Voltar
              </button>

              <button
                type="button"
                disabled={committing || result.status !== 'SUCESSO'}
                onClick={handleConfirmCommit}
                className="px-7 py-3.5 rounded-full bg-[#168821] hover:bg-[#126e1a] text-white text-sm font-extrabold shadow-sm transition-transform hover:-translate-y-0.5 disabled:opacity-60"
              >
                {committing
                  ? 'Enviando para o Banco...'
                  : '✓ Confirmar e Enviar para o Banco'}
              </button>
            </div>
          </div>

          {/* 3 Cards Coloridos de Resumo */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {/* 1. Arquivo Bruto */}
            <div className="bg-[#F8FAFC] border-[1.5px] border-[#E2E8F0] rounded-2xl p-6">
              <div className="text-[11px] font-extrabold text-[#64748B] uppercase">
                1. ARQUIVO BRUTO
              </div>
              <div className="text-[26px] font-extrabold text-[#071D41] mt-1.5">
                {formatNumber(result.metrics?.total_linhas_lidas || 0)} linhas
              </div>
              <div className="text-xs font-medium text-[#64748B] mt-1">
                {formatNumber(result.metrics?.linhas_totalizacao_removidas || 0)} linhas de
                totalizador removidas
              </div>
            </div>

            {/* 2. Limpeza Automática */}
            <div className="bg-[#EDF4FF] border-[1.5px] border-[#1351B4] rounded-2xl p-6">
              <div className="text-[11px] font-extrabold text-[#1351B4] uppercase">
                2. LIMPEZA AUTOMÁTICA
              </div>
              <div className="text-[26px] font-extrabold text-[#1351B4] mt-1.5">
                100% Higienizado
              </div>
              <div className="text-xs font-medium text-[#071D41] mt-1">
                {formatNumber(result.metrics?.pares_ug_desmembrados || 0)} UGs separadas •{' '}
                {formatNumber(result.metrics?.sentinelas_substituidas || 0)} sentinelas tratadas
              </div>
            </div>

            {/* 3. Valor Conciliado */}
            <div className="bg-[#E8F8EC] border-[1.5px] border-[#168821] rounded-2xl p-6">
              <div className="text-[11px] font-extrabold text-[#168821] uppercase">
                3. VALOR CONCILIADO
              </div>
              <div className="text-[24px] font-extrabold text-[#168821] mt-1.5 truncate">
                {formatCurrency(totalConciliado)}
              </div>
              <div className="text-xs font-medium text-[#071D41] mt-1">
                {formatNumber(result.metrics?.total_linhas_tratadas || 0)} registros válidos •
                Diferença {formatCurrency(diffTotal)}
              </div>
            </div>
          </div>

          {/* Amostra Limpa de Registros Prontos */}
          <div className="space-y-2.5">
            <div className="flex items-center justify-between">
              <h4 className="text-[13px] font-bold text-[#071D41]">
                Amostra dos dados prontos para entrar no banco:
              </h4>
              <button
                type="button"
                onClick={() => setShowFullTable((v) => !v)}
                className="inline-flex items-center gap-1 text-xs font-bold text-[#1351B4] hover:underline"
              >
                {showFullTable ? (
                  <>
                    Ocultar colunas completas <ChevronUp className="w-3.5 h-3.5" />
                  </>
                ) : (
                  <>
                    Ver todas as {result.preview_headers?.length || 0} colunas da tabela{' '}
                    <ChevronDown className="w-3.5 h-3.5" />
                  </>
                )}
              </button>
            </div>

            {getFriendlySampleRows().map((item, idx) => (
              <div
                key={idx}
                className="bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl px-5 py-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-2"
              >
                <span className="text-[13px] font-bold text-[#071D41]">{item.left}</span>
                <span className="text-xs font-semibold text-[#64748B]">{item.middle}</span>
                <span
                  className="text-[13px] font-bold text-[#1351B4]"
                  style={{ fontFamily: "'JetBrains Mono', monospace" }}
                >
                  {item.right}
                </span>
              </div>
            ))}
          </div>

          {/* Tabela Completa Expansível (Todas as colunas da tabela PostgreSQL) */}
          {showFullTable && (
            <div className="border border-[#E2E8F0] rounded-xl overflow-hidden">
              <div className="overflow-x-auto max-h-72">
                <table className="w-full text-xs text-left whitespace-nowrap">
                  <thead className="bg-[#071D41] text-white sticky top-0">
                    <tr>
                      {(result.preview_headers || []).map((h) => (
                        <th
                          key={h}
                          className="py-2.5 px-3 text-[11px]"
                          style={{ fontFamily: "'JetBrains Mono', monospace" }}
                        >
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {(result.preview_rows || []).slice(0, 15).map((r, rIdx) => (
                      <tr key={rIdx} className="hover:bg-slate-50">
                        {r.map((cell, cIdx) => (
                          <td
                            key={cIdx}
                            className="py-2 px-3 text-[11px] text-slate-700"
                            style={{ fontFamily: "'JetBrains Mono', monospace" }}
                          >
                            {cell === '' ? <span className="text-slate-400">NULL</span> : cell}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* =================================================================== */}
      {/* PASSO 3: COMPROVANTE DE CARGA NO BANCO                              */}
      {/* =================================================================== */}
      {step === 3 && commitData && (
        <div className="w-full max-w-[860px] bg-white border-[1.5px] border-[#E2E8F0] rounded-[24px] p-10 sm:p-12 text-center flex flex-col items-center gap-6 shadow-sm">
          {/* Selo Verde e Dourado */}
          <svg width="88" height="88" viewBox="0 0 88 88" fill="none">
            <circle
              cx="44"
              cy="44"
              r="42"
              stroke="#1351B4"
              strokeWidth="1.5"
              strokeDasharray="4 4"
              strokeOpacity="0.4"
            />
            <circle cx="44" cy="44" r="34" fill="#E8F8EC" stroke="#168821" strokeWidth="2" />
            <path
              d="M31 44.5L40 53.5L58 35.5"
              stroke="#168821"
              strokeWidth="4"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <circle cx="72" cy="20" r="7" fill="#FFCD07" />
          </svg>

          <div>
            <h2 className="text-2xl font-extrabold text-[#071D41]">
              Planilha enviada para o banco com sucesso!
            </h2>
            <p className="text-sm font-medium text-[#64748B] mt-1.5">
              Os dados da Base {commitData.file_code} ({commitData.short_name} •{' '}
              <code>dfm.{commitData.table_name}</code>) já estão atualizados para consulta.
            </p>
            {commitData.db_update?.pg_message && (
              <p className="text-xs font-bold text-[#168821] mt-1">
                {commitData.db_update.pg_message}
              </p>
            )}
          </div>

          {/* Quadro do Comprovante */}
          <div className="w-full bg-[#F8FAFC] border-[1.5px] border-[#E2E8F0] rounded-2xl p-6 grid grid-cols-2 sm:grid-cols-4 gap-6 text-left">
            <div>
              <div className="text-[10px] font-bold text-[#64748B] uppercase">
                BASE ATUALIZADA
              </div>
              <div className="text-[15px] font-extrabold text-[#071D41] mt-1">
                {commitData.short_name}
              </div>
            </div>

            <div>
              <div className="text-[10px] font-bold text-[#64748B] uppercase">
                REGISTROS SALVOS
              </div>
              <div className="text-[15px] font-extrabold text-[#071D41] mt-1">
                {formatNumber(commitData.db_update?.linhas_inseridas || 0)} linhas
              </div>
            </div>

            <div>
              <div className="text-[10px] font-bold text-[#64748B] uppercase">VALOR TOTAL</div>
              <div className="text-[15px] font-extrabold text-[#071D41] mt-1 truncate">
                {formatCurrency(totalConciliado)}
              </div>
            </div>

            <div>
              <div className="text-[10px] font-bold text-[#64748B] uppercase">
                PROTOCOLO DE CARGA
              </div>
              <div
                className="text-[15px] font-extrabold text-[#1351B4] mt-1"
                style={{ fontFamily: "'JetBrains Mono', monospace" }}
              >
                {commitData.db_update?.protocolo || '2026NL000482'}
              </div>
            </div>
          </div>

          {/* Botões de Ação */}
          <div className="flex flex-wrap items-center justify-center gap-4 pt-2">
            <button
              type="button"
              onClick={() => {
                setResult(null);
                setCommitData(null);
                setStep(1);
              }}
              className="px-7 py-3.5 rounded-full bg-[#1351B4] hover:bg-[#0C326F] text-white text-sm font-bold transition-transform hover:-translate-y-0.5"
            >
              Enviar Outra Planilha
            </button>

            <a
              href={`/api/secao10/download/${commitData.download_filename}`}
              className="px-7 py-3.5 rounded-full bg-[#EDF4FF] hover:bg-blue-100 text-[#1351B4] text-sm font-bold transition-colors"
            >
              Baixar Planilha Tratada (.CSV)
            </a>
          </div>
        </div>
      )}
    </div>
  );
}
