-- =============================================================================
-- SCRIPT DDL OFICIAL — POSTGRESQL (SCHEMA dfm)
-- Tabelas 01 a 05 de Tratamento e Carga de Planilhas
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS dfm;

-- -----------------------------------------------------------------------------
-- ARQUIVO 01: Table dfm.tb_provisoes
-- -----------------------------------------------------------------------------
-- DROP TABLE IF EXISTS dfm.tb_provisoes;

CREATE TABLE IF NOT EXISTS dfm.tb_provisoes
(
    id bigint NOT NULL GENERATED ALWAYS AS IDENTITY ( INCREMENT 1 START 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1 ),
    ano_emissao integer NOT NULL,
    ug_beneficiada_acc text COLLATE pg_catalog."default" NOT NULL,
    ug_beneficiada_nome text COLLATE pg_catalog."default",
    ug_emitente text COLLATE pg_catalog."default",
    ug_emitente_nome text COLLATE pg_catalog."default",
    ug_executora text COLLATE pg_catalog."default",
    ug_executora_nome text COLLATE pg_catalog."default",
    ug_responsavel text COLLATE pg_catalog."default",
    ug_responsavel_nome text COLLATE pg_catalog."default",
    acao_governo text COLLATE pg_catalog."default",
    acao_governo_nome text COLLATE pg_catalog."default",
    provisao_rcb numeric DEFAULT 0,
    destaque_rcb numeric DEFAULT 0,
    rpnp_insc numeric DEFAULT 0,
    provisao_liquidada numeric DEFAULT 0,
    destaque_liquidado numeric DEFAULT 0,
    rpnp_liq numeric DEFAULT 0,
    provisao_a_liquidar numeric DEFAULT 0,
    destaque_a_liquidar numeric DEFAULT 0,
    rpnp_a_liq numeric DEFAULT 0,
    criado_em timestamp with time zone NOT NULL DEFAULT now(),
    pi text COLLATE pg_catalog."default",
    pi_nome text COLLATE pg_catalog."default",
    CONSTRAINT tb_provisoes_pkey PRIMARY KEY (id)
)
TABLESPACE pg_default;

COMMENT ON TABLE dfm.tb_provisoes
    IS 'Provisoes orcamentarias recebidas, liquidadas e a liquidar por UG e acao de governo.';

CREATE INDEX IF NOT EXISTS tb_provisoes_filtros_idx
    ON dfm.tb_provisoes USING btree
    (ano_emissao ASC NULLS LAST, ug_beneficiada_acc COLLATE pg_catalog."default" ASC NULLS LAST, acao_governo COLLATE pg_catalog."default" ASC NULLS LAST);

CREATE INDEX IF NOT EXISTS tb_provisoes_ug_responsavel_idx
    ON dfm.tb_provisoes USING btree
    (ano_emissao ASC NULLS LAST, ug_responsavel COLLATE pg_catalog."default" ASC NULLS LAST);


-- -----------------------------------------------------------------------------
-- ARQUIVO 02: Table dfm.tb_saldo_material_mb
-- -----------------------------------------------------------------------------
-- DROP TABLE IF EXISTS dfm.tb_saldo_material_mb;

CREATE TABLE IF NOT EXISTS dfm.tb_saldo_material_mb
(
    id bigint NOT NULL GENERATED ALWAYS AS IDENTITY ( INCREMENT 1 START 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1 ),
    ano integer NOT NULL,
    ug_executora text COLLATE pg_catalog."default",
    ug_executora_nome text COLLATE pg_catalog."default",
    ug_beneficiada_acc text COLLATE pg_catalog."default" NOT NULL,
    ug_beneficiada_nome text COLLATE pg_catalog."default",
    saldo_material_estoque numeric(18,4) DEFAULT 0,
    saldo_material_permanente numeric(18,4) DEFAULT 0,
    criado_em timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT tb_saldo_material_mb_pkey PRIMARY KEY (id)
)
TABLESPACE pg_default;

COMMENT ON TABLE dfm.tb_saldo_material_mb
    IS 'Saldos de material em estoque e material permanente por UG e ano.';

CREATE INDEX IF NOT EXISTS tb_saldo_material_mb_filtros_idx
    ON dfm.tb_saldo_material_mb USING btree
    (ano ASC NULLS LAST, ug_beneficiada_acc COLLATE pg_catalog."default" ASC NULLS LAST);


