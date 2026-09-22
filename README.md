<div align="center">

# 🚀 Reserva de Carrinhos Escolares

Sistema web para consultar a disponibilidade e organizar reservas de carrinhos de notebooks para uso em aulas.

[![Python](https://img.shields.io/badge/Python-3.x-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.x-092E20?logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Status](https://img.shields.io/badge/status-em%20desenvolvimento-yellow)](#)

</div>

## Sobre o projeto

Em ambientes escolares, pode ser difícil identificar rapidamente quais carrinhos estão disponíveis, em uso ou reservados. Este projeto centraliza essas informações em uma aplicação web, tornando o controle mais organizado e prático para professores e responsáveis.

## Funcionalidades

- Consulta da disponibilidade dos carrinhos;
- Registro e controle de reservas;
- Identificação de carrinhos disponíveis, em uso ou reservados;
- Organização dos equipamentos em um sistema único;
- Interface web para facilitar a consulta e o gerenciamento.

## Tecnologias

- **Backend:** Python e Django
- **Frontend:** HTML, CSS e JavaScript
- **Banco de dados:** integração via Django ORM
- **Versionamento:** Git e GitHub
- **Deploy:** configuração preparada para ambiente de hospedagem

## Executando localmente

### Pré-requisitos

- Python 3.10 ou superior;
- Git;
- Pip.

### Instalação

```bash
git clone https://github.com/Antonny234/Projeto-Reservar_carrinhos_escola.git
cd Projeto-Reservar_carrinhos_escola
python -m venv venv
```

Ative o ambiente virtual:

```bash
# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate
```

Instale as dependências e execute as migrações:

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Abra no navegador: `http://127.0.0.1:8000/`

## Aprendizados

Este projeto foi desenvolvido para praticar a criação de uma aplicação Django completa, organização de aplicações e modelos, desenvolvimento de uma solução para um problema real, versionamento com Git e preparação para deploy.

## Próximos passos

- [ ] Implementar autenticação de usuários;
- [ ] Criar níveis de acesso para diferentes perfis;
- [ ] Adicionar calendário de reservas;
- [ ] Criar testes automatizados;
- [ ] Melhorar a interface e a experiência do usuário;
- [ ] Adicionar documentação visual com capturas de tela.

## Autor

**Antonny Gabriel** — [@Antonny234](https://github.com/Antonny234)

Este projeto faz parte do meu portfólio de estudos em Python e Django.
