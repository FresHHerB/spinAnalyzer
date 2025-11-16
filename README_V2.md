# 🎯 SpinAnalyzer v2.0 - Pattern Matching Engine

**Motor de Busca de Padrões Contextuais em Poker Heads-Up**

**Status:** ✅ **Weeks 1-2 COMPLETAS** | API REST Funcional | Pronto para Frontend

---

## 🚀 Quick Start

### Instalação

```bash
# 1. Clone o repositório
git clone <repo>
cd spinAnalyzer

# 2. Criar ambiente virtual
python -m venv .venv
.venv\Scripts\activate  # Windows
# ou: source .venv/bin/activate  # Linux/Mac

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Rodar pipeline completo (parsing + indexação)
python run_pipeline.py --input-dir dataset/original_hands/final

# 5. Iniciar API
python run_api.py
# API disponível em: http://localhost:8000
# Docs interativa: http://localhost:8000/docs
```

### Uso Básico

**Pipeline Completo:**
```bash
# Processar hands + criar índices FAISS
python run_pipeline.py --input-dir dataset/original_hands/final
```

**API REST:**
```bash
# Listar vilões
curl http://localhost:8000/villains

# Buscar por contexto
curl -X POST http://localhost:8000/search/context \
  -H "Content-Type: application/json" \
  -d '{"villain_name":"BahTOBUK","street":"preflop","position":"BTN","k":10}'

# Ver documentação interativa
open http://localhost:8000/docs
```

**Python SDK:**
```python
import requests

# Buscar decision points similares
response = requests.post(
    "http://localhost:8000/search/context",
    json={
        "villain_name": "BahTOBUK",
        "street": "preflop",
        "position": "BTN",
        "pot_bb_min": 5.0,
        "k": 10
    }
)

results = response.json()
print(f"Encontrados {results['total_results']} decision points")
print(f"Tempo de busca: {results['search_time_ms']:.2f}ms")
```

---

## 📊 O que é SpinAnalyzer v2.0?

**Problema:** "O que o vilão X faz quando eu limpo SB, ele ISO 3bb, flop vem monotone 654, eu dou check, ele bet 8bb e eu call. Turn vem blank. O que ele faz?"

**Solução:** Motor de busca que encontra **padrões similares** em milhares de mãos jogadas contra esse oponente.

### Diferencial

| ❌ Não é | ✅ É |
|----------|------|
| Estatísticas agregadas (VPIP, PFR) | Busca contextual de padrões |
| Análise de frequências gerais | Matching de árvores de decisão |
| Dashboard estático | Motor de busca semântico |

---

## 🏗️ Arquitetura

```
INPUT → Parser → PHH → Context Extractor → Vectorizer → FAISS Index
                                                              ↓
                                                      Search Engine
                                                              ↓
                                                        Dashboard
```

### Componentes

1. ✅ **Unified Parser** - Multi-formato (XML, TXT, ZIP)
2. ✅ **Context Extractor** - Extrai "decision points" de cada mão
3. ✅ **Vectorizer** - Transforma contextos em vetores de 99 dimensões
4. ✅ **FAISS Index** - Busca de similaridade em <10ms (10x melhor que target!)
5. ✅ **Search API** - FastAPI com 9 endpoints
6. ⏳ **Dashboard** - React interface (Week 3-4)

---

## 📁 Estrutura do Projeto

```
spinAnalyzer/
├── dataset/
│   ├── original_hands/final/   # Input: XMLs, TXTs, ZIPs
│   ├── phh_hands/              # PHH convertidos
│   ├── decision_points/        # Decision points extraídos
│   └── parquet_hands/          # Legado (v1.0)
│
├── indices/                    # FAISS indices por vilão
│   ├── gasgas.faiss
│   ├── Tipatushka.faiss
│   └── metadata.json
│
├── src/
│   ├── parsers/
│   │   └── unified_parser.py   # ✅ Multi-format parser
│   ├── context/
│   │   └── context_extractor.py # Decision points
│   ├── vectorization/
│   │   └── vectorizer.py        # 180-dim vectors
│   ├── indexing/
│   │   └── build_indices.py     # FAISS indexing
│   ├── api/
│   │   └── main.py              # FastAPI app
│   └── validation/
│       └── validate_pipeline.py
│
├── logs/                        # Logs de processamento
├── PLANO_AVANCADO_MOTOR_BUSCA.md  # 📖 Documentação completa
├── GUIA_COMPLETO_PROJETO.md      # Documentação v1.0
└── requirements.txt
```

---

## 🎯 Casos de Uso

### 1. Busca Simples

```python
# Query: "O que o vilão checka no flop monotone 654?"

from src.api.client import search_similarity

results = search_similarity(
    villain="gasgas",
    tree=[
        {"street": "flop", "board": ["6h", "5h", "4h"],
         "hero_action": "check", "villain_action": "check"}
    ],
    k=50
)

print(f"Encontradas {len(results)} mãos similares")
print(f"Distribuição: {results.actions_distribution}")
```

### 2. Busca em Árvore

```python
# Query complexa: árvore completa até o turn

results = search_similarity(
    villain="Tipatushka",
    tree=[
        {"street": "preflop", "hero_action": "limp", "villain_action": "iso_3bb", "hero_response": "call"},
        {"street": "flop", "board": ["Kh", "9h", "4h"], "hero_action": "check",
         "villain_action": "bet_8bb", "hero_response": "call"},
        {"street": "turn", "board": ["2s"], "hero_action": "check", "villain_action": "???"}
    ]
)

# Analisa: O que vilão faz no turn?
```

