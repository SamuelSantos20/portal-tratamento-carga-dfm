"""Respostas fundamentadas nas analises atuais, sem SQL livre ou cargas pela IA."""
import re
import unicodedata
from backend import ai_sessions
from backend.ai_model import model
from backend.engine_secao10 import TABLE_SCHEMAS

def normalize(text):
    return ''.join(c for c in unicodedata.normalize('NFKD', text.casefold()) if not unicodedata.combining(c))

def deterministic_intent(question):
    q = normalize(question)
    if re.search(r'\b(?:delete|drop|truncate|insert|update|apague|exclua|carregue|execute)\b', q):
        return 'fora_escopo'
    if any(t in q for t in ('total', 'totais', 'somatorio', 'valores', 'soma')):
        if any(t in q for t in ('arquivo', 'tabela', 'base', 'analise', 'sessao')):
            return 'consulta_totais_sessao'
    if not q.startswith(('como ', 'por que ', 'qual regra ')) and any(t in q for t in ('arquivo', 'planilha', 'base', 'tabela')) and any(t in q for t in ('tratad', 'analisad', 'processad', 'conclu')):
        return 'relatorio'
    return None

def selected_tables(question, files):
    q = normalize(question)
    codes = {code.zfill(2) for code in re.findall(r'\barquivo\s*(0?[1-5])\b', q)}
    for name, schema in TABLE_SCHEMAS.items():
        if re.search(r'\b' + re.escape(name) + r'\b', q):
            codes.add(schema['file_code'])
    if 'proviso' in q:
        codes.add('01')
    if 'estoque' in q or 'permanente' in q:
        codes.add('02')
    return [f for f in files if not codes or f['arquivo'] in codes]

def answer(question, session_id=None):
    intent = deterministic_intent(question)
    prediction = None
    if intent is None:
        try:
            prediction = model.classify(question)
        except RuntimeError:
            return {'status': 'modelo_indisponivel', 'resposta': 'O classificador local está indisponível. Você ainda pode consultar os arquivos tratados e os totais da sessão.', 'fonte': 'portal local'}
        if not prediction['aceita']:
            return {'status': 'abstencao', 'resposta': 'Não identifiquei uma pergunta coberta com segurança. Informe o arquivo, a regra ou a medida que deseja consultar.', 'fonte': 'classificador local experimental'}
        intent = prediction['intencao']
    if intent == 'fora_escopo':
        return {'status': 'fora_escopo', 'resposta': 'O assistente consulta análises e explica o tratamento. Cargas e alterações no banco continuam na etapa de confirmação do portal.', 'fonte': 'escopo do assistente'}
    if intent in ('relatorio', 'consulta_totais_sessao', 'consulta_total', 'consulta_ranking', 'auditoria'):
        session = ai_sessions.summary(session_id)
        requested_codes = {code.zfill(2) for code in re.findall(r'\barquivo\s*(\d{1,2})\b', normalize(question))}
        requested_names = set(re.findall(r'\b(tb_[a-z0-9_]+)\b', normalize(question)))
        if requested_codes - set(session['escopo']) or requested_names - TABLE_SCHEMAS.keys():
            return {'status': 'fora_escopo', 'resposta': 'Este assistente acompanha os arquivos 01 a 05. SIORG e energia estão fora do tratamento desta versão.', 'fonte': 'escopo da sessão'}
        files = selected_tables(question, session['arquivos'])
        if intent in ('relatorio', 'auditoria'):
            text = 'Todas as cinco bases da sessão foram tratadas com sucesso.' if session['todas_tratadas'] else 'A sessão ainda tem bases ausentes ou com pendências.'
            return {'status': 'consultado', 'resposta': text + ' Tratamento em prévia e carga no banco são etapas distintas. Simulações não contam como arquivos reais.', 'sessao': session, 'arquivos': files, 'fonte': 'histórico de análises deste portal', 'intencao': intent}
        q = normalize(question)
        if intent == 'consulta_ranking' or re.search(r'\b\d{6}\b|\bug\b|\bmes\b', q) or any(t in q for t in ('acao', 'macroatividade', 'centro de custo', 'natureza', 'competencia', 'referencia', 'ranking', 'energia', 'janeiro', 'fevereiro', 'marco', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro')):
            return {'status': 'esclarecimento', 'resposta': 'Os totais da sessão estão disponíveis por tabela, medida e ano. Esse filtro ou ranking não está disponível no histórico resumido; não vou ignorá-lo.', 'fonte': 'escopo da consulta'}
        years = set(re.findall(r'\b20\d{2}\b', q))
        if len(years) > 1:
            return {'status': 'esclarecimento', 'resposta': 'Informe um único ano ou consulte os totais de todos os anos da sessão.', 'fonte': 'escopo da consulta'}
        totals = []
        for file in files:
            if file['status'] != 'SUCESSO':
                continue
            groups = [g for g in file['totais_por_ano'] if not years or g['ano'] in years]
            totals.append({'arquivo': file['arquivo'], 'tabela': file['tabela'], 'por_ano': groups})
        return {'status': 'calculado' if totals else 'sem_dados', 'resposta': 'Totais das últimas prévias bem-sucedidas de cada tabela nesta sessão, separados por medida e ano. Não somamos tabelas que representam visões diferentes. Bases com erro ficam fora dos totais.', 'sessao_id': session['id'], 'totais': totals, 'arquivos_pendentes': session['arquivos_pendentes'], 'fonte': 'linhas tratadas nesta sessão; soma decimal exata', 'intencao': intent}
    return {'status': 'regra_citada', 'resposta': prediction['regra'], 'pagina_manual': prediction['pagina'], 'pontuacao_classificacao': prediction['pontuacao'], 'intencao': intent, 'fonte': 'base privada revisada do manual; classificador experimental'}
