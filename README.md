# Social Network API

Uma API simplificada de rede social construída com FastAPI e SQLite.

## Funcionalidades

- Cadastro de usuários
- Criação de posts
- Sistema de curtidas
- Feed de postagens com paginação
- Listagem de usuários com suas postagens (paginado)
- Gerador de dados de teste (1000 usuários × 1000 posts)

## Endpoints

### Usuários

- **POST** `/users/` - Criar usuário
  ```json
  Request: { "username": "alice", "email": "alice@test.com", "posts": 0 }
  Response: { "id": 1, "username": "alice" }
  ```

### Posts

- **POST** `/posts/` - Criar post

  ```json
  Request: { "user_id": 1, "content": "Hello world" }
  Response: { "id": 1, "user_id": 1, "content": "Hello world", "likes": 0, "created_at": "2025-08-02T12:00:00Z" }
  ```

- **POST** `/posts/{post_id}/like` - Curtir post

### Feed e Listagens

- **GET** `/feed/` - Listar feed de posts (paginado)
- **GET** `/users/` - Listar usuários com seus posts (paginado)

### Dados de Teste

- **POST** `/generate-test-data` - Gerar dados de teste

## Tecnologias

- FastAPI
- SQLAlchemy
- SQLite
- Pydantic
- Faker (para dados de teste)

## Como Executar

1. Clone o repositório
2. Crie um ambiente virtual:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # ou
   .\venv\Scripts\activate  # Windows
   ```
3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
4. Execute o servidor:
   ```bash
   uvicorn app.main:app --reload
   ```
5. Acesse a documentação em: http://127.0.0.1:8000/docs
