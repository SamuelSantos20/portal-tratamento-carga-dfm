"""
Motor Inteligente de Reconhecimento Estrutural, Tratamento e Validação de Planilhas
Identifica automaticamente a tabela alvo (Arquivos 01 a 05 do schema dfm) analisando
a estrutura da planilha, os nomes das colunas e o padrão dos dados nas células.
"""

import csv
import io
import os
import re
import unicodedata
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple

try:
    import openpyxl
except ImportError:
    openpyxl = None

MESES_MAP = {
    "JAN": 1, "JANEIRO": 1, "01": 1, "1": 1,
    "FEV": 2, "FEVEREIRO": 2, "FEB": 2, "02": 2, "2": 2,
    "MAR": 3, "MARCO": 3, "MARÇO": 3, "03": 3, "3": 3,
    "ABR": 4, "ABRIL": 4, "APR": 4, "04": 4, "4": 4,
    "MAI": 5, "MAIO": 5, "MAY": 5, "05": 5, "5": 5,
    "JUN": 6, "JUNHO": 6, "06": 6, "6": 6,
    "JUL": 7, "JULHO": 7, "07": 7, "7": 7,
    "AGO": 8, "AGOSTO": 8, "AUG": 8, "08": 8, "8": 8,
    "SET": 9, "SETEMBRO": 9, "SEP": 9, "09": 9, "9": 9,
    "OUT": 10, "OUTUBRO": 10, "OCT": 10, "10": 10,
    "NOV": 11, "NOVEMBRO": 11, "11": 11,
    "DEZ": 12, "DEZEMBRO": 12, "DEC": 12, "12": 12,
}

NUMERO_PARA_SIGLA_MES = {
    1: "JAN", 2: "FEV", 3: "MAR", 4: "ABR", 5: "MAI", 6: "JUN",
    7: "JUL", 8: "AGO", 9: "SET", 10: "OUT", 11: "NOV", 12: "DEZ"
}

TABLE_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "tb_provisoes": {
        "file_code": "01",
        "short_name": "Provisões Recebidas",
        "label": "01 • dfm.tb_provisoes (Provisões Orçamentárias)",
        "columns": [
            "ano_emissao",
            "ug_beneficiada_acc", "ug_beneficiada_nome",
            "ug_emitente", "ug_emitente_nome",
            "ug_executora", "ug_executora_nome",
            "ug_responsavel", "ug_responsavel_nome",
            "acao_governo", "acao_governo_nome",
            "provisao_rcb", "destaque_rcb", "rpnp_insc",
            "provisao_liquidada", "destaque_liquidado", "rpnp_liq",
            "provisao_a_liquidar", "destaque_a_liquidar", "rpnp_a_liq",
            "pi", "pi_nome"
        ],
        "numeric_cols": [
            "provisao_rcb", "destaque_rcb", "rpnp_insc",
            "provisao_liquidada", "destaque_liquidado", "rpnp_liq",
            "provisao_a_liquidar", "destaque_a_liquidar", "rpnp_a_liq"
        ],
        "ug_pairs": [
            ("ug_beneficiada_acc", "ug_beneficiada_nome"),
            ("ug_emitente", "ug_emitente_nome"),
            ("ug_executora", "ug_executora_nome"),
            ("ug_responsavel", "ug_responsavel_nome"),
        ],
        "rule_title": "Arquivo 01 — dfm.tb_provisoes",
        "rule_summary": "Separar pares de UG em código e nome + Quando UG Beneficiada estiver negativa/ausente/inválida, substituir pelos dados da UG Executora da mesma linha e conciliar as 9 medidas financeiras."
    },
    "tb_saldo_material_mb": {
        "file_code": "02",
        "short_name": "Saldo de Material e Patrimônio",
        "label": "02 • dfm.tb_saldo_material_mb (Saldos de Material)",
        "columns": [
            "ano",
            "ug_executora", "ug_executora_nome",
            "ug_beneficiada_acc", "ug_beneficiada_nome",
            "saldo_material_estoque", "saldo_material_permanente"
        ],
        "numeric_cols": ["saldo_material_estoque", "saldo_material_permanente"],
        "ug_pairs": [
            ("ug_executora", "ug_executora_nome"),
            ("ug_beneficiada_acc", "ug_beneficiada_nome"),
        ],
        "rule_title": "Arquivo 02 — dfm.tb_saldo_material_mb",
        "rule_summary": "Dividir UG em código e nome (preenchendo ug_executora e ug_beneficiada_acc), carregar Ano Lançamento em ano e converter saldos de estoque e permanente para numeric(18,4)."
    },
    "tb_custos_atividade": {
        "file_code": "03",
        "short_name": "Custos por Atividade",
        "label": "03 • dfm.tb_custos_atividade (Custos por Macroatividade e Atividade)",
        "columns": [
            "ano_emissao",
            "ug_emitente", "ug_emitente_nome",
            "ug_responsavel", "ug_responsavel_nome",
            "macroatividade", "macroatividades_mb",
            "centro_custos", "atividade_geral",
            "valor_dh",
            "ug_beneficiada_acc", "ug_beneficiada_nome",
            "acao_governo", "acao_governo_nome",
            "natureza_despesa_detalhada", "natureza_despesa_detalhada_nome"
        ],
        "numeric_cols": ["valor_dh"],
        "ug_pairs": [
            ("ug_emitente", "ug_emitente_nome"),
            ("ug_responsavel", "ug_responsavel_nome"),
            ("ug_beneficiada_acc", "ug_beneficiada_nome"),
        ],
        "rule_title": "Arquivo 03 — dfm.tb_custos_atividade",
        "rule_summary": "Separar pares de UG + Quando UG Responsável contiver -8 ou sentinela negativa, substituir por ug_emitente e ug_emitente_nome da mesma linha. Colunas geradas (atividades_geral e detacusto_dh_rs) são calculadas pelo banco."
    },
    "tb_custos_ugr_na_liq": {
        "file_code": "04",
        "short_name": "Custos Liquidados por UGR",
        "label": "04 • dfm.tb_custos_ugr_na_liq (Custos Liquidados por UG e NE)",
        "columns": [
            "ano_emissao",
            "ug_emitente", "ug_emitente_nome",
            "ug_responsavel", "ug_responsavel_nome",
            "detacusto_dh_rs",
            "ug_beneficiada_acc", "ug_beneficiada_nome",
            "ne"
        ],
        "numeric_cols": ["detacusto_dh_rs"],
        "ug_pairs": [
            ("ug_emitente", "ug_emitente_nome"),
            ("ug_responsavel", "ug_responsavel_nome"),
            ("ug_beneficiada_acc", "ug_beneficiada_nome"),
        ],
        "rule_title": "Arquivo 04 — dfm.tb_custos_ugr_na_liq",
        "rule_summary": "Separar pares de UG + Quando UG Responsável contiver -8 ou sentinela negativa, substituir por ug_emitente e ug_emitente_nome da mesma linha e validar Nota de Empenho (NE)."
    },
    "tb_custos_atividade_mes": {
        "file_code": "05",
        "short_name": "Custos Mensais por Atividade",
        "label": "05 • dfm.tb_custos_atividade_mes (Custos por Atividade Mensal)",
        "columns": [
            "ano_emissao",
            "ano_referencia_acc", "mes_referencia_acc",
            "mes_referencia_numero", "mes_referencia_ordem", "mes_referencia_data",
            "ug_responsavel", "ug_responsavel_nome",
            "ug_beneficiada_acc", "ug_beneficiada_nome",
            "ug_emitente", "ug_emitente_nome",
            "acao_governo", "acao_governo_nome",
            "macroatividades_mb", "atividades_geral", "centro_custos",
            "natureza_despesa_detalhada", "natureza_despesa_detalhada_nome",
            "detacusto_dh_rs"
        ],
        "numeric_cols": ["detacusto_dh_rs"],
        "ug_pairs": [
            ("ug_responsavel", "ug_responsavel_nome"),
            ("ug_beneficiada_acc", "ug_beneficiada_nome"),
            ("ug_emitente", "ug_emitente_nome"),
        ],
        "rule_title": "Arquivo 05 — dfm.tb_custos_atividade_mes",
        "rule_summary": "Separar pares de UG + Quando UG Responsável for negativa/sentinela, substituir pelos dados da UG Beneficiada + Desmembrar referência MMM/AAAA nas 5 colunas temporais."
    },
}


