# Registro de Alterações e Evoluções do Repositório GPT (`ChatGPT/SCM-Marinha`)

**Data do levantamento:** 16/11/2026  
**Origem analisada:** `c:\Users\samue\OneDrive\Documentos\ChatGPT\SCM-Marinha` (branch `codex/sql-period-filters` + alterações locais não commitadas) e worktree `c:\Users\samue\OneDrive\Documentos\ChatGPT\SCM-MARINHA 2\gitlab_atualizacao` (branch `codex/atualizar-schema-dfm-20261030` / `main`).  
**Objetivo:** Consolidar tudo o que foi desenvolvido no ambiente GPT/Codex (PostgreSQL `DFM_70` / Metabase) e registrar o mapeamento de aderência e pendências em relação a este projeto local (`SCM MARINHA` — FastAPI + SQLite + React).

---

## 1. Linha do Tempo Consolidada das Alterações no GPT

### A. Branch `codex/atualizar-schema-dfm-20261030` (`main` no GitHub/GitLab)

1. **Conciliação do Schema `dfm` com os CSVs e preservação de PI (`5babfdc` — 30/10/2026)**
   - **Arquivos principais:** `sql/migrations/20261030_sincronizar_dfm.sql`, `sql/schemas/README.md`, `sql/schemas/*.sql`, `sql/metabase/custos_atividade/*.sql`.
   - **Mudanças:**
     - `dfm.tb_provisoes`: preserva as 9 medidas financeiras em `numeric`, `ug_responsavel`, nomes das UGs e os campos `pi` e `pi_nome`; campos vazios podem permanecer `NULL`.
     - `dfm.tb_custos_atividade`: os campos graváveis do CSV são `atividade_geral` e `valor_dh`; `atividades_geral` e `detacusto_dh_rs` são mantidos como colunas geradas para compatibilidade com consultas legadas.
     - `dfm.tb_custos_atividade_mes`: `ano_emissao` tornado `NOT NULL` e independente da referência mensal.
     - `dfm.controle_atualizacao`: passou a suportar o contrato `(processo, atualizado_em, status)` com índice único `controle_atualizacao_processo_uk` para `INSERT ... ON CONFLICT (processo)`, mantendo as colunas legadas de auditoria (inclusive `tabela` anulável).
     - **Consolidação de UGs sem duplicidade:** criação das views `dfm.vw_ugs_ocorrencias`, `dfm.vw_ugs` e atualização de `dfm.vw_ug_custos` (1 linha por `ug_codigo`).
     - **Custos básicos:** padronização das constantes textuais de natureza de despesa (preservando zeros à esquerda e sentinelas) nos 7 gráficos individuais e na evolução mensal.

2. **Consulta de Gastos com Energia Sem Consumo (`728f4a8` — 03/11/2026)**
   - **Arquivo:** `sql/metabase/custos_atividade/tabela_gastos_energia_consumo_nulo.sql`.
   - **Mudança:** Nova consulta sobre `dfm.tb_custo_consumo_energia` listando documentos hábeis (`ods_ug_emitente`, `ug_emitente`, `ug_emitente_nome`, `mes`, `ano`, `documento_habil`, `energia_eletrica`, `consumo_kwh`) onde `consumo_kwh IS NULL`, com filtros opcionais `{{Ano}}`, `{{Mes}}` e `{{OM}}` (via `dfm.filtrar_ugs`).

3. **Correção da View `dfm.vw_provisoes_pivot` (não commitado em `gitlab_atualizacao`)**
   - **Arquivos:** `sql/views/vw_provisoes_pivot.sql`, `sql/migrations/20261030_corrigir_view_provisoes_pivot.sql`.
   - **Mudanças:**
     - Agrega `dfm.tb_saldo_material_mb` por `(ug_beneficiada_acc, ano)` antes do `LEFT JOIN`, impedindo multiplicação das provisões.
     - Usa `ROW_NUMBER() OVER (PARTITION BY p.ug_beneficiada_acc, p.ano_emissao ORDER BY p.acao_governo, p.pi, p.pi_nome, p.id)` para exibir `saldo_material_estoque` e `saldo_material_permanente` apenas na 1ª linha de cada `(UG + Ano)`, evitando duplicação entre PIs.
     - Expande a view de 16 para **24 colunas**, acrescentando ao final: `pi`, `pi_nome`, `ug_beneficiada_nome`, `ug_responsavel_nome`, `ug_emitente`, `ug_emitente_nome`, `ug_executora`, `ug_executora_nome`.

---