-- -----------------------------------------------------------------------------
-- ARQUIVO 03: Table dfm.tb_custos_atividade
-- -----------------------------------------------------------------------------
-- DROP TABLE IF EXISTS dfm.tb_custos_atividade;

CREATE TABLE IF NOT EXISTS dfm.tb_custos_atividade
(
    id bigint NOT NULL GENERATED ALWAYS AS IDENTITY ( INCREMENT 1 START 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1 ),
    ano_emissao integer NOT NULL,
    ug_emitente text COLLATE pg_catalog."default",
    ug_emitente_nome text COLLATE pg_catalog."default",
    ug_responsavel text COLLATE pg_catalog."default",
    ug_responsavel_nome text COLLATE pg_catalog."default",
    macroatividade text COLLATE pg_catalog."default",
    macroatividades_mb text COLLATE pg_catalog."default",
    centro_custos text COLLATE pg_catalog."default",
    atividade_geral text COLLATE pg_catalog."default",
    valor_dh numeric(18,4) NOT NULL DEFAULT 0,
    criado_em timestamp with time zone NOT NULL DEFAULT now(),
    ug_beneficiada_acc text COLLATE pg_catalog."default",
    ug_beneficiada_nome text COLLATE pg_catalog."default",
    acao_governo text COLLATE pg_catalog."default",
    acao_governo_nome text COLLATE pg_catalog."default",
    natureza_despesa_detalhada text COLLATE pg_catalog."default",
    natureza_despesa_detalhada_nome text COLLATE pg_catalog."default",
    atividades_geral text COLLATE pg_catalog."default" GENERATED ALWAYS AS (atividade_geral) STORED,
    detacusto_dh_rs numeric(18,4) GENERATED ALWAYS AS (valor_dh) STORED,
    CONSTRAINT tb_custos_atividade_pkey PRIMARY KEY (id)
)
TABLESPACE pg_default;

COMMENT ON TABLE dfm.tb_custos_atividade
    IS 'Custos liquidados por macroatividade e atividade.';

CREATE INDEX IF NOT EXISTS tb_custos_atividade_acao_natureza_idx
    ON dfm.tb_custos_atividade USING btree
    (acao_governo COLLATE pg_catalog."default" ASC NULLS LAST, natureza_despesa_detalhada COLLATE pg_catalog."default" ASC NULLS LAST);

CREATE INDEX IF NOT EXISTS tb_custos_atividade_filtros_idx
    ON dfm.tb_custos_atividade USING btree
    (ano_emissao ASC NULLS LAST, ug_responsavel COLLATE pg_catalog."default" ASC NULLS LAST, macroatividade COLLATE pg_catalog."default" ASC NULLS LAST, centro_custos COLLATE pg_catalog."default" ASC NULLS LAST);


-- -----------------------------------------------------------------------------
-- ARQUIVO 04: Table dfm.tb_custos_ugr_na_liq
-- -----------------------------------------------------------------------------
-- DROP TABLE IF EXISTS dfm.tb_custos_ugr_na_liq;

CREATE TABLE IF NOT EXISTS dfm.tb_custos_ugr_na_liq
(
    id bigint NOT NULL GENERATED ALWAYS AS IDENTITY ( INCREMENT 1 START 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1 ),
    ano_emissao integer NOT NULL,
    ug_emitente text COLLATE pg_catalog."default",
    ug_emitente_nome text COLLATE pg_catalog."default",
    ug_responsavel text COLLATE pg_catalog."default",
    ug_responsavel_nome text COLLATE pg_catalog."default",
    detacusto_dh_rs numeric(18,4) NOT NULL DEFAULT 0,
    criado_em timestamp with time zone NOT NULL DEFAULT now(),
    ug_beneficiada_acc text COLLATE pg_catalog."default",
    ug_beneficiada_nome text COLLATE pg_catalog."default",
    ne text COLLATE pg_catalog."default",
    CONSTRAINT tb_custos_ugr_na_liq_pkey PRIMARY KEY (id)
)
TABLESPACE pg_default;

COMMENT ON TABLE dfm.tb_custos_ugr_na_liq
    IS 'Custos liquidados por UG, permitindo analise de quanto foi liquidado por Unidade Gestora.';