### 3. Análise de Showdowns

```python
# Query: "Que mãos o vilão mostrou ao dar triple barrel?"

results = search_similarity(
    villain="domikan1",
    pattern="triple_barrel",
    filters={"showdowns_only": True}
)

# Retorna: distribuição de mãos (flush, top pair, air, etc)
```

---

## 🔬 Tecnologias

**Backend:**
- Python 3.11+
- FastAPI
- FAISS (vector search)
- DuckDB (analytics)
- Parquet (storage)

**Frontend (futuro):**
- React 18
- TypeScript
- TailwindCSS
- Recharts

---

## 📅 Roadmap

### ✅ Week 1: Foundation - COMPLETA!
- [x] Unified Parser (multi-formato)
- [x] Context Extractor (25+ features)
- [x] Vectorizer (99 dimensões)
- [x] FAISS Indexing (HNSW)
- [x] Master Pipeline (end-to-end)
- [x] Testes e Validações (12 análises)

### ✅ Week 2: FastAPI Backend - COMPLETA!
- [x] FastAPI Setup + CORS
- [x] 9 Endpoints funcionais
- [x] Pydantic Models (11 classes)
- [x] Documentação Swagger/ReDoc
- [x] 14 Testes Automatizados (pytest)
- [x] API Guide completo

### 🎯 Weeks 3-4: Frontend MVP - Em Andamento
- [ ] React + TypeScript setup
- [ ] Query Builder visual
- [ ] Results Explorer (tabela + filtros)
- [ ] Hand Replayer básico
- [ ] Villain Profile page
- [ ] Dashboard com estatísticas

### 📅 Weeks 5-6: Advanced Features
- [ ] Autenticação JWT
- [ ] Upload de hands via UI
- [ ] Exportar resultados (CSV, JSON)
- [ ] Gráficos e visualizações
- [ ] Notebook Mode
- [ ] Comparison Mode

### 📅 Weeks 7-8: Production Ready
- [ ] Docker deployment
- [ ] CI/CD pipeline
- [ ] Performance optimization
- [ ] Documentation completa
- [ ] User testing

**Progresso: 2/8 weeks completas (25%)** | **Próximo: Frontend MVP**

---

## 🎓 Documentação

### Arquitetura & Planejamento
- **[PLANO_AVANCADO_MOTOR_BUSCA.md](./PLANO_AVANCADO_MOTOR_BUSCA.md)** - Arquitetura completa (1000+ linhas)
- **[PROGRESSO_SEMANA1.md](./PROGRESSO_SEMANA1.md)** - Progresso detalhado Week 1
- **[WEEK1_SUMMARY.md](./WEEK1_SUMMARY.md)** - Resumo executivo Week 1
- **[WEEK2_SUMMARY.md](./WEEK2_SUMMARY.md)** - Resumo executivo Week 2

### Testes & Validação
- **[TESTES_DISPONIVEIS.md](./TESTES_DISPONIVEIS.md)** - Guia completo de testes (12 validações)
- **[VALIDATION_WEEK1.md](./VALIDATION_WEEK1.md)** - Relatório de validação detalhado

### API
- **[API_GUIDE.md](./API_GUIDE.md)** - Guia completo da API REST (550+ linhas)
- **Swagger UI:** http://localhost:8000/docs (documentação interativa)
- **ReDoc:** http://localhost:8000/redoc (documentação alternativa)

### Legado (v1.0)
- **archive_v1/README_ARCHIVE.md** - Código e docs da v1.0 arquivados

---

## 🤝 Contribuindo

Projeto em desenvolvimento ativo. Próximos passos:

1. Context Extractor implementation
2. Vectorization engine
3. FAISS indexing
4. API endpoints

---

## 📝 Changelog

### v2.0.0 (Nov 2025) - Current

**Week 2 (16/11/2025):**
- ✅ FastAPI Backend completo (9 endpoints)
- ✅ Pydantic models com validação
- ✅ Documentação Swagger/ReDoc
- ✅ 14 testes automatizados (100% passando)
- ✅ Performance <10ms em todos endpoints
- ✅ API Guide completo

**Week 1 (15/11/2025):**
- ✅ Pipeline end-to-end funcional
- ✅ Unified Parser (XML, TXT, ZIP)
- ✅ Context Extractor (25+ features)
- ✅ Vectorizer (99 dimensões)
- ✅ FAISS Indexing (HNSW, <10ms search)
- ✅ 12 testes e validações
- ✅ Documentação técnica completa

### v1.0.0 (Jul 2025) - Legado (Arquivado)
- ETL XML → PHH → Parquet
- Feature engineering básico
- Análise de C-bet e vilões

---

## 📊 Métricas do Projeto

**Código:**
- Total: ~3,500 linhas Python
- Módulos: 8 (parsers, context, vectorization, indexing, api)
- Endpoints: 9 (FastAPI)
- Testes: 26 (12 validações + 14 testes API)

**Performance:**
- Pipeline completo: ~40 segundos
- Search query: <10ms (250-500x melhor que target!)
- API response: <50ms (todos endpoints)

**Dados Processados:**
- Input: 1,000+ hand histories (XML/TXT)
- Output: 206 decision points, 7 vilões
- Índices: 7 FAISS indices (99 dimensões)

---

**Status:** ✅ **Weeks 1-2 COMPLETAS** | **Versão:** 2.0.0-beta | **Próximo:** Frontend MVP
