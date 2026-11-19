import React, { useEffect, useRef, useState } from 'react';
import { Bot, Send, ShieldCheck, MessageSquare, Plus, Loader2, Trash2 } from 'lucide-react';

const EXAMPLES = [
  'Quais arquivos foram analisados e tratados na ultima sessão?',
  'Quais os valores totais de cada tabela na ultima analise?',
  'Todas planilhas já foram tratadas?',
  'Como corrigir a UG responsável negativa no arquivo 05?',
];

function DecimalAmount({ value }) {
  // Formatar o texto decimal sem converter valores grandes em Number.
  if (value == null) return <span className="text-slate-500">Não informado</span>;
  const [integer, fraction = ''] = String(value).split('.');
  return <span>R$ {integer.replace(/\B(?=(\d{3})+(?!\d))/g, '.')},{fraction.padEnd(2, '0')}</span>;
}

function Evidence({ answer }) {
  return <>
    {answer.arquivos?.length > 0 && <ul className="mt-4 space-y-2">
      {answer.arquivos.map(file => <li key={file.tabela} className="rounded-lg bg-slate-50 border border-slate-200 px-3 py-2 text-xs">
        <div className="font-bold break-all">{file.arquivo} · {file.nome}</div>
        <div className="mt-1 text-slate-600">{file.status} · {file.registros.toLocaleString('pt-BR')} registros · {file.carregado_no_banco ? 'Carga confirmada' : 'Prévia; carga não confirmada'}</div>
        {file.pendencias?.map((error, index) => <div key={index} className="text-amber-800 mt-1">{error}</div>)}
      </li>)}
    </ul>}
    {answer.sessao && <p className="text-xs mt-3 text-slate-600">Bases pendentes: {answer.sessao.arquivos_pendentes.join(', ') || 'nenhuma'}. Simulações: {answer.sessao.simulacoes}.</p>}
    {answer.sessao?.falhas_nao_identificadas?.map((file, index) => <p key={index} className="text-xs text-amber-800 mt-2">Falha na importação: {file.nome}. O arquivo não foi identificado ou tratado.</p>)}
    {answer.totais?.map(table => <div key={table.tabela} className="mt-4 rounded-xl border border-slate-200 overflow-hidden">
      <div className="bg-slate-50 px-3 py-2 text-xs font-bold break-all">{table.arquivo} · {table.tabela}</div>
      {table.por_ano.length === 0 && <p className="p-3 text-xs">Sem registros para o ano solicitado.</p>}
      {table.por_ano.map(group => <div key={group.ano} className="p-3 border-t border-slate-100">
        <div className="text-xs font-bold mb-2">{group.ano} · {group.registros.toLocaleString('pt-BR')} registros</div>
        <dl className="space-y-1.5">
          {Object.entries(group.valores).map(([column, value]) => <div key={column} className="flex flex-wrap justify-between gap-x-4 gap-y-1 text-xs">
            <dt className="break-all text-slate-600">{column}</dt>
            <dd className="font-semibold tabular-nums"><DecimalAmount value={value} />{group.ausentes[column] > 0 && <span className="font-normal text-slate-500"> · {group.ausentes[column]} ausentes</span>}</dd>
          </div>)}
        </dl>
      </div>)}
    </div>)}
    {answer.fonte && <p className="text-[11px] text-slate-500 mt-4">Fonte: {answer.fonte}{answer.pagina_manual ? ` · Manual, p. ${answer.pagina_manual}` : ''}</p>}
  </>;
}

