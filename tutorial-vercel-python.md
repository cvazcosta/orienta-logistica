# Tutorial: Como Configurar Funções Serverless em Python no Vercel

Este tutorial abrangente irá guiá-lo através do processo de configuração de funções serverless em Python no Vercel, fornecendo todas as informações necessárias para ajudar um agente de IA a configurar corretamente uma função Python no seu build.

## 1. Introdução às Funções Serverless no Vercel

O Vercel suporta funções serverless em Python através do runtime `@vercel/python`, permitindo executar código Python sem gerenciar servidores. As funções se adaptam automaticamente à demanda do usuário e escalam para zero quando não há requisições.

### Versões Python Suportadas
- **Python 3.12** (padrão)
- **Python 3.9** (requer imagem legacy)

## 2. Estrutura Básica do Projeto

### Estrutura de Diretórios
```
meu-projeto/
├── api/
│   └── index.py          # Função principal
├── requirements.txt      # Dependências Python
├── vercel.json          # Configuração do Vercel (opcional)
└── package.json         # Para configurações de Node.js (se necessário)
```

### Pasta `/api`
- **Todas as funções Python devem estar na pasta `/api`**
- Cada arquivo `.py` na pasta `/api` se torna uma função serverless
- O caminho do arquivo determina a rota: `/api/hello.py` → `/api/hello`

## 3. Criando sua Primeira Função Python

### Exemplo Básico (`api/index.py`)
```python
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write('Hello, World!'.encode('utf-8'))
        return
    
    def do_POST(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write('{"message": "POST recebido!"}'.encode('utf-8'))
        return
```

### Exemplo com Flask (`api/index.py`)
```python
from flask import Flask, jsonify

app = Flask(__name__)

@app.route("/")
def home():
    return "Flask Vercel Example - Hello World", 200

@app.route("/api/users")
def users():
    return jsonify({"users": ["João", "Maria", "Pedro"]})

@app.errorhandler(404)
def page_not_found(e):
    return jsonify({"status": 404, "message": "Not Found"}), 404

# Para Vercel
if __name__ == "__main__":
    app.run()
```

## 4. Gerenciamento de Dependências

### requirements.txt
```txt
Flask==3.0.3
requests==2.31.0
python-dateutil==2.8.2
```

### Pipfile (Para Especificar Versão Python)
```toml
[[source]]
url = "https://pypi.org/simple"
verify_ssl = true
name = "pypi"

[packages]
flask = "*"

[requires]
python_version = "3.12"
```

## 5. Configuração Avançada com vercel.json

### Configuração Básica
```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "functions": {
    "api/**/*.py": {
      "memory": 1024,
      "maxDuration": 30
    }
  }
}
```

### Configuração Completa
```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "builds": [
    {
      "src": "api/index.py",
      "use": "@vercel/python",
      "config": {
        "maxLambdaSize": "15mb",
        "runtime": "python3.12"
      }
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "api/index.py"
    }
  ],
  "functions": {
    "api/**/*.py": {
      "memory": 1024,
      "maxDuration": 30
    }
  }
}
```

### Para Flask com Rewrite
```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "rewrites": [
    {
      "source": "/(.*)",
      "destination": "/api/index"
    }
  ]
}
```

## 6. Configuração de Versão Python 3.9

### package.json (Para Python 3.9)
```json
{
  "engines": {
    "node": "18.x"
  }
}
```

### Pipfile (Para Python 3.9)
```toml
[requires]
python_version = "3.9"
```

## 7. Deploy e Configuração

### Usando Vercel CLI
```bash
# Instalar Vercel CLI
npm install -g vercel

# Login
vercel login

# Deploy
vercel --prod
```

### Configurações no Dashboard
1. **Root Directory**: Deixe vazio se o projeto está na raiz
2. **Build Command**: Pode deixar vazio para projetos Python simples
3. **Install Command**: Pode deixar vazio (Vercel detecta automaticamente)
4. **Node.js Version**: 18.x (para Python 3.9) ou 20.x/22.x (para Python 3.12)

## 8. Estruturas de Projeto Avançadas