def normalize_col_name(s: str) -> str:
    if not s:
        return ""
    s = str(s).strip().lower()
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s


def is_sentinel_ug(code: Any, name: Any = "") -> bool:
    c = str(code or "").strip().strip("'\"")
    n = str(name or "").strip().strip("'\"").upper()
    if not c:
        return True
    if c.startswith("-"):
        return True
    try:
        val = float(c.replace(",", "."))
        if val <= 0:
            return True
    except ValueError:
        pass
    if c.upper() in ("SEM INFORMACAO", "SEM INFORMAÇÃO", "INVALIDO", "INVÁLIDO", "NULL", "NONE", "N/A"):
        return True
    if n in ("-8", "'-8", "SEM INFORMACAO", "SEM INFORMAÇÃO", "INVALIDO", "INVÁLIDO"):
        return True
    return False


def split_ug_cell(raw_val: str, companion_name: str = "") -> Tuple[str, str, bool]:
    val = str(raw_val or "").strip()
    comp = str(companion_name or "").strip()

    if comp and not is_sentinel_ug(val) and re.fullmatch(r"\d{5,6}", val):
        return val.zfill(6), comp, False

    m_sent = re.match(r"^['\"]?(-\d+(?:\.\d+)?)['\"]?\s*(?:[-–/|:;]\s*|\s+)(.+)$", val)
    if m_sent:
        return m_sent.group(1).strip(), m_sent.group(2).strip(), True

    m_ug = re.match(r"^['\"]?(\d{5,6})['\"]?\s*(?:[-–/|:;]\s*|\s+)(.+)$", val)
    if m_ug:
        code = m_ug.group(1).strip().zfill(6)
        name = m_ug.group(2).strip()
        return code, name, True

    clean_code = val.strip("'\"")
    if re.fullmatch(r"\d{5,6}", clean_code):
        clean_code = clean_code.zfill(6)
    return clean_code, comp, False


def parse_monetary(val: Any, round_2_decimals: bool = False, preserve_null: bool = False) -> Tuple[Optional[Decimal], str]:
    if val is None:
        return (None, "") if preserve_null else (Decimal("0"), "0")
    s = str(val).strip().strip("'\"")
    s = re.sub(r"^[Rr]\$\s*", "", s).strip()
    if s == "" or s.upper() == "NULL":
        return (None, "") if preserve_null else (Decimal("0"), "0")

    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")

    try:
        d = Decimal(s)
    except InvalidOperation:
        return (None, "") if preserve_null else (Decimal("0"), "0")

    if round_2_decimals:
        d = d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return d, f"{d:.2f}"
    else:
        formatted = f"{d:f}"
        if "." in formatted:
            formatted = formatted.rstrip("0").rstrip(".")
        return d, formatted or "0"


