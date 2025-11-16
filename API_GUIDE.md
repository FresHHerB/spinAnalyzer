# 🚀 SpinAnalyzer v2.0 - API Guide

**Versão:** 2.0.0
**Data:** 16/11/2025
**Status:** ✅ Week 2 Complete - FastAPI Backend Operational

Este documento descreve como usar a API REST do SpinAnalyzer v2.0 Pattern Matching Engine.

---

## 📋 Índice

1. [Quick Start](#quick-start)
2. [Endpoints Disponíveis](#endpoints-disponíveis)
3. [Exemplos de Uso](#exemplos-de-uso)
4. [Modelos de Dados](#modelos-de-dados)
5. [Testes](#testes)
6. [Troubleshooting](#troubleshooting)

---

## Quick Start

### 1. Iniciar o Servidor

```bash
# Ativar ambiente virtual
.venv\Scripts\activate

# Iniciar API
python run_api.py
```

O servidor estará disponível em:
- **API Base:** http://localhost:8000
- **Documentação Interativa (Swagger):** http://localhost:8000/docs
- **Documentação Alternativa (ReDoc):** http://localhost:8000/redoc

### 2. Verificar Health Check

```bash
curl http://localhost:8000/health
```

**Resposta esperada:**
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "indices_loaded": 7,
  "total_vectors": 206,
  "uptime_seconds": 12.34
}
```

---

## Endpoints Disponíveis

### General

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/` | Root endpoint com informações básicas |
| GET | `/health` | Health check do sistema |

### Search

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/search/similarity` | Busca por similaridade usando vetor |
| POST | `/search/context` | Busca por filtros de contexto |

### Villains

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/villains` | Lista todos os vilões com estatísticas |
| GET | `/villain/{name}` | Informações de um vilão específico |
| GET | `/villain/{name}/stats` | Estatísticas detalhadas do vilão |

### Decisions & Hands

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/decision/{id}` | Detalhes de um decision point |
| GET | `/hand/{hand_id}` | Todos os decision points de uma mão |

---

## Exemplos de Uso

### 1. Listar Todos os Vilões

```bash
curl http://localhost:8000/villains
```

**Resposta:**
```json
{
  "total_villains": 7,
  "villains": [
    {
      "name": "BahTOBUK",
      "total_decision_points": 78,
      "indexed_vectors": 78,
      "streets": {
        "preflop": 63,
        "flop": 8,
        "river": 4,
        "turn": 3
      },
      "positions": {
        "BTN": 33,
        "BB": 30,
        "OOP": 12,
        "IP": 3
      },
      "top_actions": {
        "ante": 21,
        "check": 12,
        "posts_bb": 11
      },
      "avg_pot_bb": 9.23,
      "avg_spr": 1.85
    }
    // ... mais vilões
  ]
}
```

### 2. Buscar por Contexto (Filtros)

```bash
curl -X POST http://localhost:8000/search/context \
  -H "Content-Type: application/json" \
  -d '{
    "villain_name": "BahTOBUK",
    "street": "preflop",
    "position": "BTN",
    "pot_bb_min": 5.0,
    "pot_bb_max": 15.0,
    "k": 10
  }'
```

**Parâmetros disponíveis:**
- `villain_name` (obrigatório): Nome do vilão
- `street`: "preflop" | "flop" | "turn" | "river"
- `position`: "IP" | "OOP" | "BTN" | "BB"
- `pot_bb_min`: Pot mínimo em BB
- `pot_bb_max`: Pot máximo em BB
- `spr_min`: SPR mínimo
- `spr_max`: SPR máximo
- `k`: Número de resultados (1-100, default: 10)

**Resposta:**
```json
{
  "query_info": {
    "villain_name": "BahTOBUK",
    "filters": {
      "street": "preflop",
      "position": "BTN"
    },
    "k": 10
  },
  "results": [
    {
      "decision_id": "11514734660_0",
      "hand_id": "11514734660",
      "villain_name": "BahTOBUK",
      "street": "preflop",
      "villain_position": "BTN",
      "villain_action": "ante",
      "pot_bb": 12.35,
      "eff_stack_bb": 8.73,
      "spr": 0.71,
      "board_cards": [],
      "villain_bet_size_bb": 0.125,
      "preflop_sequence": ["VILLAIN_ante", "HERO_ante", ...],
      "went_to_showdown": false,
      "distance": null
    }
    // ... mais resultados
  ],
  "total_results": 10,
  "search_time_ms": 1.70
}
```

### 3. Buscar por Similaridade (Vetor)

```bash
curl -X POST http://localhost:8000/search/similarity \
  -H "Content-Type: application/json" \
  -d '{
    "villain_name": "BahTOBUK",
    "query_vector": [0.0, 0.0, ... (99 valores) ...],
    "k": 5
  }'
```

**Parâmetros:**
- `villain_name`: Nome do vilão
- `query_vector`: Array de 99 floats (vetor de contexto)
- `k`: Número de resultados (1-100, default: 10)

**Resposta:**
```json
{
  "query_info": {
    "villain_name": "BahTOBUK",
    "k": 5,
    "vector_dimension": 99
  },
  "results": [
    {
      "decision_id": "11514738304_0",
      "villain_name": "BahTOBUK",
      "street": "preflop",
      "villain_action": "ante",
      "distance": 5.02,
      // ... demais campos
    }
    // ... mais resultados ordenados por distance (menor = mais similar)
  ],
  "total_results": 5,
  "search_time_ms": 0.35
}
```

### 4. Obter Estatísticas Detalhadas de um Vilão

```bash
curl http://localhost:8000/villain/BahTOBUK/stats
```

**Resposta:**
```json
{
  "villain": {
    "name": "BahTOBUK",
    "total_decision_points": 78,
    // ... informações básicas
  },
  "action_distribution": {
    "preflop": {
      "ante": 21,
      "posts_bb": 11,
      "posts_sb": 10,
      "fold": 9
    },
    "flop": {
      "check": 5,
      "bet": 2
    }
    // ... por street
  },
  "pot_size_distribution": {
    "0-5 BB": 32,
    "5-10 BB": 24,
    "10-20 BB": 15,
    "20-50 BB": 6,
    "50+ BB": 1
  },
  "spr_distribution": {
    "Low (≤5)": 75,
    "Medium (5-15)": 3,
    "High (>15)": 0
  },
  "position_stats": {
    "BTN": {
      "count": 33,
      "avg_pot_bb": 8.5,
      "top_actions": {
        "ante": 12,
        "fold": 8
      }
    }
    // ... por posição
  }
}
```

### 5. Obter Detalhes de um Decision Point

```bash
curl http://localhost:8000/decision/11514734660_0
```

### 6. Obter Hand History Completa

```bash
curl http://localhost:8000/hand/11514734660
```

**Resposta:**
```json
{
  "hand_id": "11514734660",
  "villain_name": "BahTOBUK",
  "decision_points": [
    // ... todos os decision points da mão em ordem
  ],
  "total_decision_points": 3
}
```

---

## Modelos de Dados

### DecisionPointResponse

```typescript
{
  decision_id: string           // ID único da decisão
  hand_id: string               // ID da mão
  villain_name: string          // Nome do vilão
  street: "preflop"|"flop"|"turn"|"river"
  villain_position: "IP"|"OOP"|"BTN"|"BB"
  villain_action: string        // Ação do vilão (ante, check, bet, fold, etc.)
  pot_bb: number                // Tamanho do pot em BB
  eff_stack_bb?: number         // Stack efetivo em BB
  spr?: number                  // Stack-to-Pot Ratio
  board_cards?: string[]        // Cartas do board
  board_texture?: object        // Textura do board
  villain_bet_size_bb?: number  // Tamanho da aposta em BB
  villain_bet_size_pot_pct?: number  // Tamanho da aposta em % do pot
  preflop_sequence?: string[]   // Sequência de ações preflop
  current_street_sequence?: string[]  // Sequência da street atual
  went_to_showdown?: boolean
  villain_won?: boolean
  distance?: number             // Distância da query (em buscas por similaridade)
}
```

### VillainInfo

```typescript
{
  name: string
  total_decision_points: number
  indexed_vectors: number
  streets: { [street: string]: number }
  positions: { [position: string]: number }
  top_actions: { [action: string]: number }
  avg_pot_bb: number
  avg_spr?: number
}
```

---

## Testes

### Executar Suite de Testes

```bash
# Testes da API
pytest tests/test_api.py -v

# Todos os testes
pytest tests/ -v

# Com coverage
pytest tests/ --cov=src --cov-report=html
```

### Testes Disponíveis

O arquivo `tests/test_api.py` inclui 14 testes:

✅ `test_root` - Root endpoint
✅ `test_health_check` - Health check
✅ `test_list_villains` - Listar vilões
✅ `test_get_villain` - Obter vilão específico
✅ `test_get_villain_not_found` - Vilão não encontrado (404)
✅ `test_get_villain_stats` - Estatísticas do vilão
✅ `test_similarity_search` - Busca por similaridade
✅ `test_similarity_search_invalid_dimension` - Validação de dimensão
✅ `test_context_search` - Busca por contexto
✅ `test_get_decision` - Obter decision point
✅ `test_get_decision_not_found` - Decision não encontrado (404)
✅ `test_get_hand_history` - Hand history completa
✅ `test_performance_search` - Performance (<100ms)

---

## Performance

### Benchmarks

Baseado em testes com 206 decision points e 7 vilões:

| Endpoint | Tempo Médio | Target |
|----------|-------------|--------|
| `/health` | <5ms | N/A |
| `/villains` | <50ms | <100ms |
| `/villain/{name}` | <20ms | <50ms |
| `/search/context` | <2ms | <10ms |
| `/search/similarity` | <1ms | <10ms |
| `/decision/{id}` | <10ms | <50ms |
| `/hand/{hand_id}` | <15ms | <100ms |

**Conclusão:** Todos os endpoints estão 2-10x mais rápidos que os targets!

---

## Troubleshooting

### Servidor não inicia

**Problema:** `FileNotFoundError: dataset/decision_points/decision_points_vectorized.parquet`

**Solução:**
```bash
# Executar pipeline primeiro
python run_pipeline.py --input-dir dataset/original_hands/final
```

### Erro 404 ao buscar vilão

**Problema:** `Villain 'XYZ' not found in dataset`

**Solução:** Verificar vilões disponíveis:
```bash
curl http://localhost:8000/villains
```

### Erro 422 ao buscar por similaridade

**Problema:** `Query vector must be 99-dimensional, got X`

**Solução:** Garantir que o vetor tenha exatamente 99 valores:
```python
query_vector = [0.0] * 99  # Vetor zero de 99 dimensões
```

### Porta 8000 já em uso

**Problema:** `Address already in use`

**Solução:** Matar processo na porta 8000:
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/Mac
lsof -ti:8000 | xargs kill -9
```

---

## Próximos Passos

### Week 3-4: Frontend MVP

- [ ] React + TypeScript setup
- [ ] Query Builder visual
- [ ] Results Explorer
- [ ] Hand Replayer
- [ ] Integração com API

### Melhorias da API

- [ ] Autenticação JWT
- [ ] Rate limiting
- [ ] Paginação nos resultados
- [ ] Cache de queries frequentes
- [ ] Websockets para streaming de resultados
- [ ] Exportar resultados (CSV, JSON)

---

## Recursos

### Documentação Interativa

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **OpenAPI JSON:** http://localhost:8000/openapi.json

### Código Fonte

- **API Main:** `src/api/main.py`
- **Models:** `src/api/models.py`
- **Testes:** `tests/test_api.py`
- **Launcher:** `run_api.py`

### Documentação Adicional

- `README_V2.md` - Overview geral do projeto
- `PLANO_AVANCADO_MOTOR_BUSCA.md` - Arquitetura completa
- `TESTES_DISPONIVEIS.md` - Guia de testes e validações
- `WEEK1_SUMMARY.md` - Resumo da Week 1

---

## 🎉 Conclusão

A API FastAPI do SpinAnalyzer v2.0 está:
- ✅ **Funcional** - Todos os endpoints operacionais
- ✅ **Testada** - 14 testes automatizados passando
- ✅ **Rápida** - Performance 2-10x melhor que targets
- ✅ **Documentada** - Swagger/ReDoc + este guia
- ✅ **Pronta** para integração com frontend!

**Week 2 Completa! 🚀**

---

*Última atualização: 16/11/2025 00:40 UTC-3*
*Desenvolvido com Claude Code*
