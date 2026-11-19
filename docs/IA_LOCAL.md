# Assistente IA local

O portal usa o classificador próprio já treinado para identificar intenções e recuperar regras de uma base privada. Não usa APIs de geração, não treina com os uploads e não gera SQL livre. O classificador continua experimental: respostas incertas são recusadas. Uma pontuação de classificação não garante correção.

## O que está integrado

- Aba **Assistente IA**, com conversa em memória e fontes das respostas.
- As perguntas sobre arquivos tratados, totais e conclusão consultam o histórico real deste portal. Funcionam mesmo sem os pesos instalados.
- Sessões explícitas: **Nova sessão** mantém as análises anteriores, sem misturar os totais. Reimportar uma tabela substitui sua prévia mais recente no resumo; não soma o mesmo arquivo duas vezes.
- Totais por tabela, medida e ano, calculados com `Decimal` sobre as linhas tratadas. Valores ausentes continuam ausentes. Não existe soma geral entre tabelas que representam visões diferentes. Filtros não suportados são esclarecidos, não ignorados.
- Arquivos com erros e simulações são identificados. Simulações não completam o escopo de arquivos reais; falhas de reconhecimento também ficam registradas. A resposta distingue prévia tratada e carga confirmada.
- A IA não pode confirmar cargas nem alterar o PostgreSQL. A confirmação continua na etapa de carga do portal; lotes inválidos ou de outra sessão são bloqueados.

O escopo atual são os arquivos 01–05. SIORG e energia não estão incluídos. Regras do arquivo 01: Responsável inválida recebe código e nome da Executora da mesma linha; Executora permanece; Beneficiada recebe uma cópia desse par.

## Armazenamento e acesso

O padrão Windows é `%LOCALAPPDATA%\SCM-Confidencial`. No Linux é `~/.local/share/scm-confidencial`. `SCM_PRIVATE_DIR` pode indicar outro caminho absoluto fora do repositório e de pastas sincronizadas. Confira também sincronizadores com nomes diferentes, que não podem ser detectados apenas pelo caminho.

Arquivos do portal ficam em `portal/`: banco SQLite, histórico resumido, exportações e configuração do PostgreSQL. A importação automática de arquivos de Downloads foi desativada; o operador deve enviar e conferir suas planilhas. A opção legada `SCM_SEED_LEGACY=true` existe apenas para compatibilidade e não deve ser usada com fontes confidenciais sem revisão.

No Windows a pasta de dados exige EFS, e novos arquivos herdam a criptografia. Não desative esse controle se o volume não suportar EFS; prepare um destino compatível. No Linux as pastas são restritas ao usuário, e a criptografia do volume deve ser fornecida pela instalação. EFS e DPAPI dependem de chaves do usuário Windows: preserve-as antes de reinstalar ou migrar o computador.

As APIs exigem uma sessão local de oito horas, com cookie `HttpOnly`/`SameSite=Strict`. O inicializador lê uma chave privada do operador, abre o acesso por fragmento temporário e a interface remove esse fragmento da URL. A chave não é impressa. O servidor confere cliente loopback, Host e Origin; não aceita acesso remoto. O inicializador verifica uma prova HMAC antes de reutilizar um serviço na porta local.

O processo de inferência recebe apenas a pergunta por pipe local, usa CPU e bloqueia conexões da rede Python como defesa adicional. Isso não constitui uma sandbox do sistema operacional. Não há telemetria de perguntas, respostas em logs ou persistência da conversa no servidor. As respostas de API usam `Cache-Control: no-store`. Recursos de fontes externas foram removidos da interface.

Esses controles não impedem administradores ou software com as mesmas credenciais do operador. O portal está preparado para uso por um operador local; hospedagem em rede exige um projeto separado de autenticação por usuário, autorização, TLS e isolamento de dados. Não exponha esta instalação por túneis ou proxies que transformem clientes remotos em loopback.

## Instalar os pesos no computador autorizado

Os pesos e o código privado derivado do manual **não estão neste repositório público**. Preserve-os por um canal privado autorizado. Este projeto contém somente a integração genérica e testes com dados fictícios.

Use Python 3.12, com as dependências do backend e as dependências opcionais da IA:

```powershell
python -m pip install -r requirements.txt -r requirements-ai.txt
python -m pip install torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu
```

Não há necessidade de instalar CUDA ou refazer o treinamento. As versões correspondem ao runtime recuperado, usando a distribuição CPU de PyTorch. Instale somente a partir das fontes oficiais e não carregue `joblib`/checkpoints de origem desconhecida: podem conter objetos executáveis.

Disponha a base recuperada dentro da área privada e os cinco módulos privados (`assistente.py`, `conhecimento.py`, `modelo.py`, `processamento.py`, `runtime_security.py`) em uma pasta de origem confiável. Configure uma vez:

```powershell
$scmBase = Join-Path $env:LOCALAPPDATA 'SCM-Confidencial\trabalho\resultado_colab\artefatos'
python scripts/configurar_ia_local.py --runtime-origem 'C:\PASTA_PRIVADA\ia_scm' --base $scmBase
```

O comando copia o código para `runtime/ia_scm` na área privada e registra hashes dos módulos e dos pesos. Não copia conteúdo para o Git. O servidor verifica essa integridade antes de carregar o modelo. Uma alteração no runtime exige revisão e nova configuração; não edite os hashes para contornar uma divergência.

`SCM_AI_MANIFEST` permite escolher outro manifesto absoluto dentro de `SCM_PRIVATE_DIR`. Não forneça caminhos recebidos de usuários da interface.

Na máquina já configurada, `iniciar_sistema.bat` usa `.venv` do projeto quando existir ou o ambiente privado `runtime/portal-venv`. Abra pelo inicializador para estabelecer a sessão autorizada; acessar só o endereço HTTP sem a sessão não libera as APIs.

## Dados de uma instalação anterior

Se houver `data/dfm_scm.db` na instalação antiga e nenhum banco privado, o início é interrompido para evitar que um banco vazio pareça substituir o existente. Com o portal anterior fechado, execute:

```powershell
python scripts/migrar_armazenamento.py
```

O comando copia o SQLite consistentemente e a configuração existente para a área privada, sem sobrescrever destinos nem apagar origens. Revise a cópia antes de decidir separadamente sobre a remoção dos arquivos antigos. Históricos do OneDrive ou de outros provedores não são removidos por esse procedimento.

## Verificação e limites

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
cd frontend
npm ci
npm run build
```

Os testes usam arquivos inteiramente fictícios em diretórios temporários e não precisam dos pesos privados. A CI pública executa somente esses testes. Perguntas sobre sessão se referem às análises feitas no portal, não importam automaticamente o histórico do treinamento no Colab.

Não publique bases, planilhas, manual, perguntas reais, pesos, chave de acesso ou backups no Git. `.gitignore` e hooks são defesas auxiliares que podem ser ignoradas; revise cada diff antes de publicar. A proteção local não apaga cópias já existentes nos provedores. A decisão anterior de manter Colab e notebook online permanece respeitada por esta integração.

Ative os hooks também em novas cópias de trabalho: `git config --local core.hooksPath .githooks`.
