# Reserva de Carrinhos Escolares

Sistema web desenvolvido para ajudar professores e responsáveis a consultar a disponibilidade e reservar carrinhos de notebooks para uso em aulas.

> **Status:** projeto acadêmico/prático em evolução.

## Sobre o projeto

Em uma escola, pode ser difícil saber quais carrinhos estão em uso, disponíveis ou reservados. Este projeto organiza essas informações em um único sistema, facilitando o controle das reservas e a visualização da disponibilidade dos equipamentos.

## Funcionalidades

- Consulta de carrinhos disponíveis;
- Controle de reservas para aulas;
- Identificação de carrinhos em uso ou reservados;
- Organização das informações dos equipamentos;
- Interface web para facilitar o uso por professores e responsáveis.

## Tecnologias

- Python
- Django
- HTML
- CSS
- JavaScript
- Banco de dados integrado ao Django

## Como executar localmente

### 1. Clone o repositório

```bash
git clone https://github.com/Antonny234/Projeto-Reservar_carrinhos_escola.git
cd Projeto-Reservar_carrinhos_escola
```

### 2. Crie e ative um ambiente virtual

```bash
python -m venv venv
```

No Windows:

```bash
venv\Scripts\activate
```

No Linux/macOS:

```bash
source venv/bin/activate
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Execute as migrações

```bash
python manage.py migrate
```

### 5. Inicie o servidor

```bash
python manage.py runserver
```

Acesse `http://127.0.0.1:8000/` no navegador.

## O que aprendi

- Estruturação de um projeto Django;
- Organização de aplicações e modelos;
- Criação de uma solução para um problema real;
- Versionamento do código com Git e GitHub;
- Preparação de uma aplicação para execução e deploy.

## Próximas melhorias

- Adicionar autenticação de usuários;
- Criar diferentes níveis de acesso;
- Implementar calendário de reservas;
- Adicionar testes automatizados;
- Melhorar a documentação e a experiência visual.

## Autor

**Antonny Gabriel**

- GitHub: [@Antonny234](https://github.com/Antonny234)
- Projeto: [Projeto-Reservar_carrinhos_escola](https://github.com/Antonny234/Projeto-Reservar_carrinhos_escola)