def parse_mes_referencia(
    raw_ref: str,
    raw_ano_ref: str = "",
    raw_mes_ref: str = ""
) -> Optional[Dict[str, Any]]:
    ano: Optional[int] = None
    mes_num: Optional[int] = None

    ref = str(raw_ref or "").strip().upper()
    if ref:
        m1 = re.match(r"^([A-ZÇ]{3,9}|\d{1,2})[\s/\-_]+(\d{4})$", ref)
        m2 = re.match(r"^(\d{4})[\s/\-_]*([A-ZÇ]{3,9}|\d{1,2})$", ref)
        if m1:
            m_tok, y_tok = m1.group(1), m1.group(2)
            ano = int(y_tok)
            mes_num = MESES_MAP.get(m_tok)
        elif m2:
            y_tok, m_tok = m2.group(1), m2.group(2)
            ano = int(y_tok)
            mes_num = MESES_MAP.get(m_tok)

    if (ano is None or mes_num is None) and raw_ano_ref and raw_mes_ref:
        try:
            ano = int(str(raw_ano_ref).strip())
            mes_num = MESES_MAP.get(str(raw_mes_ref).strip().upper())
        except ValueError:
            pass

    if ano is None or mes_num is None or not (1990 <= ano <= 2100) or not (1 <= mes_num <= 12):
        return None

    sigla = NUMERO_PARA_SIGLA_MES[mes_num]
    ordem = f"{ano:04d}{mes_num:02d}"
    data_str = f"{ano:04d}-{mes_num:02d}-01"
    return {
        "ano_referencia_acc": str(ano),
        "mes_referencia_acc": sigla,
        "mes_referencia_numero": str(mes_num),
        "mes_referencia_ordem": ordem,
        "mes_referencia_data": data_str,
    }


def is_totalization_row(row: List[str]) -> bool:
    non_empty = [str(c).strip() for c in row if str(c).strip() != ""]
    if not non_empty:
        return True
    first_cells = [str(c).strip().upper() for c in row[:5] if str(c).strip()]
    for cell in first_cells:
        if cell in ("TOTAL", "TOTAL GERAL", "SUBTOTAL", "RESULTADO", "TOTALIZAÇÃO", "TOTALIZACAO", "SOMA"):
            return True
        if cell.startswith("TOTAL ") or cell.startswith("SUBTOTAL "):
            return True
    return False


def read_raw_rows_from_bytes(file_bytes: bytes, filename: str) -> List[List[str]]:
    ext = os.path.splitext(filename.lower())[1]
    if ext in (".xlsx", ".xlsm") and openpyxl is not None:
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
        ws = wb.active
        rows = []
        for r in ws.iter_rows(values_only=True):
            rows.append(["" if v is None else str(v).strip() for v in r])
        wb.close()
        return rows

    text = None
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            text = file_bytes.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        text = file_bytes.decode("utf-8", errors="replace")

    sample = text[:4096]
    delim = ";" if sample.count(";") >= sample.count(",") else ","
    if sample.count("\t") > max(sample.count(";"), sample.count(",")):
        delim = "\t"

    reader = csv.reader(io.StringIO(text), delimiter=delim)
    return [row for row in reader]


def analyze_spreadsheet_structure(raw_rows: List[List[str]], filename: str = "") -> Dict[str, Any]:
    header_idx = 0
    metadata_lines = []
    for idx, r in enumerate(raw_rows[:20]):
        non_empty = [c.strip() for c in r if c.strip()]
        norm_r = " ".join(normalize_col_name(c) for c in non_empty)
        if len(non_empty) >= 3 and any(
            kw in norm_r
            for kw in (
                "ug_", "ug", "ano", "provisao", "destaque", "material", "estoque",
                "permanente", "macroatividade", "atividade", "centro_custo",
                "ne", "nota_de_empenho"
            )
        ):
            header_idx = idx
            break
        elif non_empty:
            metadata_lines.append(" | ".join(non_empty))

    raw_headers = [c.strip() for c in raw_rows[header_idx]]
    norm_headers = [normalize_col_name(c) for c in raw_headers]
    norm_set = set(h for h in norm_headers if h)
    joined_headers = " ".join(norm_headers)

    sample_data_rows = [
        r for r in raw_rows[header_idx + 1 : header_idx + 40]
        if any(c.strip() for c in r) and not is_totalization_row(r)
    ]

    scores: Dict[str, int] = {k: 0 for k in TABLE_SCHEMAS}
    reasons: Dict[str, List[str]] = {k: [] for k in TABLE_SCHEMAS}

    # 01: tb_provisoes
    prov_signals = {
        "provisao_rcb", "provisao_recebida", "destaque_rcb", "destaque_recebido",
        "rpnp_insc", "provisao_liquidada", "provisao_a_liquidar", "rpnp_liq", "rpnp_a_liq"
    }
    matched_prov = norm_set.intersection(prov_signals)
    if matched_prov or "provisao" in joined_headers:
        scores["tb_provisoes"] += 60 + len(matched_prov) * 10
        reasons["tb_provisoes"].append(
            f"Colunas de execução orçamentária identificadas ({', '.join(sorted(list(matched_prov))[:5]) or 'provisao/destaque/rpnp'})"
        )

    # 02: tb_saldo_material_mb
    mat_signals = {
        "saldo_material_estoque", "material_em_estoque", "saldo_material_permanente", "material_permanente"
    }
    matched_mat = norm_set.intersection(mat_signals)
    if matched_mat or ("estoque" in joined_headers and "permanente" in joined_headers):
        scores["tb_saldo_material_mb"] += 80 + len(matched_mat) * 15
        reasons["tb_saldo_material_mb"].append(
            "Colunas patrimoniais de Material em Estoque e Material Permanente identificadas"
        )

    # 04: tb_custos_ugr_na_liq
    if "ne" in norm_set or "nota_de_empenho" in joined_headers or "nota_empenho" in joined_headers:
        scores["tb_custos_ugr_na_liq"] += 85
        reasons["tb_custos_ugr_na_liq"].append("Coluna de Nota de Empenho (NE) identificada no cabeçalho")

    ne_pattern_hits = 0
    mmm_aaaa_hits = 0
    for r in sample_data_rows[:15]:
        for cell in r:
            cs = cell.strip().upper()
            if re.fullmatch(r"\d{11}\d{4}NE\d{6}", cs):
                ne_pattern_hits += 1
            elif re.fullmatch(r"(JAN|FEV|MAR|ABR|MAI|JUN|JUL|AGO|SET|OUT|NOV|DEZ)[/\-_]\d{4}", cs):
                mmm_aaaa_hits += 1

    if ne_pattern_hits > 0:
        scores["tb_custos_ugr_na_liq"] += 45
        reasons["tb_custos_ugr_na_liq"].append("Detectados códigos de Nota de Empenho (padrão *NE*) nas linhas de dados")

    # 03: tb_custos_atividade vs 05: tb_custos_atividade_mes
    has_macro = any(k in joined_headers for k in ("macroatividade", "atividade_geral", "atividades_geral", "centro_custo"))
    has_mes_col = any(
        k in joined_headers
        for k in ("mes_referencia", "ano_referencia", "mes_lancamento", "mmm_aaaa", "competencia", "referencia_mensal")
    )

    if has_macro:
        if has_mes_col or mmm_aaaa_hits > 0:
            scores["tb_custos_atividade_mes"] += 90
            reasons["tb_custos_atividade_mes"].append(
                "Colunas de Macroatividade/Atividade combinadas com Referência Mensal (MMM/AAAA)"
            )
        else:
            scores["tb_custos_atividade"] += 85
            reasons["tb_custos_atividade"].append(
                "Colunas de Macroatividade, Atividade Geral, Centro de Custos e NDD (Arquivo 03)"
            )

    # Dica complementar pelo prefixo do nome do arquivo (01..05)
    fn_lower = (filename or "").lower()
    if fn_lower.startswith("01") or "provis" in fn_lower:
        scores["tb_provisoes"] += 15
    elif fn_lower.startswith("02") or "material" in fn_lower or "saldo" in fn_lower:
        scores["tb_saldo_material_mb"] += 15
    elif fn_lower.startswith("03"):
        scores["tb_custos_atividade"] += 15
    elif fn_lower.startswith("04") or "ugr" in fn_lower or "liq" in fn_lower:
        scores["tb_custos_ugr_na_liq"] += 15
    elif fn_lower.startswith("05") or "mes" in fn_lower or "mensal" in fn_lower:
        scores["tb_custos_atividade_mes"] += 15

    best_table = max(scores.items(), key=lambda x: x[1])[0]
    best_score = scores[best_table]

    inferred_year = "2026"
    for r in sample_data_rows[:10]:
        for i, nh in enumerate(norm_headers):
            if nh in ("ano_emissao", "ano", "ano_lancamento") and i < len(r):
                v = r[i].strip()
                if re.fullmatch(r"20\d{2}", v):
                    inferred_year = v
                    break

    return {
        "detected_table": best_table,
        "file_code": TABLE_SCHEMAS[best_table]["file_code"],
        "confidence_score": min(100, max(88, best_score)),
        "header_row_index": header_idx + 1,
        "metadata_skipped": metadata_lines,
        "raw_headers": raw_headers,
        "reasons": reasons[best_table],
        "inferred_ano_emissao": inferred_year,
    }