export default function AssistenteIAView({ session, revision, onNewSession, sessionBusy }) {
  const [status, setStatus] = useState(null);
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const controller = useRef(null);
  const conversation = useRef(null);
  const requestId = useRef(0);

  useEffect(() => {
    const cancel = new AbortController();
    fetch('/api/ai/status', { signal: cancel.signal, cache: 'no-store' })
      .then(r => r.ok ? r.json() : Promise.reject(new Error('Falha ao verificar a IA local.')))
      .then(setStatus).catch(e => { if (e.name !== 'AbortError') setStatus(null); });
    return () => cancel.abort();
  }, [revision, busy]);

  useEffect(() => {
    requestId.current += 1;
    controller.current?.abort();
    setMessages([]); setBusy(false); setError(''); setInput('');
    return () => controller.current?.abort();
  }, [session?.id]);

  useEffect(() => { conversation.current?.scrollTo({ top: conversation.current.scrollHeight, behavior: 'smooth' }); }, [messages, busy]);

  async function ask(question = input) {
    if (!question.trim() || busy || !session?.id) return;
    const id = ++requestId.current;
    setInput(''); setError(''); setBusy(true);
    setMessages(previous => [...previous.slice(-28), { role: 'user', text: question.trim() }]);
    controller.current = new AbortController();
    try {
      const response = await fetch('/api/ai/ask', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pergunta: question.trim(), sessao_id: session.id }),
        signal: controller.current.signal,
      });
      const data = await response.json();
      if (!response.ok) throw new Error('Não foi possível consultar esta sessão. Tente novamente.');
      if (requestId.current === id) setMessages(previous => [...previous, { role: 'assistant', answer: data }]);
    } catch (e) {
      if (e.name !== 'AbortError' && requestId.current === id) setError(e.message);
    } finally {
      if (requestId.current === id) setBusy(false);
    }
  }

  const modelReady = ['carregado', 'pronto_para_carregar'].includes(status?.classificador);
  return <section aria-labelledby="assistant-heading" className="grid gap-6 lg:grid-cols-[280px_minmax(0,1fr)]">
    <aside className="space-y-4">
      <div className="bg-white rounded-2xl border border-slate-200 p-5">
        <div className="flex items-center gap-2 text-[#1351B4]"><ShieldCheck size={20}/><h2 className="font-bold text-sm">Assistente local</h2></div>
        <p className="text-xs text-slate-600 leading-relaxed mt-3">Perguntas e respostas são processadas neste computador. A conversa não é salva pelo portal.</p>
        <p className={`text-xs font-semibold mt-3 ${modelReady ? 'text-green-700' : 'text-amber-800'}`}>{modelReady ? 'Classificador próprio disponível' : 'Classificador não disponível'}</p>
        <p className="text-xs text-slate-500 mt-1">Consultas de sessão funcionam sem o classificador.</p>
      </div>
      <div className="bg-white rounded-2xl border border-slate-200 p-5">
        <h3 className="text-sm font-bold">Sessão de análise</h3>
        <p className="text-xs text-slate-500 mt-2 break-all">{session?.id || 'Abrindo sessão…'}</p>
        <p className="text-sm font-semibold mt-3">{session?.arquivos?.filter(f => f.status === 'SUCESSO').length || 0} de 5 bases tratadas</p>
        <p className="text-xs text-slate-500 mt-1">SIORG e energia estão fora deste escopo.</p>
        <button onClick={onNewSession} disabled={busy || sessionBusy} className="mt-4 w-full flex items-center justify-center gap-2 rounded-xl border border-blue-200 px-3 py-2 text-xs font-bold text-[#1351B4] disabled:opacity-50"><Plus size={16}/>Nova sessão</button>
        <p className="text-[11px] text-slate-500 mt-2">Mantém as análises anteriores no histórico local.</p>
      </div>
    </aside>
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
      <header className="p-5 border-b border-slate-100 flex flex-wrap gap-3 items-center justify-between">
        <div className="flex gap-3 items-center"><div className="p-2.5 rounded-xl bg-blue-50 text-[#1351B4]"><Bot size={23}/></div><div><h1 id="assistant-heading" className="font-extrabold">IA SCM</h1><p className="text-xs text-slate-500">Arquivos, totais e regras de tratamento</p></div></div>
        <button onClick={() => { setMessages([]); setError(''); }} disabled={busy} className="flex items-center gap-1.5 text-xs text-slate-500 disabled:opacity-50"><Trash2 size={14}/>Limpar conversa</button>
      </header>
      <div ref={conversation} className="h-[470px] overflow-y-auto p-5 space-y-5" role="log" aria-live="polite" aria-label="Conversa com o assistente">
        {messages.length === 0 && <div className="py-6 max-w-xl mx-auto">
          <MessageSquare className="text-blue-300 mb-4" size={32}/>
          <h2 className="text-lg font-bold">O que você quer conferir?</h2>
          <p className="text-sm text-slate-500 mt-2 mb-5">Consulte a sessão atual ou tire dúvidas sobre as regras. A IA não executa cargas nem altera o banco.</p>
          <div className="grid gap-2">{EXAMPLES.map(question => <button key={question} onClick={() => ask(question)} disabled={busy || !session?.id} className="rounded-xl border border-slate-200 text-left px-4 py-3 text-xs hover:bg-blue-50 hover:border-blue-200 disabled:opacity-50">{question}</button>)}</div>
        </div>}
        {messages.map((message, index) => <article key={index} className={message.role === 'user' ? 'ml-auto max-w-[90%] rounded-2xl rounded-tr-sm bg-[#1351B4] text-white px-4 py-3 text-sm whitespace-pre-wrap break-words' : 'max-w-[96%] rounded-2xl rounded-tl-sm border border-slate-200 p-4 text-sm'}>
          {message.role === 'user' ? message.text : <><p className="whitespace-pre-wrap break-words leading-relaxed">{message.answer.resposta}</p><Evidence answer={message.answer}/></>}
        </article>)}
        {busy && <div role="status" className="text-xs text-slate-500 flex items-center gap-2"><Loader2 size={16} className="animate-spin"/>Consultando localmente…</div>}
      </div>
      <form onSubmit={e => { e.preventDefault(); ask(); }} className="border-t border-slate-100 p-4">
        {error && <p role="alert" className="text-xs text-red-700 mb-3">{error}</p>}
        <div className="flex gap-2 items-end"><textarea aria-label="Sua pergunta" value={input} onChange={e => setInput(e.target.value)} maxLength={2000} rows={2} placeholder="Pergunte sobre os arquivos ou o tratamento…" className="resize-none flex-1 min-w-0 rounded-xl border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"/><button aria-label="Enviar pergunta" type="submit" disabled={busy || !input.trim() || !session?.id} className="rounded-xl p-3 bg-[#1351B4] text-white disabled:opacity-40"><Send size={19}/></button></div>
        <p className="text-[10px] text-slate-500 mt-2">Modelo experimental. Confira as fontes e pendências antes de decidir sobre uma carga.</p>
      </form>
    </div>
  </section>;
}
