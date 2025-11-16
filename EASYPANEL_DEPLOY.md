# Deploy SpinAnalyzer no Easypanel

## Visão Geral

Este projeto está configurado para deploy completo (backend + frontend) no Easypanel com um único clique.

## Pré-requisitos

- Conta no Easypanel
- Repositório GitHub: https://github.com/FresHHerB/spinAnalyzer

## Deploy Automático

### 1. Criar Novo Projeto no Easypanel

1. Acesse seu painel Easypanel
2. Clique em "Create New Project"
3. Nome do projeto: `spinanalyzer`

### 2. Adicionar Serviço Backend

1. Clique em "Add Service" → "App"
2. Configurações:
   - **Name:** `backend`
   - **Source:** GitHub Repository
   - **Repository:** `FresHHerB/spinAnalyzer`
   - **Branch:** `master`
   - **Build Method:** Dockerfile
   - **Dockerfile Path:** `./Dockerfile`
   - **Port:** `8000`

3. Variáveis de Ambiente:
   ```
   PYTHONUNBUFFERED=1
   LOG_LEVEL=INFO
   ```

4. Domínio (opcional):
   - Configure domínio customizado para API
   - Exemplo: `api.spinanalyzer.com`

### 3. Adicionar Serviço Frontend

1. Clique em "Add Service" → "App"
2. Configurações:
   - **Name:** `frontend`
   - **Source:** GitHub Repository
   - **Repository:** `FresHHerB/spinAnalyzer`
   - **Branch:** `master`
   - **Build Method:** Dockerfile
   - **Dockerfile Path:** `./frontend/Dockerfile`
   - **Port:** `80`

3. Variáveis de Ambiente:
   ```
   VITE_API_URL=https://api.spinanalyzer.com  # URL do backend
   ```

4. Domínio:
   - Configure domínio principal
   - Exemplo: `spinanalyzer.com`

### 4. Volumes (Persistência de Dados)

Para o serviço **backend**, adicione volumes:

1. Volume para dados:
   - **Mount Path:** `/app/dataset`
   - **Type:** Persistent Volume

2. Volume para índices:
   - **Mount Path:** `/app/indices`
   - **Type:** Persistent Volume

3. Volume para uploads:
   - **Mount Path:** `/app/uploads`
   - **Type:** Persistent Volume

## Deploy com docker-compose

Alternativamente, use o arquivo `docker-compose.yml`:

```bash
# No Easypanel terminal
docker-compose up -d
```

## Primeira Execução

Após o deploy, o sistema estará disponível mas sem dados:

1. **Acesse o frontend:** `https://spinanalyzer.com`
2. **Vá para /upload**
3. **Faça upload de arquivos** .txt (PokerStars) ou .xml (iPoker)
4. **O sistema processará automaticamente** e criará os índices

## Estrutura de Diretórios

```
/app/
├── src/                    # Código fonte (read-only)
├── dataset/                # Dados persistentes (volume)
│   ├── phh_hands/         # Hand histories convertidas
│   └── decision_points/   # Decision points vetorizados
├── indices/               # Índices FAISS (volume)
└── uploads/               # Arquivos uploaded (volume)
    ├── temp/
    └── processed/
```

## Variáveis de Ambiente

### Backend

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `PYTHONUNBUFFERED` | `1` | Logs em tempo real |
| `LOG_LEVEL` | `INFO` | Nível de logging |
| `PORT` | `8000` | Porta do servidor |

### Frontend

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `VITE_API_URL` | `http://localhost:8000` | URL do backend |

## Health Checks

O Easypanel monitorará automaticamente:

**Backend:**
```
GET http://localhost:8000/health
Interval: 30s
Timeout: 10s
```

**Frontend:**
```
GET http://localhost/
Interval: 30s
Timeout: 10s
```

## Endpoints Disponíveis

Após deploy, os seguintes endpoints estarão disponíveis:

| Endpoint | Descrição |
|----------|-----------|
| `GET /` | Informações da API |
| `GET /health` | Status da aplicação |
| `GET /docs` | Documentação Swagger |
| `GET /villains` | Lista de vilões indexados |
| `POST /upload/file` | Upload de arquivo |
| `POST /search/context` | Busca contextual |
| `POST /search/range-analysis` | Análise de range |

## Monitoramento

### Logs

```bash
# Backend logs
easypanel logs backend

# Frontend logs
easypanel logs frontend
```

### Métricas

Acesse o painel Easypanel para ver:
- CPU usage
- Memory usage
- Network traffic
- Request count

## Backup

### Backup Manual

```bash
# Backup de dados
docker cp backend:/app/dataset ./backup/dataset
docker cp backend:/app/indices ./backup/indices
```

### Backup Automático (Easypanel)

Configure backups automáticos nos volumes:
1. Vá em "Volumes"
2. Selecione volume
3. Enable "Auto Backup"
4. Configure frequência

## Troubleshooting

### Backend não inicia

1. Verifique logs: `easypanel logs backend`
2. Confirme que portas estão corretas
3. Verifique variáveis de ambiente

### Frontend não conecta ao backend

1. Verifique `VITE_API_URL` está correto
2. Teste endpoint: `curl https://api.spinanalyzer.com/health`
3. Verifique CORS no backend

### Dados não persistem

1. Confirme volumes estão montados corretamente
2. Verifique permissões: `docker exec backend ls -la /app/dataset`

### Build falha

1. Verifique Dockerfile syntax
2. Confirme `requirements.txt` está correto
3. Veja build logs no Easypanel

## Atualizações

Para atualizar o sistema:

1. **Push para GitHub:**
   ```bash
   git push origin master
   ```

2. **Easypanel detecta automaticamente** e reconstrói
   - Webhook configurado automaticamente
   - Zero downtime deployment

3. **Ou manualmente:**
   - Vá em "Services" → "Rebuild"

## Rollback

Se houver problemas após atualização:

1. Vá em "Deployments"
2. Selecione deployment anterior
3. Clique em "Rollback"

## Scaling

### Horizontal Scaling

```yaml
# Adicione réplicas no Easypanel
services:
  backend:
    deploy:
      replicas: 3
```

### Vertical Scaling

1. Vá em "Services" → "Resources"
2. Ajuste CPU e Memory limits

## SSL/HTTPS

O Easypanel configura SSL automaticamente:
- Let's Encrypt certificates
- Auto-renewal
- HTTP → HTTPS redirect

## Custos Estimados

| Recurso | Uso | Custo/mês |
|---------|-----|-----------|
| CPU | 1 vCPU | $5-10 |
| Memory | 2 GB RAM | $5-10 |
| Storage | 10 GB | $1-2 |
| **Total** | - | **$11-22** |

## Suporte

- Issues: https://github.com/FresHHerB/spinAnalyzer/issues
- Docs: Ver DEPLOYMENT.md e UPLOAD_SYSTEM.md
- Easypanel Docs: https://easypanel.io/docs

## Checklist de Deploy

- [ ] Repositório GitHub configurado
- [ ] Dockerfile testado localmente
- [ ] Variáveis de ambiente definidas
- [ ] Volumes configurados para persistência
- [ ] Domínios configurados
- [ ] SSL habilitado
- [ ] Health checks funcionando
- [ ] Logs monitorados
- [ ] Backup configurado
- [ ] Primeiro upload testado

---

**Deploy completo em ~5 minutos!** 🚀