### B. Branch `codex/sql-period-filters` (`ChatGPT/SCM-Marinha`)

1. **Filtros de Período e Comparativo Anual (`2fa73fd` — 02/09/2026 + alterações locais não commitadas de 03/09/2026)**
   - **Arquivos:** `sql/metabase/aspecto_comparativo_anual/01..04_*_maior_impacto_mensal_por_atividade.sql`, `comparativo_anual_custos_por_atividade.sql`, `comparacao_anual_custo_por_atividade_grafico.sql`, `README.md` e `tests/test_periodos_comparativo_anual.py`.
   - **Mudanças:**
     - Cartões 504, 536, 537 e 540 renomeados no Metabase de *"Impacto Mensal"* para *"Impacto no Período"* (coluna `valor_rs` exibida como **Valor no período (R$)** e nova coluna `periodo_analisado`, ex.: `07–08/2026 vs 07–08/2025`).
     - **Corte simétrico de meses encerrados:** exclui mês corrente e referências futuras (`t.mes_referencia_data < DATE_TRUNC('month', CURRENT_DATE)::date`) e calcula `ultimo_mes_completo` global para o `Ano` selecionado, aplicando esse mesmo limite aos dois anos (`ano` e `ano - 1`).
     - Sem `Ano`: os 4 cartões preservam o histórico filtrado (meses encerrados) sem variação; tabela e gráfico superior adotam o último ano com referência encerrada.
     - Gráfico superior (Metabase 453) migrado para `dfm.tb_custos_atividade_mes` com suporte a `Mes`, `Semestre`, `Trimestre` e `UG_Responsavel` (top 15 por soma dos dois anos).
     - **Suíte de testes:** `tests/test_periodos_comparativo_anual.py` com 14 testes unitários de contrato SQL e regras de calendário (todos passando).

2. **Pendências SIORG por OM (`c1306a5`, `f13ef1d` — 09/09/2026 + carga local de 02/11/2026)**
   - **Arquivos:** `sql/schemas/tb_siorg_corrigir.sql`, `sql/metabase/siorg_corrigir/*.sql`, `scripts/carregar_siorg_corrigir.sql`, `sql/metabase/siorg_corrigir/README.md`.
   - **Mudanças:**
     - Carga conferida em 02/11/2026 no `DFM_70` (`dfm.tb_siorg_corrigir`) a partir de `06_SIORG_Custos_DH_TRATADO.csv`: **38.384 linhas**, **26.877 DHs distintos** e **245 UGs (`ug_emitente`)**.
     - Remoção da coluna `total` em `tb_siorg_corrigir` e `detalhes_dhs.sql` (mantendo `qtde_dh_distintos`); `detacusto_dh_rs` permanece apenas no CSV original, não sendo carregado em `tb_siorg_corrigir`.
     - Registro de atualização dedicado via `registrar_atualizacao.sql` em `dfm.controle_atualizacao`.

3. **Levantamento de Demandas do Metabase (`docs/DEMANDAS_METABASE_2026-11-10.md` — 10/11/2026)**
   - Inspeção somente leitura no Metabase local (`dashboard/2-scm`) registrando 6 demandas priorizadas:
     1. **Prioridade 1:** Investigar percentuais incompatíveis no Comparativo Periódico (ex.: `818,1%` exibido onde a variação real seria `8.181,1%`; `799,8%` onde seria `79.983,5%`) e tratar `anterior = 0` ou ausente.
     2. **Prioridade 2:** Tornar o período e a cobertura visíveis no comparativo (reaproveitar `QUALIDADE DA BASE COMPARATIVA`, distinguir ausência de dados de zero).
     3. **Prioridade 3:** Mostrar data de atualização **por fonte** (Posição exibia `30/10/2026 18:44`, enquanto SIORG teve carga em `02/11/2026`).
     4. **Prioridade 4:** Revisar filtros temporais da aba *Custos com Funcionamento* (atualmente só exibe `OM` para os 7 gráficos básicos; não conectar período ao SIORG).
     5. **Prioridade 5:** Melhorar nomenclatura exibida (`MacroClick`, `MATERIAL_PIVOT`, pares *Impacto Mensal / Impacto no Período*).
     6. **Prioridade 6:** Validar fluxo SIORG por OM (esclarecer que `OM = ug_emitente`, validar contexto do link de detalhes de documentos).