CREATE INDEX IF NOT EXISTS tb_custos_ugr_na_liq_beneficiada_ne_idx
    ON dfm.tb_custos_ugr_na_liq USING btree
    (ano_emissao ASC NULLS LAST, ug_beneficiada_acc COLLATE pg_catalog."default" ASC NULLS LAST, ne COLLATE pg_catalog."default" ASC NULLS LAST);

CREATE INDEX IF NOT EXISTS tb_custos_ugr_na_liq_filtros_idx
    ON dfm.tb_custos_ugr_na_liq USING btree
    (ano_emissao ASC NULLS LAST, ug_responsavel COLLATE pg_catalog."default" ASC NULLS LAST);


-- -----------------------------------------------------------------------------
-- ARQUIVO 05: Table dfm.tb_custos_atividade_mes
-- -----------------------------------------------------------------------------
-- DROP TABLE IF EXISTS dfm.tb_custos_atividade_mes;

CREATE TABLE IF NOT EXISTS dfm.tb_custos_atividade_mes
(
    id bigserial NOT NULL,
    ano_emissao integer NOT NULL,
    ano_referencia_acc integer,
    mes_referencia_acc text COLLATE pg_catalog."default",
    mes_referencia_numero integer,
    mes_referencia_ordem integer,
    mes_referencia_data date,
    ug_responsavel text COLLATE pg_catalog."default",
    ug_responsavel_nome text COLLATE pg_catalog."default",
    ug_beneficiada_acc text COLLATE pg_catalog."default",
    ug_beneficiada_nome text COLLATE pg_catalog."default",
    ug_emitente text COLLATE pg_catalog."default",
    ug_emitente_nome text COLLATE pg_catalog."default",
    acao_governo text COLLATE pg_catalog."default",
    acao_governo_nome text COLLATE pg_catalog."default",
    macroatividades_mb text COLLATE pg_catalog."default",
    atividades_geral text COLLATE pg_catalog."default",
    centro_custos text COLLATE pg_catalog."default",
    natureza_despesa_detalhada text COLLATE pg_catalog."default",
    natureza_despesa_detalhada_nome text COLLATE pg_catalog."default",
    detacusto_dh_rs numeric(18,4),
    CONSTRAINT tb_custos_atividade_mes_pkey PRIMARY KEY (id)
)
TABLESPACE pg_default;

CREATE INDEX IF NOT EXISTS idx_tb_custos_atividade_mes_ano
    ON dfm.tb_custos_atividade_mes USING btree
    (ano_emissao ASC NULLS LAST);

CREATE INDEX IF NOT EXISTS idx_tb_custos_atividade_mes_beneficiada
    ON dfm.tb_custos_atividade_mes USING btree
    (ug_beneficiada_acc COLLATE pg_catalog."default" ASC NULLS LAST);

CREATE INDEX IF NOT EXISTS idx_tb_custos_atividade_mes_emitente
    ON dfm.tb_custos_atividade_mes USING btree
    (ug_emitente COLLATE pg_catalog."default" ASC NULLS LAST);

CREATE INDEX IF NOT EXISTS idx_tb_custos_atividade_mes_mes
    ON dfm.tb_custos_atividade_mes USING btree
    (mes_referencia_ordem ASC NULLS LAST);

CREATE INDEX IF NOT EXISTS idx_tb_custos_atividade_mes_responsavel
    ON dfm.tb_custos_atividade_mes USING btree
    (ug_responsavel COLLATE pg_catalog."default" ASC NULLS LAST);


-- -----------------------------------------------------------------------------
-- Tabela de Auditoria e Controle de Carga: dfm.controle_atualizacao
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dfm.controle_atualizacao (
    id BIGSERIAL PRIMARY KEY,
    nome_tabela VARCHAR(100) NOT NULL UNIQUE,
    arquivo_origem VARCHAR(255),
    data_hora_inicio TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    data_hora_fim TIMESTAMP WITH TIME ZONE,
    status VARCHAR(30) NOT NULL,
    total_linhas_brutas INTEGER DEFAULT 0,
    linhas_totalizacao_removidas INTEGER DEFAULT 0,
    total_linhas_carregadas INTEGER DEFAULT 0,
    sentinelas_substituidas INTEGER DEFAULT 0,
    sentinelas_restantes INTEGER DEFAULT 0,
    soma_financeira_original NUMERIC(18,4) DEFAULT 0,
    soma_financeira_carregada NUMERIC(18,4) DEFAULT 0,
    protocolo_carga VARCHAR(50),
    mensagem_detalhe TEXT
);