def process_table_secao10(
    file_bytes: bytes,
    filename: str,
    target_table: Optional[str] = None,
    default_ano_emissao: Optional[str] = None,
    cc_lookup: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    raw_rows = read_raw_rows_from_bytes(file_bytes, filename)
    if not raw_rows:
        raise ValueError("O arquivo enviado está vazio.")

    structural_analysis = analyze_spreadsheet_structure(raw_rows, filename)
    header_idx = structural_analysis["header_row_index"] - 1
    raw_headers = structural_analysis["raw_headers"]
    norm_headers = [normalize_col_name(c) for c in raw_headers]

    table_name = (
        target_table
        if (target_table and target_table != "AUTO" and target_table in TABLE_SCHEMAS)
        else structural_analysis["detected_table"]
    )
    auto_ano = default_ano_emissao or structural_analysis["inferred_ano_emissao"] or "2026"

    schema_info = TABLE_SCHEMAS[table_name]
    out_columns = schema_info["columns"]
    numeric_cols = schema_info["numeric_cols"]

    total_data_rows_read = 0
    totalization_rows_removed = 0
    ug_splits_count = 0
    sentinel_replacements_count = 0
    remaining_ug_sentinels = 0
    sample_transformations: List[Dict[str, Any]] = []
    validation_errors: List[str] = []

    raw_financial_sums: Dict[str, Decimal] = {c: Decimal("0") for c in numeric_cols}
    treated_financial_sums: Dict[str, Decimal] = {c: Decimal("0") for c in numeric_cols}
    treated_rows: List[List[str]] = []

    col_idx_map: Dict[str, int] = {}
    for i, nh in enumerate(norm_headers):
        if nh and nh not in col_idx_map:
            col_idx_map[nh] = i

    def get_cell(row: List[str], *aliases: str, default: str = "") -> str:
        for al in aliases:
            nal = normalize_col_name(al)
            if nal in col_idx_map and col_idx_map[nal] < len(row):
                return row[col_idx_map[nal]].strip()
        return default

    def extract_ug_pair(row: List[str], code_aliases: Tuple[str, ...], name_aliases: Tuple[str, ...]) -> Tuple[str, str]:
        nonlocal ug_splits_count
        raw_code = get_cell(row, *code_aliases)
        raw_name = get_cell(row, *name_aliases)
        if not raw_name:
            for al in code_aliases:
                nal = normalize_col_name(al)
                if nal in col_idx_map:
                    c_i = col_idx_map[nal]
                    if c_i + 1 < len(row) and (c_i + 1 >= len(norm_headers) or norm_headers[c_i + 1] == ""):
                        raw_name = row[c_i + 1].strip()
                    break
        code, name, was_split = split_ug_cell(raw_code, raw_name)
        if was_split:
            ug_splits_count += 1
        return code, name

    for r_idx, row in enumerate(raw_rows[header_idx + 1:], start=header_idx + 2):
        if not any(c.strip() for c in row):
            continue
        total_data_rows_read += 1

        if is_totalization_row(row):
            totalization_rows_removed += 1
            continue

        # =====================================================================
        # ARQUIVO 01: dfm.tb_provisoes
        # =====================================================================
        if table_name == "tb_provisoes":
            ano_emissao = get_cell(row, "ano_emissao", "ano_lancamento", "ano", default=auto_ano)
            ug_exec, ug_exec_nome = extract_ug_pair(
                row, ("ug_executora", "ug_exec"), ("ug_executora_nome", "nome_ug_executora")
            )
            ug_ben, ug_ben_nome = extract_ug_pair(
                row, ("ug_beneficiada_acc", "ug_beneficiada", "ug_ben"), ("ug_beneficiada_nome", "nome_ug_beneficiada")
            )
            ug_emit, ug_emit_nome = extract_ug_pair(
                row, ("ug_emitente", "ug_emit"), ("ug_emitente_nome", "nome_ug_emitente")
            )
            ug_resp, ug_resp_nome = extract_ug_pair(
                row, ("ug_responsavel", "ugr", "ug_resp"), ("ug_responsavel_nome", "nome_ug_responsavel")
            )

            if is_sentinel_ug(ug_ben, ug_ben_nome) and not is_sentinel_ug(ug_exec, ug_exec_nome):
                old_ben = f"{ug_ben} ({ug_ben_nome})"
                ug_ben, ug_ben_nome = ug_exec, ug_exec_nome
                sentinel_replacements_count += 1
                if len(sample_transformations) < 15:
                    sample_transformations.append({
                        "linha": r_idx,
                        "regra": "tb_provisoes: UG Beneficiada <- UG Executora",
                        "antes": old_ben,
                        "depois": f"{ug_ben} ({ug_ben_nome})"
                    })

            if is_sentinel_ug(ug_exec, ug_exec_nome) and not is_sentinel_ug(ug_ben, ug_ben_nome):
                ug_exec, ug_exec_nome = ug_ben, ug_ben_nome

            if is_sentinel_ug(ug_emit, ug_emit_nome):
                ug_emit, ug_emit_nome = ug_exec, ug_exec_nome

            if is_sentinel_ug(ug_resp, ug_resp_nome):
                ug_resp, ug_resp_nome = ug_ben, ug_ben_nome

            if is_sentinel_ug(ug_ben, ug_ben_nome):
                remaining_ug_sentinels += 1

            acao_gov, acao_gov_nome, _ = split_ug_cell(
                get_cell(row, "acao_governo", "acao"),
                get_cell(row, "acao_governo_nome", "nome_acao_governo")
            )
            pi_code = get_cell(row, "pi", "plano_interno")
            pi_nome = get_cell(row, "pi_nome", "nome_plano_interno")
            if not pi_nome and " - " in pi_code:
                parts = pi_code.split(" - ", 1)
                pi_code, pi_nome = parts[0].strip(), parts[1].strip()

            num_strs = {}
            for nc in numeric_cols:
                raw_v = get_cell(row, nc)
                d_raw, s_fmt = parse_monetary(raw_v, round_2_decimals=False, preserve_null=False)
                if d_raw is not None:
                    raw_financial_sums[nc] += d_raw
                    treated_financial_sums[nc] += d_raw
                num_strs[nc] = s_fmt

            treated_rows.append([
                ano_emissao,
                ug_ben, ug_ben_nome,
                ug_emit, ug_emit_nome,
                ug_exec, ug_exec_nome,
                ug_resp, ug_resp_nome,
                acao_gov, acao_gov_nome,
                num_strs["provisao_rcb"], num_strs["destaque_rcb"], num_strs["rpnp_insc"],
                num_strs["provisao_liquidada"], num_strs["destaque_liquidado"], num_strs["rpnp_liq"],
                num_strs["provisao_a_liquidar"], num_strs["destaque_a_liquidar"], num_strs["rpnp_a_liq"],
                pi_code, pi_nome
            ])

        # =====================================================================
        # ARQUIVO 02: dfm.tb_saldo_material_mb
        # =====================================================================
        elif table_name == "tb_saldo_material_mb":
            ano = get_cell(row, "ano", "ano_lancamento", "ano_emissao", default=auto_ano).strip()
            ug_exec, ug_exec_nome = extract_ug_pair(
                row,
                ("ug_executora", "ug_beneficiada_acc", "ug_beneficiada", "ug"),
                ("ug_executora_nome", "ug_beneficiada_nome", "nome_ug")
            )
            ug_ben, ug_ben_nome = extract_ug_pair(
                row,
                ("ug_beneficiada_acc", "ug_executora", "ug_beneficiada", "ug"),
                ("ug_beneficiada_nome", "ug_executora_nome", "nome_ug")
            )
            if is_sentinel_ug(ug_ben, ug_ben_nome) and not is_sentinel_ug(ug_exec, ug_exec_nome):
                ug_ben, ug_ben_nome = ug_exec, ug_exec_nome
            if is_sentinel_ug(ug_exec, ug_exec_nome) and not is_sentinel_ug(ug_ben, ug_ben_nome):
                ug_exec, ug_exec_nome = ug_ben, ug_ben_nome

            if is_sentinel_ug(ug_ben, ug_ben_nome):
                remaining_ug_sentinels += 1

            raw_est = get_cell(row, "saldo_material_estoque", "material_em_estoque", "estoque")
            raw_perm = get_cell(row, "saldo_material_permanente", "material_permanente", "permanente")

            d_est_raw, _ = parse_monetary(raw_est, round_2_decimals=False, preserve_null=True)
            d_perm_raw, _ = parse_monetary(raw_perm, round_2_decimals=False, preserve_null=True)
            if d_est_raw is not None:
                raw_financial_sums["saldo_material_estoque"] += d_est_raw
            if d_perm_raw is not None:
                raw_financial_sums["saldo_material_permanente"] += d_perm_raw

            d_est_2, s_est = parse_monetary(raw_est, round_2_decimals=True, preserve_null=True)
            d_perm_2, s_perm = parse_monetary(raw_perm, round_2_decimals=True, preserve_null=True)
            if d_est_2 is not None:
                treated_financial_sums["saldo_material_estoque"] += d_est_2
            if d_perm_2 is not None:
                treated_financial_sums["saldo_material_permanente"] += d_perm_2

            treated_rows.append([
                ano,
                ug_exec, ug_exec_nome,
                ug_ben, ug_ben_nome,
                s_est, s_perm
            ])

        # =====================================================================
        # ARQUIVO 03: dfm.tb_custos_atividade
        # =====================================================================
        elif table_name == "tb_custos_atividade":
            ano_emissao = get_cell(row, "ano_emissao", "ano_lancamento", "ano", default=auto_ano)
            ug_emit, ug_emit_nome = extract_ug_pair(
                row, ("ug_emitente", "ug_emit"), ("ug_emitente_nome", "nome_ug_emitente")
            )
            ug_resp, ug_resp_nome = extract_ug_pair(
                row, ("ug_responsavel", "ugr", "ug_resp"), ("ug_responsavel_nome", "nome_ug_responsavel")
            )
            ug_ben, ug_ben_nome = extract_ug_pair(
                row, ("ug_beneficiada_acc", "ug_beneficiada"), ("ug_beneficiada_nome", "nome_ug_beneficiada")
            )

            if is_sentinel_ug(ug_resp, ug_resp_nome):
                old_resp = f"{ug_resp} ({ug_resp_nome})"
                ug_resp, ug_resp_nome = ug_emit, ug_emit_nome
                sentinel_replacements_count += 1
                if len(sample_transformations) < 15:
                    sample_transformations.append({
                        "linha": r_idx,
                        "regra": "tb_custos_atividade: UG Responsável <- UG Emitente",
                        "antes": old_resp,
                        "depois": f"{ug_resp} ({ug_resp_nome})"
                    })

            if is_sentinel_ug(ug_resp, ug_resp_nome) or is_sentinel_ug(ug_emit, ug_emit_nome) or is_sentinel_ug(ug_ben, ug_ben_nome):
                remaining_ug_sentinels += 1

            acao_gov = get_cell(row, "acao_governo", "acao")
            acao_gov_nome = get_cell(row, "acao_governo_nome", "nome_acao_governo")
            macro_mb = get_cell(row, "macroatividades_mb", "macroatividade")
            macro_simple = get_cell(row, "macroatividade", "macroatividades_mb") or macro_mb
            ativ = get_cell(row, "atividade_geral", "atividades_geral", "atividade")
            cc = get_cell(row, "centro_custos", "centro_custo", "centro_custos_codigo")
            ndd = get_cell(row, "natureza_despesa_detalhada", "ndd")
            ndd_nome = get_cell(row, "natureza_despesa_detalhada_nome", "nome_ndd")

            raw_val = get_cell(row, "valor_dh", "detacusto_dh_rs", "valor")
            d_val, s_val = parse_monetary(raw_val, round_2_decimals=False, preserve_null=False)
            raw_financial_sums["valor_dh"] += d_val or Decimal("0")
            treated_financial_sums["valor_dh"] += d_val or Decimal("0")

            treated_rows.append([
                ano_emissao,
                ug_emit, ug_emit_nome,
                ug_resp, ug_resp_nome,
                macro_simple, macro_mb,
                cc, ativ,
                s_val,
                ug_ben, ug_ben_nome,
                acao_gov, acao_gov_nome,
                ndd, ndd_nome
            ])

        # =====================================================================
        # ARQUIVO 04: dfm.tb_custos_ugr_na_liq
        # =====================================================================
        elif table_name == "tb_custos_ugr_na_liq":
            ano_emissao = get_cell(row, "ano_emissao", "ano_lancamento", "ano", default=auto_ano)
            ug_resp, ug_resp_nome = extract_ug_pair(
                row, ("ug_responsavel", "ugr", "ug_resp"), ("ug_responsavel_nome", "nome_ug_responsavel")
            )
            ug_emit, ug_emit_nome = extract_ug_pair(
                row, ("ug_emitente", "ug_emit"), ("ug_emitente_nome", "nome_ug_emitente")
            )
            ug_ben, ug_ben_nome = extract_ug_pair(
                row, ("ug_beneficiada_acc", "ug_beneficiada"), ("ug_beneficiada_nome", "nome_ug_beneficiada")
            )

            if is_sentinel_ug(ug_resp, ug_resp_nome):
                old_resp = f"{ug_resp} ({ug_resp_nome})"
                ug_resp, ug_resp_nome = ug_emit, ug_emit_nome
                sentinel_replacements_count += 1
                if len(sample_transformations) < 15:
                    sample_transformations.append({
                        "linha": r_idx,
                        "regra": "tb_custos_ugr_na_liq: UG Responsável <- UG Emitente",
                        "antes": old_resp,
                        "depois": f"{ug_resp} ({ug_resp_nome})"
                    })

            if is_sentinel_ug(ug_resp, ug_resp_nome) or is_sentinel_ug(ug_emit, ug_emit_nome) or is_sentinel_ug(ug_ben, ug_ben_nome):
                remaining_ug_sentinels += 1

            ne = get_cell(row, "ne", "nota_empenho", "nota_de_empenho")
            raw_val = get_cell(row, "detacusto_dh_rs", "valor_dh", "valor")
            d_val, s_val = parse_monetary(raw_val, round_2_decimals=False, preserve_null=False)
            raw_financial_sums["detacusto_dh_rs"] += d_val or Decimal("0")
            treated_financial_sums["detacusto_dh_rs"] += d_val or Decimal("0")

            treated_rows.append([
                ano_emissao,
                ug_emit, ug_emit_nome,
                ug_resp, ug_resp_nome,
                s_val,
                ug_ben, ug_ben_nome,
                ne
            ])

        # =====================================================================
        # ARQUIVO 05: dfm.tb_custos_atividade_mes
        # =====================================================================
        elif table_name == "tb_custos_atividade_mes":
            ano_emissao = get_cell(row, "ano_emissao", "ano_lancamento", default=auto_ano)
            raw_mmm_aaaa = get_cell(row, "mes_referencia", "referencia", "mmm_aaaa", "competencia", "mes_lancamento")
            raw_ano_ref = get_cell(row, "ano_referencia_acc", "ano_referencia")
            raw_mes_ref = get_cell(row, "mes_referencia_acc")
            ref_info = parse_mes_referencia(raw_mmm_aaaa, raw_ano_ref, raw_mes_ref)
            if not ref_info:
                validation_errors.append(f"Linha {r_idx}: Referência mensal inválida ('{raw_mmm_aaaa}' / '{raw_mes_ref}/{raw_ano_ref}').")
                ref_info = {
                    "ano_referencia_acc": raw_ano_ref or auto_ano,
                    "mes_referencia_acc": raw_mes_ref or "JAN",
                    "mes_referencia_numero": get_cell(row, "mes_referencia_numero") or "1",
                    "mes_referencia_ordem": get_cell(row, "mes_referencia_ordem") or f"{auto_ano}01",
                    "mes_referencia_data": get_cell(row, "mes_referencia_data") or f"{auto_ano}-01-01",
                }

            ug_resp, ug_resp_nome = extract_ug_pair(
                row, ("ug_responsavel", "ugr", "ug_resp"), ("ug_responsavel_nome", "nome_ug_responsavel")
            )
            ug_ben, ug_ben_nome = extract_ug_pair(
                row, ("ug_beneficiada_acc", "ug_beneficiada"), ("ug_beneficiada_nome", "nome_ug_beneficiada")
            )
            ug_emit, ug_emit_nome = extract_ug_pair(
                row, ("ug_emitente", "ug_emit"), ("ug_emitente_nome", "nome_ug_emitente")
            )

            if is_sentinel_ug(ug_resp, ug_resp_nome):
                if not is_sentinel_ug(ug_ben, ug_ben_nome) and ug_ben and ug_ben_nome:
                    old_resp = f"{ug_resp} ({ug_resp_nome})"
                    ug_resp, ug_resp_nome = ug_ben, ug_ben_nome
                    sentinel_replacements_count += 1
                    if len(sample_transformations) < 15:
                        sample_transformations.append({
                            "linha": r_idx,
                            "regra": "tb_custos_atividade_mes: UG Responsável <- UG Beneficiada",
                            "antes": old_resp,
                            "depois": f"{ug_resp} ({ug_resp_nome})"
                        })

            if is_sentinel_ug(ug_resp, ug_resp_nome):
                remaining_ug_sentinels += 1

            acao_gov = get_cell(row, "acao_governo", "acao")
            acao_gov_nome = get_cell(row, "acao_governo_nome", "nome_acao_governo")
            macro = get_cell(row, "macroatividades_mb", "macroatividade")
            ativ = get_cell(row, "atividades_geral", "atividade_geral", "atividade")
            cc = get_cell(row, "centro_custos", "centro_custo", "centro_custos_codigo")
            ndd = get_cell(row, "natureza_despesa_detalhada", "ndd")
            ndd_nome = get_cell(row, "natureza_despesa_detalhada_nome", "nome_ndd")

            raw_val = get_cell(row, "detacusto_dh_rs", "valor_dh", "valor")
            d_val, s_val = parse_monetary(raw_val, round_2_decimals=False, preserve_null=False)
            raw_financial_sums["detacusto_dh_rs"] += d_val or Decimal("0")
            treated_financial_sums["detacusto_dh_rs"] += d_val or Decimal("0")

            treated_rows.append([
                ano_emissao,
                ref_info["ano_referencia_acc"],
                ref_info["mes_referencia_acc"],
                ref_info["mes_referencia_numero"],
                ref_info["mes_referencia_ordem"],
                ref_info["mes_referencia_data"],
                ug_resp, ug_resp_nome,
                ug_ben, ug_ben_nome,
                ug_emit, ug_emit_nome,
                acao_gov, acao_gov_nome,
                macro, ativ, cc, ndd, ndd_nome, s_val
            ])

    csv_buf = io.StringIO()
    writer = csv.writer(csv_buf, delimiter=";", lineterminator="\n")
    writer.writerow(out_columns)
    for tr in treated_rows:
        writer.writerow(tr)
    csv_content = csv_buf.getvalue()

    reconciliation = []
    for nc in numeric_cols:
        orig_v = float(raw_financial_sums[nc])
        trat_v = float(treated_financial_sums[nc])
        diff_v = round(trat_v - orig_v, 2)
        reconciliation.append({
            "coluna": nc,
            "soma_original": round(orig_v, 2),
            "soma_tratada": round(trat_v, 2),
            "diferenca": diff_v,
            "status": "OK" if abs(diff_v) < 1.0 else "DIVERGENTE"
        })

    status_final = "SUCESSO" if len(validation_errors) == 0 else "ERRO"

    return {
        "table_name": table_name,
        "file_code": schema_info["file_code"],
        "short_name": schema_info["short_name"],
        "table_label": schema_info["label"],
        "rule_title": schema_info["rule_title"],
        "rule_summary": schema_info["rule_summary"],
        "structural_analysis": structural_analysis,
        "filename": filename,
        "status": status_final,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "metrics": {
            "total_linhas_lidas": total_data_rows_read,
            "linhas_totalizacao_removidas": totalization_rows_removed,
            "total_linhas_tratadas": len(treated_rows),
            "pares_ug_desmembrados": ug_splits_count,
            "sentinelas_substituidas": sentinel_replacements_count,
            "sentinelas_restantes_ug": remaining_ug_sentinels,
        },
        "reconciliation": reconciliation,
        "sample_transformations": sample_transformations,
        "validation_errors": validation_errors[:25],
        "preview_headers": out_columns,
        "preview_rows": treated_rows[:50],
        "treated_rows": treated_rows,
        "csv_content": csv_content,
    }


def generate_synthetic_raw_sample(table_name: str) -> Tuple[str, bytes]:
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";", lineterminator="\n")

    if table_name == "tb_provisoes":
        w.writerow([
            "ano_emissao", "ug_executora", "ug_beneficiada_acc", "acao_governo",
            "provisao_rcb", "destaque_rcb", "rpnp_insc",
            "provisao_liquidada", "destaque_liquidado", "rpnp_liq",
            "provisao_a_liquidar", "destaque_a_liquidar", "rpnp_a_liq",
            "ug_responsavel", "pi", "pi_nome"
        ])
        w.writerow([
            "2026", "672001 - UNIDADE EXECUTORA CENTRAL", "-8 - SEM INFORMACAO",
            "2000 - ADMINISTRACAO DA UNIDADE", "150000.00", "", "25000.00",
            "100000.00", "", "15000.00", "50000.00", "", "10000.00",
            "'-8 - SEM INFORMACAO", "B406FC0Z1B4", "FUNCIONAMENTO"
        ])
        w.writerow([
            "2026", "791800 - BASE OPERACIONAL REGIONAL", "691534 - UNIDADE ESPECIALIZADA",
            "21A0 - APRESTAMENTO E OPERACOES", "890000.50", "0", "0",
            "450000.25", "0", "0", "440000.25", "0", "0",
            "691534 - UNIDADE ESPECIALIZADA", "C302090Z1B4", "MANUTENCAO"
        ])
        w.writerow([
            "Total Geral", "", "", "", "1040000.50", "0", "25000.00",
            "550000.25", "0", "15000.00", "490000.25", "0", "10000.00", "", "", ""
        ])
        return "01_Provisoes_Amostra_Bruta.csv", buf.getvalue().encode("utf-8")

    elif table_name == "tb_saldo_material_mb":
        w.writerow(["Ano Lançamento", "UG Executora", "MATERIAL EM ESTOQUE", "MATERIAL PERMANENTE"])
        w.writerow(["2026", "710100 - UNIDADE GESTORA 01", "37485.044", "829233.741"])
        w.writerow(["2026", "720301 - CENTRO DE PESQUISAS", "", "4548855.059"])
        w.writerow(["Total", "", "37485.044", "5378088.80"])
        return "02_Saldo_Material_Amostra_Bruta.csv", buf.getvalue().encode("utf-8")

    elif table_name == "tb_custos_atividade":
        w.writerow([
            "ano_emissao", "ug_emitente", "ug_responsavel", "ug_beneficiada_acc",
            "acao_governo", "acao_governo_nome", "macroatividades_mb", "atividade_geral",
            "centro_custos", "natureza_despesa_detalhada", "natureza_despesa_detalhada_nome", "valor_dh"
        ])
        w.writerow([
            "2026", "791800 - UNIDADE GESTORA REGIONAL 01", "-8 - SEM INFORMACAO",
            "691534 - CENTRO DE OPERACOES", "21A0", "OPERACOES E LOGISTICA",
            "B6.00 - MANUTENÇÃO E SUPORTE", "B6.05 – MANUTENÇÃO CORRETIVA",
            "B60504", "33903917", "MANUT. E CONSERV. DE MAQUINAS E EQUIPAMENTOS", "45980.75"
        ])
        w.writerow([
            "2026", "710100 - UNIDADE DE ATENDIMENTO E GESTAO", "'-8",
            "710100 - UNIDADE DE ATENDIMENTO E GESTAO", "'-8", "SEM INFORMACAO",
            "29.00 - DEMAIS ATIVIDADES FINALÍSTICAS", "29.99 – DEPRECIAÇÃO DE BENS MÓVEIS",
            "299901", "-8", "SEM INFORMACAO", "10009.65"
        ])
        w.writerow(["Total", "", "", "", "", "", "", "", "", "", "", "55990.40"])
        return "03_Custos_Atividade_Amostra_Bruta.csv", buf.getvalue().encode("utf-8")

    elif table_name == "tb_custos_ugr_na_liq":
        w.writerow(["ano_emissao", "ug_responsavel", "ug_emitente", "ug_beneficiada_acc", "ne", "detacusto_dh_rs"])
        w.writerow([
            "2026", "-8.0 - SEM INFORMACAO", "710100 - UNIDADE GESTORA 01",
            "710100 - UNIDADE GESTORA 01", "710100000012026NE000009", "75000.00"
        ])
        w.writerow([
            "2026", "'-8", "784800 - CENTRO REGIONAL NORTE",
            "160502 - DEPARTAMENTO DE ENGENHARIA", "784800000012025NE000112", "28442.70"
        ])
        w.writerow(["Total Geral", "", "", "", "", "103442.70"])
        return "04_Custos_UGR_LIQ_Amostra_Bruta.csv", buf.getvalue().encode("utf-8")

    else:
        w.writerow([
            "ano_emissao", "mes_referencia", "ug_responsavel", "ug_beneficiada_acc", "ug_emitente",
            "acao_governo", "acao_governo_nome", "macroatividades_mb", "atividades_geral",
            "centro_custos", "natureza_despesa_detalhada", "natureza_despesa_detalhada_nome", "detacusto_dh_rs"
        ])
        w.writerow([
            "2026", "JAN/2026", "-8 - SEM INFORMACAO", "765700 - CENTRO ASSISTENCIAL",
            "765709 - UNIDADE REGIONAL", "2004", "ASSISTENCIA E SERVICOS",
            "59.00 - ATIVIDADES ADMINISTRATIVAS", "59.01 – ADMINISTRAÇÃO DA UNIDADE",
            "590103", "33903969", "SEGUROS EM GERAL", "77.62"
        ])
        w.writerow([
            "2026", "FEV/2026", "'-8", "710100 - UNIDADE GESTORA 01",
            "710100 - UNIDADE GESTORA 01", "2000", "ADMINISTRACAO DA UNIDADE",
            "59.00 - ATIVIDADES ADMINISTRATIVAS", "59.01 – ADMINISTRAÇÃO DA UNIDADE",
            "590101", "33903943", "SERVICOS DE ENERGIA ELETRICA", "23650.60"
        ])
        w.writerow(["Total", "", "", "", "", "", "", "", "", "", "", "", "23728.22"])
        return "05_Custos_Mensal_Amostra_Bruta.csv", buf.getvalue().encode("utf-8")