4. **Outras entregas no repositório GPT**
   - `docs/REGRAS_TRATAMENTO_DADOS.md` e `docs/PREPARADOR_TABELAS.md`: regras da Seção 10 e preparador de planilhas.
   - `docs/hardening_metabase_publicacao/`: proposta e diagramas de controle de fronteira de publicação do Metabase.
   - `auditoria_portal_custos_metabase.ipynb` e `relatorio_viabilidade_metabase.artifact.json`: parecer de viabilidade de reprodução do Portal de Custos no Metabase.
   - `scripts/criar_manual_*.py` e `scripts/gerar_pdfs_metabase_docker.py`: geração do manual em DOCX/PDF.

---

## 2. Comparação com este Projeto (`SCM MARINHA` — App Local)

| Área / Recurso | Situação Atual no `SCM MARINHA` | Evolução Existente no GPT (`ChatGPT/SCM-Marinha`) | Ação Recomendada para o `SCM MARINHA` |
|---|---|---|---|
| **Schema `tb_provisoes` e `vw_provisoes_pivot`** | `backend/schema_dfm.sql` e `backend/database.py` já incluem `pi` e `pi_nome`. A `vw_provisoes_pivot` tem 16 colunas e `main.py` agrega por `acao_governo` no endpoint. | `vw_provisoes_pivot` atualizada para **24 colunas** (incluindo `pi`, `pi_nome`, `ug_emitente`, `ug_executora`, nomes) e `ROW_NUMBER()` por `(ug, ano)` ordenado por `(acao_governo, pi, pi_nome, id)` evitando duplicação de material entre PIs. | Atualizar `backend/schema_dfm.sql` se for sincronizar o DDL PostgreSQL completo; no app SQLite, avaliar exposição de `pi` na tabela pivot sem duplicar saldo de material. |
| **Controle de Atualização (`controle_atualizacao`)** | `controle_atualizacao` já exibe status por tabela (`dfm.tb_*`) na aba *Banco de Dados (dfm)* (`ControleGovernancaView.jsx`). | Contrato unificado por `processo` (`ON CONFLICT (processo)`) e demanda de exibir atualização por fonte nos próprios painéis (não apenas uma data geral). | Já atendido parcialmente na aba de governança; opcionalmente exibir a data da última carga por fonte nos cabeçalhos das abas de painel. |
| **Comparativo Anual & Corte de Períodos** | `GET /api/dashboard/custos` exibe evolução mensal simples de `tb_custos_atividade_mes` sem corte simétrico de meses encerrados nem cálculo de variação anual. | Corte simétrico (`mes_referencia_data < mês corrente`), `ultimo_mes_completo` global por ano, rótulo `periodo_analisado` e validação de variação percentual (`(atual/anterior - 1) * 100`). | Incorporar lógica de corte simétrico de meses encerrados e indicador de período analisado caso seja adicionada visão de comparativo anual ao `PainelCustosView.jsx`. |
| **SIORG (`tb_siorg_custos_dh` vs `tb_siorg_corrigir`)** | `backend/database.py` e `engine_secao10.py` usam `tb_siorg_custos_dh` (com `linha_origem` e `detacusto_dh_rs`) e exibem resumo por tipo de DH em `/api/dashboard/custos`. | `tb_siorg_corrigir` no `DFM_70` removeu `total` e não carrega `detacusto_dh_rs` (foca em `qtde_dh_distintos`, 26.877 DHs e 245 UGs). | Manter compatibilidade: `SCM MARINHA` já aceita o CSV `06_SIORG_Custos_DH_*.csv`; se necessário, adicionar visão de pendências por OM (`ug_emitente`) e centro de custos sem depender de `detacusto_dh_rs`. |
| **Energia sem Consumo (`tb_custo_consumo_energia`)** | Não existe tabela nem consulta para `tb_custo_consumo_energia` no app local. | Nova consulta `tabela_gastos_energia_consumo_nulo.sql` (commit `728f4a8` de 03/11/2026) listando DHs de energia com `consumo_kwh IS NULL`. | Avaliar inclusão da tabela/schema `tb_custo_consumo_energia` no `engine_secao10.py` e `database.py` se essa planilha passar a ser tratada no app local. |
| **Custos Básicos (7 gráficos individuais)** | `PainelCustosView.jsx` exibe macroatividades, atividades, evolução mensal, UGR e NDDs gerais. | 7 consultas dedicadas de custos básicos (água/esgoto, energia, gás, limpeza, TI, telefonia, vigilância) filtradas por NDD textual + demanda de filtro temporal. | Opcional: adicionar seção ou filtro rápido de *Custos Básicos / Utilidades Essenciais* no `PainelCustosView.jsx` usando as mesmas NDDs textuais. |