### Projeto com Django
```
projeto-django/
├── api/
│   └── index.py         # WSGI handler
├── meu_app/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── requirements.txt
└── vercel.json
```

### WSGI Handler para Django (`api/index.py`)
```python
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'meu_app.settings')

application = get_wsgi_application()
app = application  # Para Vercel
```

### Projeto com FastAPI
```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello World"}

@app.get("/api/users/{user_id}")
def read_user(user_id: int):
    return {"user_id": user_id}
```

## 9. Boas Práticas e Dicas Importantes

### Organização de Arquivos
- **Funções utilitárias**: Use arquivos que começam com `_` (ex: `_utils.py`) - não se tornam rotas
- **Tipos TypeScript**: Arquivos `.d.ts` são ignorados
- **Arquivos de configuração**: Arquivos que começam com `.` são ignorados

### Importações
```python
# Para importar módulos da pasta api
from api.utils import helper_function

# Para importações relativas (mesmo diretório)
from .database import db_connection
```

### Variáveis de Ambiente
```python
import os

# Acessar variáveis de ambiente
DATABASE_URL = os.environ.get('DATABASE_URL')
API_KEY = os.environ.get('API_KEY')
```

### Tratamento de Erros
```python
def handler(request):
    try:
        # Seu código aqui
        return {"success": True}
    except Exception as e:
        return {
            "error": str(e),
            "status": 500
        }
```

## 10. Troubleshooting Comum

### Problema: ModuleNotFoundError
**Solução**: Certifique-se de que:
- Arquivos `__init__.py` existem nas pastas que devem ser módulos
- Imports estão corretos (`from api.module import func`)
- Estrutura de pastas está correta

### Problema: Versão Python Incorreta
**Solução**: 
- Use `Pipfile` para especificar a versão
- Configure Node.js corretamente (18.x para Python 3.9)

### Problema: Dependências não Instaladas
**Solução**:
- Verifique o `requirements.txt`
- Use versões específicas (ex: `Flask==3.0.3`)
- Evite dependências que requerem compilação nativa

### Problema: Timeout na Função
**Solução**:
- Configure `maxDuration` no `vercel.json`
- Otimize o código para executar mais rapidamente
- Use processamento assíncrono quando possível

## 11. Exemplo Completo Funcional

### Estrutura Final
```
meu-projeto-python/
├── api/
│   ├── index.py
│   ├── users.py
│   └── _utils.py
├── requirements.txt
├── vercel.json
└── README.md
```

### `api/index.py`
```python
from http.server import BaseHTTPRequestHandler
import json

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        response = {
            "message": "API Python funcionando!",
            "status": "success",
            "endpoints": ["/api/users", "/api/"]
        }
        
        self.wfile.write(json.dumps(response).encode('utf-8'))
        return
```

### `api/users.py`
```python
from http.server import BaseHTTPRequestHandler
import json

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        users = [
            {"id": 1, "name": "João"},
            {"id": 2, "name": "Maria"},
            {"id": 3, "name": "Pedro"}
        ]
        
        self.wfile.write(json.dumps({"users": users}).encode('utf-8'))
        return
```

### `requirements.txt`
```txt
requests==2.31.0
```

### `vercel.json`
```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "functions": {
    "api/**/*.py": {
      "memory": 1024,
      "maxDuration": 30
    }
  }
}
```

## 12. Comandos de Deploy

```bash
# Deploy inicial
vercel

# Deploy para produção
vercel --prod

# Ver logs
vercel logs

# Baixar variáveis de ambiente para desenvolvimento
vercel env pull
```

## Conclusão

Este tutorial fornece uma base sólida para configurar funções serverless em Python no Vercel. Lembre-se de que:

1. **Estrutura é fundamental**: Sempre use a pasta `/api`
2. **Dependências claras**: Mantenha `requirements.txt` atualizado
3. **Configuração apropriada**: Use `vercel.json` para customizações
4. **Testes locais**: Use `vercel dev` para testar localmente
5. **Monitoramento**: Acompanhe logs e performance após deploy

Com essas informações, você ou um agente de IA podem configurar com sucesso funções Python no Vercel!