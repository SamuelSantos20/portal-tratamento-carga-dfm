import React, { useEffect, useRef, useState } from 'react';
import Secao10MotorView from './components/Secao10MotorView';
import ControleGovernancaView from './components/ControleGovernancaView';
import AssistenteIAView from './components/AssistenteIAView';

export default function App() {
  const [activeTab, setActiveTab] = useState('carga');
  const [statusData, setStatusData] = useState(null);
  const [session, setSession] = useState(null);
  const [revision, setRevision] = useState(0);
  const [sessionBusy, setSessionBusy] = useState(false);
  const [sessionError, setSessionError] = useState('');
  const [authorized, setAuthorized] = useState(false);
  const authorizationPromise = useRef(null);
  const currentSessionId = useRef(null);

  async function refreshAnalysis() {
    const expectedSession = currentSessionId.current;
    try {
      const response = await fetch(`/api/ai/session${expectedSession ? `?sessao_id=${expectedSession}` : ''}`, { cache: 'no-store' });
      if (!response.ok) throw new Error('Falha ao abrir a sessão de análise. Recarregue a página.');
      const data = await response.json();
      if (currentSessionId.current && data.id !== currentSessionId.current) return;
      currentSessionId.current = data.id;
      setSession(data);
      setRevision(value => value + 1);
      setSessionError('');
    } catch (error) { if (expectedSession === currentSessionId.current) setSessionError(error.message); }
  }

  async function newSession() {
    setSessionBusy(true);
    try {
      const response = await fetch('/api/ai/sessions', { method: 'POST' });
      if (!response.ok) throw new Error('Não foi possível criar a sessão.');
      const data = await response.json();
      currentSessionId.current = data.id;
      setSession(data);
      setRevision(value => value + 1);
      setSessionError('');
    } catch (error) { setSessionError(error.message); }
    finally { setSessionBusy(false); }
  }

  async function refreshMetadata() {
    try {
      const stRes = await fetch('/api/status');
      const stJson = await stRes.json();
      setStatusData(stJson);
    } catch (err) {
      console.error('Erro ao carregar status do sistema:', err);
    }
  }

  useEffect(() => {
    let active = true;
    async function authorize() {
      const fragment = new URLSearchParams(window.location.hash.slice(1));
      const key = fragment.get('acesso');
      if (key) {
        window.history.replaceState(null, '', window.location.pathname + window.location.search);
        const response = await fetch('/api/auth/session', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ chave: key }) });
        if (!response.ok) throw new Error('Acesso não autorizado. Abra o portal pelo inicializador local.');
      } else {
        const response = await fetch('/api/ai/status', { cache: 'no-store' });
        if (!response.ok) throw new Error('Abra o portal pelo inicializador local para autorizar esta sessão.');
      }
    }
    function beginAuthorization() {
      if (!authorizationPromise.current || new URLSearchParams(window.location.hash.slice(1)).has('acesso')) authorizationPromise.current = authorize();
      authorizationPromise.current.then(() => {
        if (active) { setAuthorized(true); setSessionError(''); refreshMetadata(); refreshAnalysis(); }
      }).catch(error => { if (active) setSessionError(error.message); });
    }
    beginAuthorization();
    window.addEventListener('hashchange', beginAuthorization);
    return () => { active = false; window.removeEventListener('hashchange', beginAuthorization); };
  }, []);

  const totalCarregados = Object.values(statusData?.table_counts || {}).reduce(
    (acc, val) => acc + Number(val || 0),
    0
  );

  const pgEnabled = statusData?.pg_config?.enabled;

  return (
    <div className="min-h-screen flex flex-col bg-[#F3F6FB] text-[#071D41]">
      {/* TOP BAR BRANCA — ESTILO PORTAL */}
      <header className="bg-white border-b border-slate-200/80 sticky top-0 z-30">
        <div className="max-w-[1340px] mx-auto px-6 min-h-[64px] py-3 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="bg-[#EDF4FF] px-3 py-1.5 rounded-lg flex items-center gap-2 font-extrabold text-[15px] text-[#1351B4]">
              <svg width="28" height="12" viewBox="0 0 28 12" fill="none">
                <circle cx="5" cy="6" r="4.5" fill="#1351B4" />
                <circle cx="14" cy="6" r="4.5" fill="#FFCD07" />
                <circle cx="23" cy="6" r="4.5" fill="#168821" />
              </svg>
              PORTAL
            </div>

            <div className="hidden sm:block w-[1.5px] h-6 bg-[#EDF4FF]" />

            <div>
              <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                PLATAFORMA DE INTEGRAÇÃO E GOVERNANÇA DE DADOS
              </div>
              <div className="text-[13px] font-bold text-[#071D41]">
                Sistema de Tratamento e Carga de Planilhas
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            <span className="hidden md:inline-flex items-center gap-1.5 bg-[#E8F8EC] text-[#168821] text-[11px] font-bold px-3.5 py-1.5 rounded-full">
              ● {!authorized ? 'Acesso local restrito' : !statusData ? 'Verificando banco local' : pgEnabled ? `PostgreSQL (${statusData?.pg_config?.database}) + SQLite` : 'SQLite local'}
            </span>

            <button
              onClick={() => setActiveTab('carga')}
              className={`px-4 py-1.5 rounded-full text-[11px] font-bold transition-all ${
                activeTab === 'carga'
                  ? 'bg-[#1351B4] text-white shadow-sm'
                  : 'bg-[#EDF4FF] text-[#1351B4] hover:bg-blue-100'
              }`}
            >
              PAINEL DE CARGA
            </button>

            <button
              onClick={() => setActiveTab('banco')}
              className={`px-4 py-1.5 rounded-full text-[11px] font-bold transition-all ${
                activeTab === 'banco'
                  ? 'bg-[#1351B4] text-white shadow-sm'
                  : 'bg-[#EDF4FF] text-[#1351B4] hover:bg-blue-100'
              }`}
            >
              BANCO DE DADOS (5 TABELAS)
            </button>
            <button onClick={() => setActiveTab('ia')} className={`px-4 py-1.5 rounded-full text-[11px] font-bold transition-all ${activeTab === 'ia' ? 'bg-[#1351B4] text-white shadow-sm' : 'bg-[#EDF4FF] text-[#1351B4] hover:bg-blue-100'}`}>ASSISTENTE IA</button>
          </div>
        </div>
      </header>

      {/* HERO BANNER COM ONDAS GEOMÉTRICAS */}
      <section
        className="relative h-[148px] overflow-hidden flex items-center"
        style={{
          background: 'linear-gradient(100deg, #071D41 0%, #0C326F 55%, #1351B4 100%)',
        }}
      >
        <svg
          className="absolute inset-0 w-full h-full object-cover pointer-events-none"
          viewBox="0 0 1440 148"
          fill="none"
          preserveAspectRatio="none"
        >
          <path d="M820 148 C940 30, 1120 10, 1440 80 L1440 148 Z" fill="#1351B4" fillOpacity="0.55" />
          <path d="M960 0 C1080 120, 1240 130, 1440 30 L1440 0 Z" fill="#38BDF8" fillOpacity="0.18" />
          <circle cx="1280" cy="74" r="110" stroke="#FFCD07" strokeWidth="2" strokeOpacity="0.35" />
          <circle
            cx="1280"
            cy="74"
            r="70"
            stroke="#FFFFFF"
            strokeWidth="1.5"
            strokeOpacity="0.2"
            strokeDasharray="4 4"
          />
          <path d="M1050 148 Q 1180 40 1380 148" stroke="#FFCD07" strokeWidth="3" strokeOpacity="0.65" fill="none" />
          <path d="M1140 148 Q 1250 70 1420 148" stroke="#168821" strokeWidth="4" strokeOpacity="0.7" fill="none" />
          <rect x="0" y="144" width="900" height="4" fill="#1351B4" />
          <rect x="900" y="144" width="340" height="4" fill="#FFCD07" />
          <rect x="1240" y="144" width="200" height="4" fill="#168821" />
        </svg>

        <div className="relative z-10 max-w-[1340px] w-full mx-auto px-6">
          <span className="inline-block bg-[#FFCD07] text-[#071D41] text-[10px] font-extrabold px-2.5 py-0.5 rounded-md mb-1.5">
            PROCESSAMENTO E CONCILIAÇÃO AUTOMÁTICA
          </span>
          <h1 className="text-white text-2xl sm:text-[26px] font-extrabold tracking-tight">
            Central de Tratamento e Envio de Planilhas
          </h1>
          <p className="text-white/90 text-[13px] font-medium mt-0.5">
            Higienização automática de dados contábeis e sincronização direta com o banco de dados (Tabelas 01 a 05)
          </p>
        </div>
      </section>

      {/* CONTEÚDO PRINCIPAL */}
      <main className="flex-1 max-w-[1340px] w-full mx-auto px-6 py-7">
        {sessionError && <p role="alert" className="mb-4 rounded-xl bg-red-50 border border-red-200 text-red-700 p-3 text-sm">{sessionError}</p>}
        {authorized && <><div className={activeTab === 'carga' ? '' : 'hidden'}>
          <Secao10MotorView
            key={session?.id || 'loading'}
            statusData={statusData}
            onDatabaseUpdated={refreshMetadata}
            onOpenDatabaseTab={() => setActiveTab('banco')}
            sessionId={session?.id}
            onAnalysisUpdated={refreshAnalysis}
          />
        </div>
        {activeTab === 'banco' && (
          <ControleGovernancaView
            statusData={statusData}
            onDatabaseUpdated={refreshMetadata}
          />
        )}
        <div className={activeTab === 'ia' ? '' : 'hidden'}><AssistenteIAView session={session} revision={revision} onNewSession={newSession} sessionBusy={sessionBusy}/></div></>}
      </main>

      {/* RODAPÉ DISCRETO */}
      <footer className="bg-white border-t border-slate-200 text-slate-500 text-xs py-3 px-6">
        <div className="max-w-[1340px] mx-auto flex items-center justify-between">
          <span className="font-semibold text-[#071D41]">
            Portal de Tratamento e Carga de Planilhas • Schema dfm
          </span>
          <span className="text-[#168821] font-bold">
            ● {totalCarregados.toLocaleString('pt-BR')} registros sincronizados nas 5 bases
          </span>
        </div>
      </footer>
    </div>
  );
}
