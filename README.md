# Portal — Sistema de Tratamento e Carga de Planilhas (`schema dfm`)

Sistema Web (FastAPI + React + PostgreSQL / SQLite) para recepção, reconhecimento estrutural automático, higienização de dados contábeis e carga transacional nas 5 tabelas do banco de dados (`schema dfm`).

## Tabelas Alvo Suportadas (`schema dfm`)

| Código | Arquivo / Planilha | Tabela no Banco (`PostgreSQL / SQLite`) |
| :---: | :--- | :--- |
| **01** | Provisões Orçamentárias Recebidas | `dfm.tb_provisoes` |
| **02** | Saldos de Material em Estoque e Permanente | `dfm.tb_saldo_material_mb` |
| **03** | Custos Liquidados por Macroatividade e Atividade | `dfm.tb_custos_atividade` |
| **04** | Custos Liquidados por UG Responsável e NE | `dfm.tb_custos_ugr_na_liq` |
| **05** | Custos por Atividade Mensal (Série Temporal) | `dfm.tb_custos_atividade_mes` |

---

## Fluxo em 3 Etapas

1. **1. Importar Planilha:** Upload (drag-and-drop ou seleção) de arquivos `.CSV`, `.XLSX` ou `.XLS` com reconhecimento automático da tabela de destino (`01` a `05`) ou seleção manual.
2. **2. Tratamento Automático:** Expurgo de linhas de totalização, desmembramento de pares de Unidades Gestoras (`Código - Nome`), tratamento de sentinelas (`-8`, `'-8`, `-8.0`), conversão monetária para padrão SQL `numeric(18,4)` e conciliação financeira (`Δ = R$ 0,00`).
3. **3. Enviado ao Banco:** Substituição transacional na tabela alvo (SQLite local + sincronização direta com PostgreSQL `schema dfm`), geração de protocolo de carga e opção de download do `.CSV` tratado.

---

## Estrutura do Repositório

- `backend/`
  - `main.py`: API FastAPI com endpoints de processamento (`/api/secao10/process`), confirmação de carga (`/api/secao10/commit/{table_name}`), simulação, configuração PostgreSQL (`/api/db-config`) e explorador de tabelas.
  - `engine_secao10.py`: Motor de reconhecimento estrutural e tratamento das tabelas `01` a `05`.
  - `database.py`: Conector híbrido PostgreSQL (`schema dfm`) + banco local SQLite.
  - `schema_dfm.sql`: Script DDL oficial do PostgreSQL com todas as tabelas, colunas geradas e índices.
- `frontend/`: Aplicação React + Vite + Tailwind CSS seguindo o design do protótipo aprovado no Figma.
- `design_export/`: Protótipo interativo HTML/CSS, imagens PNG exportadas, vetores SVG e tokens de design.

---

## Como Executar Localmente

### 1. Backend (FastAPI)
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000
```

### 2. Frontend (React + Vite)
```bash
cd frontend
npm install
npm run dev
```

Ou clique duas vezes em `iniciar_sistema.bat` no Windows.
