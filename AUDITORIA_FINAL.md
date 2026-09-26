# Auditoria e endurecimento do projeto

## O que foi corrigido

- Isolamento por escola reforçado em views administrativas, formulários, análises e reservas fixas.
- Rotas destrutivas/mutáveis críticas passaram a exigir POST + CSRF.
- Painéis de superadmin passaram a exigir superusuário real.
- PIN de envio de tablet passou a ser armazenado com hash.
- Códigos de verificação passaram a ser gerados com fonte criptograficamente segura e deixaram de aparecer no `__str__`/Django Admin.
- Senhas de criação de conta/admin passaram a respeitar os validadores de senha do Django.
- Reservas receberam índices e restrições de banco para horários inválidos, quantidade positiva e conflito de carrinho integral.
- Operações críticas de reserva usam transação/lock para reduzir corrida entre requisições concorrentes, inclusive reservas fixas e pedidos de reposição.
- Quantidade disponível de carrinhos sem numeração individual foi corrigida; notebooks inativos passam a ser descontados corretamente quando há numeração.
- Faixas de numeração e vínculos escola/equipamento/sala passaram a ser validados.
- Respostas AJAX deixaram de devolver exceções internas ao usuário; detalhes continuam no log.
- Dependências de deploy foram reduzidas e configuração passou para variáveis de ambiente.
- Configuração de produção recebeu cookies seguros, HSTS, CSP-adjacent headers do Django/WhiteNoise, PostgreSQL via `DATABASE_URL` e logging.
- Backups contendo dados pessoais foram removidos do pacote de entrega.
- Arquivos/rotas legadas quebradas relacionados à câmera e redefinição antiga foram removidos.
- Foi criado pipeline CI com checks, suíte de testes e `check --deploy` em Python 3.12–3.14.

## Validações realizadas nesta entrega

- Compilação estática de todos os módulos Python: OK.
- Verificação de símbolos importados pelas URLs: OK.
- Verificação de referências `reverse()`/`redirect()` contra nomes de URL: OK.
- Verificação de `{% url %}` em templates contra nomes de URL: OK.
- Verificação das importações relativas locais: OK.
- Revisão de referências legadas de câmera/redefinição: removidas.

## Limitação do ambiente de auditoria

O ambiente usado para esta revisão não possuía Django instalado e não tinha acesso à internet para baixar as dependências. Por isso, não foi possível executar `python manage.py test` nesta máquina. A suíte foi ampliada e o CI do projeto foi configurado para executar os testes com as dependências reais.

Antes de publicar a versão final, execute:

```bash
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py check
python manage.py check --deploy
python manage.py test
python manage.py collectstatic --no-input
```


## Melhorias de produto adicionadas nesta revisão

- Landing page reformulada com UX responsivo e busca pública por escola.
- CTA do mural público corrigido para não apontar para uma URL sem `escola_id`.
- Integração Telegram multi-escola: um bot por escola, vários destinos por bot e pareamento por link.
- Token do bot cifrado no banco; código de pareamento é armazenado somente como hash e expira em 10 minutos.
- Webhook autenticado com `X-Telegram-Bot-Api-Secret-Token`.
- Alertas de reservas, aprovações, fichas ausentes, notebooks quebrados, divergências e reservas fixas direcionados para a escola correta.
- Painel administrativo dedicado para conectar, testar, parear e remover destinos Telegram.
