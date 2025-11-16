# 🚀 PLANO AVANÇADO - Motor de Busca de Padrões Contextuais

**SpinAnalyzer v2.0 - Pattern Matching Engine**

---

## 📋 ÍNDICE

1. [Visão Geral do Sistema](#1-visão-geral-do-sistema)
2. [Análise dos Dados Atuais](#2-análise-dos-dados-atuais)
3. [Arquitetura Proposta](#3-arquitetura-proposta)
4. [Modelagem de Contextos](#4-modelagem-de-contextos)
5. [Motor de Busca por Similaridade](#5-motor-de-busca-por-similaridade)
6. [Query Language & Interface](#6-query-language--interface)
7. [Dashboard Moderna](#7-dashboard-moderna)
8. [Pipeline de Implementação](#8-pipeline-de-implementação)
9. [Tecnologias e Stack](#9-tecnologias-e-stack)
10. [Roadmap de Desenvolvimento](#10-roadmap-de-desenvolvimento)

---

## 1. VISÃO GERAL DO SISTEMA

### 1.1. Objetivo Central

**Motor de busca semântico e contextual** que encontra padrões similares em árvores de decisão de poker, respondendo perguntas do tipo:

```
❓ "Em limped pot → Vilão ISO → Flop monotone 654 → Vilão check → O que ele checka aqui?"
❓ "Vilão deu 3 barrels → Turn abriu FD → River blank → O que ele tem quando dá 3 barrels?"
❓ "Hero limpa SB → Vilão ISO BB → Hero call → FD abre no turn → O que vilão faz com FD? Com air?"
```

### 1.2. Diferencial Fundamental

| ❌ Não é | ✅ É |
|----------|------|
| Estatísticas agregadas (VPIP, PFR, C-bet%) | Busca por padrões contextuais específicos |
| Análise de frequências gerais | Matching de árvores de decisão similares |
| Dashboard de stats estáticos | Motor de busca semântico interativo |

### 1.3. Casos de Uso Práticos

**Exemplo 1: Query Simples**
```
INPUT: "Flop monotone 654, vilão check"
OUTPUT: 15 mãos similares onde vilão checkou
  ├─ 8 mãos: tinha air (top card Q ou menor)
  ├─ 4 mãos: tinha pair fraco (66, 55, 44)
  └─ 3 mãos: tinha flush draw
```

**Exemplo 2: Query em Árvore**
```
TREE:
  Preflop: Hero limp SB → Vilão ISO 3bb BB → Hero call
  Flop: [Kh 9h 4h] (monotone) → Hero check → Vilão bet 5bb → Hero call
  Turn: [2s] (blank) → Hero check → Vilão ???

QUERY: "O que vilão faz no turn após Hero call flop?"
OUTPUT: 23 mãos similares
  ├─ 12 mãos (52%): Check-behind (give-up)
  ├─ 8 mãos (35%): Bet turn (barrel)
  └─ 3 mãos (13%): Check-raise turn

  └─ Showdowns:
      ├─ Checks: 7 mãos com air, 3 com made hand
      ├─ Bets: 5 mãos com flush, 2 com air, 1 com top pair
      └─ Raises: todas tinham flush ou overpair
```

**Exemplo 3: Query com Cartas Conhecidas**
```
QUERY: "Vilão deu 3 barrels em board [Ah Kd 7c][3s][2h], que mãos ele mostrou?"
OUTPUT: 4 mãos com triple barrel nesse tipo de board
  ├─ 2 mãos: Ax (top pair+)
  ├─ 1 mão: Flush draw que perdeu
  └─ 1 mão: Air total (bluff)

  INSIGHT: Vilão é capaz de triple barrel bluff (25% das vezes)
```

---

## 2. ANÁLISE DOS DADOS ATUAIS

### 2.1. Estrutura dos Parquets Existentes

**Arquivo: `hands.parquet` (134 mãos)**
```
Colunas: hand_id, players, winners
Nível: Mão completa
Uso: Metadata e lookup
```

**Arquivo: `actions_raw.parquet` (1026 ações)**
```
Colunas principais:
├─ hand_id, step_idx
├─ player, street, action_type
├─ amount_bb, pot_bb_before, eff_stack_bb_before
├─ board_cards, hole_cards_known, hole_cards_real
└─ Uso: Sequência cronológica de ações

PROBLEMA: Formato "flat" dificulta busca por padrões
SOLUÇÃO: Transformar em grafo/árvore de decisão
```

**Arquivo: `street_features.parquet` (1026 ações)**
```
Colunas ricas (30 features):
├─ Contexto: street, in_position, spr, pot_bb_before
├─ Board: board_comp, paired_board, board_high, board_tex_bucket
├─ Hand Strength: hand_strength_lbl, kicker1/2/3
├─ Draws: fd_flag, oe_flag, gs_flag, combo_draw_flag
├─ Sequência: action_sequence, last_aggressor
└─ Uso: ML-ready, mas falta vetorização para similaridade

PROBLEMA: Features independentes, não capturam contexto sequencial
SOLUÇÃO: Criar embeddings que capturam sequência de ações
```

### 2.2. Limitações dos Dados Atuais

| Limitação | Impacto | Solução Proposta |
|-----------|---------|------------------|
| **Formato flat** | Dificulta queries de árvore | Criar grafo de decisão por mão |
| **Features isoladas** | Não capturam sequência | Embeddings sequenciais (LSTM/Transformer) |
| **Sem indexação** | Busca lenta (scan completo) | FAISS index para nearest neighbors |
| **Sem normalização** | Dificulta similaridade | Vetorização padronizada |
| **Cartas ausentes** | 65% das mãos sem showdown | Inferência probabilística |

### 2.3. Insights da Estrutura Atual

**✅ Pontos Fortes:**
- Features ricas e bem categorizadas
- Board texture detalhado (monotone, paired, span, gap)
- Draws detectados (FD, OESD, gutshot, combo)
- SPR calculado
- Sequência de ações preservada

**⚠️ Pontos a Melhorar:**
- Falta representação de **contexto completo** (estado da mão)
- Falta **vetorização** para busca eficiente
- Falta **indexação** para queries rápidas
- Falta **normalização** de vilões (cada vilão tem distribuições diferentes)

---

## 3. ARQUITETURA PROPOSTA

### 3.1. Visão de Alto Nível

```
┌─────────────────────────────────────────────────────────────────┐
│                    INPUT LAYER                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ XML (iPoker) │  │ TXT (PS)     │  │ ZIP Archive  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                 ETL PIPELINE (Enhanced)                         │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐                  │
│  │ Parser   │ →  │   PHH    │ →  │ Context  │                  │
│  │ Multi-   │    │ Standard │    │ Extractor│                  │
│  │ Format   │    │          │    │          │                  │
│  └──────────┘    └──────────┘    └──────────┘                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              CONTEXT VECTORIZATION ENGINE                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Para cada DECISÃO POINT (ação do vilão):                │   │
│  │                                                          │   │
│  │  Context Vector = [                                     │   │
│  │    • Street (preflop/flop/turn/river)                   │   │
│  │    • Position (IP/OOP)                                  │   │
│  │    • Action Sequence até agora                          │   │
│  │    • Board Texture (monotone, paired, connected, etc)   │   │
│  │    • SPR                                                │   │
│  │    • Pot Size                                           │   │
│  │    • Hero Action (last)                                 │   │
│  │    • Villain Hand Strength (se conhecido)               │   │
│  │    • Draws Available                                    │   │
│  │    • Aggressor (quem tem iniciativa)                    │   │
│  │  ]                                                       │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                   STORAGE LAYER (Hybrid)                        │
│  ┌─────────────────────┐    ┌─────────────────────┐            │
│  │  DuckDB / Parquet   │    │   FAISS Index       │            │
│  │  (Structured Data)  │    │  (Vector Search)    │            │
│  │                     │    │                     │            │
│  │  • Hands            │    │  • Context Vectors  │            │
│  │  • Actions          │    │  • Decision Points  │            │
│  │  • Features         │    │  • Embeddings       │            │
│  └─────────────────────┘    └─────────────────────┘            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              PATTERN MATCHING ENGINE                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 1. Query Parser                                          │  │
│  │    "Limped pot → ISO → Flop monotone → Check"           │  │
│  │           ↓                                              │  │
│  │ 2. Context Vectorization                                 │  │
│  │    Query Vector = vectorize(query_tree)                 │  │
│  │           ↓                                              │  │
│  │ 3. Similarity Search (FAISS)                            │  │
│  │    similar_contexts = faiss.search(query_vec, k=100)    │  │
│  │           ↓                                              │  │
│  │ 4. Filtering & Ranking                                   │  │
│  │    • Exact matches (board texture, street, etc)         │  │
│  │    • Fuzzy matches (similar SPR, pot size)              │  │
│  │    • Weighted scoring                                    │  │
│  │           ↓                                              │  │
│  │ 5. Result Aggregation                                    │  │
│  │    • Group by villain action                            │  │
│  │    • Extract showdown info                              │  │
│  │    • Calculate frequencies                              │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                   PRESENTATION LAYER                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Modern Dashboard (React + FastAPI)                       │  │
│  │                                                          │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │  │
│  │  │ Query       │  │ Tree        │  │ Hand        │     │  │
│  │  │ Builder     │  │ Visualizer  │  │ Replayer    │     │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘     │  │
│  │                                                          │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │  │
│  │  │ Results     │  │ Pattern     │  │ Insights    │     │  │
│  │  │ Explorer    │  │ Explorer    │  │ Generator   │     │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘     │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2. Componentes Principais

**1. Context Extractor**
- Input: Mão em formato PHH
- Output: Lista de "decision points" (momentos de decisão do vilão)
- Cada decision point é um snapshot completo do estado do jogo

**2. Vectorization Engine**
- Input: Decision point
- Output: Vetor de alta dimensão (128-256 dim) representando o contexto
- Técnicas: One-hot encoding + embeddings learned ou hand-crafted

**3. FAISS Index**
- Indexa todos os decision points de todos os vilões
- Permite busca de k-nearest neighbors em <100ms
- Particionado por vilão para queries específicas

**4. Query Engine**
- Parser de queries em linguagem natural ou estruturada
- Converte query em vetor
- Executa busca + filtros
- Agrega resultados

**5. Dashboard**
- Interface visual para construir queries
- Visualização de árvores de decisão
- Hand replayer integrado
- Insights automatizados

---

## 4. MODELAGEM DE CONTEXTOS

### 4.1. Conceito de "Decision Point"

Um **decision point** é um momento específico onde o vilão precisa tomar uma decisão.

**Exemplo:**
```python
DecisionPoint {
    # Identificação
    hand_id: "11514545369",
    villain: "domikan1",
    step_idx: 7,

    # Contexto temporal
    street: "flop",
    action_number_in_street: 2,

    # Estado do jogo
    pot_bb: 12.5,
    eff_stack_bb: 85.0,
    spr: 6.8,

    # Posição
    villain_position: "OOP",  # Big Blind
    hero_position: "IP",      # Button

    # Histórico de ações até agora
    preflop_sequence: ["BTN_raise_3bb", "BB_call"],
    flop_sequence: ["BB_check", "BTN_bet_8bb"],

    # Agressor
    preflop_aggressor: "hero",
    current_aggressor: "hero",

    # Board
    board_cards: ["Kh", "9h", "4h"],
    board_texture: {
        "monotone": True,
        "paired": False,
        "connected": False,
        "high_card": "K",
        "texture_bucket": "WET"
    },

    # Draws disponíveis
    draws: {
        "flush_draw": True,
        "straight_draw": False,
        "gutshot": False
    },

    # Mão do vilão (se conhecida)
    villain_hand: ["Ah", "Qh"],  # ou None se não foi ao showdown
    villain_hand_strength: "FLUSH_DRAW",

    # Ação tomada pelo vilão (TARGET)
    villain_action: "call",
    villain_bet_size_bb: 8.0,

    # Outcome
    went_to_showdown: True,
    villain_won: False
}
```

### 4.2. Vetorização do Decision Point

**Estratégia Híbrida: One-Hot Encoding + Embeddings**

```python
# DIMENSÕES DO VETOR (Total: ~180 dimensões)

# 1. Street (4 dim) - One-hot
[preflop, flop, turn, river]

# 2. Position (2 dim) - One-hot
[IP, OOP]

# 3. Action Sequence (30 dim) - Embedding
# Sequência de ações até agora codificada como embedding
# Ex: "raise → call → check → bet" → embedding de 30 dim

# 4. Board Texture (15 dim) - Multi-hot
[monotone, two_tone, rainbow, paired, trips,
 connected, disconnected, high_broadway, low,
 wet, dry, A_high, K_high, Q_high, J_high]

# 5. SPR Category (5 dim) - One-hot
[micro <2, low 2-5, medium 5-10, high 10-20, very_high >20]

# 6. Pot Size (1 dim) - Normalized (log scale)
log(pot_bb) / 10

# 7. Stack Size (1 dim) - Normalized
eff_stack_bb / 100

# 8. Draws (4 dim) - Binary
[flush_draw, oesd, gutshot, combo_draw]

# 9. Aggressor (3 dim) - One-hot
[villain_aggressor, hero_aggressor, no_aggressor]

# 10. Previous Hero Action (10 dim) - One-hot
[fold, check, call, bet_small, bet_medium, bet_large,
 raise_small, raise_medium, raise_large, all_in]

# 11. Number of Actions So Far (2 dim)
[actions_this_street / 10, total_actions / 20]

# 12. Board Cards Encoding (12 dim)
# Cada carta codificada como (rank_value / 14, suit_one_hot[4])
# 3 cartas no flop = 3 * 4 = 12 dim

# 13. Hand Strength (9 dim) - One-hot (se conhecido)
[high_card, pair, two_pair, trips, straight,
 flush, full_house, quads, straight_flush]

# 14. Additional Context (variável)
# Pode incluir: número de barrels, histórico de showdowns, etc.
```

**Total: ~180 dimensões**

### 4.3. Normalização e Pesos

**Pesos por Categoria de Feature:**
```python
WEIGHTS = {
    "street": 10.0,              # Muito importante (flop != turn)
    "board_texture": 8.0,        # Muito importante
    "action_sequence": 7.0,      # Crítico para padrões
    "spr": 6.0,                  # Importante
    "position": 5.0,             # Importante
    "aggressor": 5.0,            # Importante
    "previous_hero_action": 4.0, # Moderado
    "pot_size": 3.0,             # Moderado
    "draws": 6.0,                # Importante
    "board_cards": 4.0,          # Moderado (já capturado em texture)
    "hand_strength": 7.0,        # Muito importante (se conhecido)
}
```

**Função de Similaridade:**
```python
def similarity_score(vec1, vec2, weights):
    """
    Calcula similaridade ponderada entre dois contextos
    """
    # Cosine similarity por categoria
    score = 0
    total_weight = 0

    for category, weight in weights.items():
        start_idx, end_idx = CATEGORY_INDICES[category]

        # Extrair sub-vetores
        sub_vec1 = vec1[start_idx:end_idx]
        sub_vec2 = vec2[start_idx:end_idx]

        # Cosine similarity
        sim = cosine_similarity(sub_vec1, sub_vec2)

        score += sim * weight
        total_weight += weight

    return score / total_weight  # Normalizar para [0, 1]
```

---

## 5. MOTOR DE BUSCA POR SIMILARIDADE

### 5.1. FAISS - Facebook AI Similarity Search

**Por que FAISS?**
- ✅ Extremamente rápido (milhões de vetores em <100ms)
- ✅ Suporta GPUs para aceleração
- ✅ Vários tipos de índices (Flat, IVF, HNSW)
- ✅ Suporta filtragem (por vilão, por street, etc)
- ✅ Open-source e bem mantido

**Arquitetura do Index:**
```python
import faiss
import numpy as np

# Criar index FAISS
dimension = 180  # Dimensão dos vetores
index = faiss.IndexHNSWFlat(dimension, 32)  # HNSW = Hierarchical Navigable Small World

# Adicionar metadados com IndexIDMap
index_with_ids = faiss.IndexIDMap(index)

# Para cada decision point
for dp in decision_points:
    vector = vectorize(dp)
    index_with_ids.add_with_ids(
        vector.reshape(1, -1),
        np.array([dp.id])
    )

# Busca
query_vector = vectorize(query_decision_point)
k = 50  # Top 50 mais similares
distances, ids = index.search(query_vector.reshape(1, -1), k)

# Retrieve decision points
similar_dps = [get_decision_point(id) for id in ids[0]]
```

### 5.2. Indexação Particionada

**Problema:** Queremos buscar apenas em mãos de um vilão específico.

**Solução:** Criar índices separados por vilão.

```python
# Estrutura de índices
indices = {
    "domikan1": faiss.IndexHNSWFlat(180, 32),
    "gasgas": faiss.IndexHNSWFlat(180, 32),
    "Tipatushka": faiss.IndexHNSWFlat(180, 32),
    # ...
}

# Busca específica
def search_villain(villain_name, query_vector, k=50):
    if villain_name not in indices:
        return []

    index = indices[villain_name]
    distances, ids = index.search(query_vector.reshape(1, -1), k)

    return [get_decision_point(id) for id in ids[0]]
```

### 5.3. Filtragem Pós-Busca

Após encontrar os k-nearest neighbors, aplicar filtros adicionais:

```python
def filter_results(results, filters):
    """
    Filtros adicionais:
    - street_exact: Só mãos na mesma street
    - board_exact: Board exatamente igual
    - spr_range: SPR similar (±2)
    - min_similarity: Score mínimo
    """
    filtered = results

    if filters.get("street_exact"):
        filtered = [r for r in filtered if r.street == filters["street_exact"]]

    if filters.get("board_exact"):
        filtered = [r for r in filtered
                    if r.board_cards == filters["board_exact"]]

    if filters.get("spr_range"):
        spr_min, spr_max = filters["spr_range"]
        filtered = [r for r in filtered
                    if spr_min <= r.spr <= spr_max]

    if filters.get("min_similarity"):
        filtered = [r for r in filtered
                    if r.similarity_score >= filters["min_similarity"]]

    return filtered
```

### 5.4. Agregação de Resultados

```python
def aggregate_results(results):
    """
    Agrega resultados e extrai insights
    """
    aggregation = {
        "total_hands": len(results),
        "actions_distribution": {},
        "showdown_hands": [],
        "avg_similarity": np.mean([r.similarity_score for r in results]),
        "contexts": []
    }

    # Distribuição de ações
    for r in results:
        action = r.villain_action
        if action not in aggregation["actions_distribution"]:
            aggregation["actions_distribution"][action] = {
                "count": 0,
                "hands": [],
                "showdowns": []
            }

        aggregation["actions_distribution"][action]["count"] += 1
        aggregation["actions_distribution"][action]["hands"].append(r.hand_id)

        if r.went_to_showdown:
            aggregation["actions_distribution"][action]["showdowns"].append({
                "hand_id": r.hand_id,
                "villain_hand": r.villain_hand,
                "villain_hand_strength": r.villain_hand_strength,
                "villain_won": r.villain_won
            })

    # Showdowns
    aggregation["showdown_hands"] = [r for r in results if r.went_to_showdown]

    return aggregation
```

---

## 6. QUERY LANGUAGE & INTERFACE

### 6.1. Query DSL (Domain-Specific Language)

**Sintaxe Proposta:**

```python
# Query 1: Simples
query = """
VILLAIN: gasgas
STREET: flop
BOARD: monotone
HERO_ACTION: check
VILLAIN_ACTION: ???
"""

# Query 2: Sequencial
query = """
VILLAIN: Tipatushka
TREE:
  preflop: hero_limp_sb → villain_iso_3bb → hero_call
  flop: [Kh 9h 4h] → hero_check → villain_bet_8bb → hero_call
  turn: [2s] → hero_check → villain_???
FILTERS:
  spr_range: [5, 10]
  min_similarity: 0.8
"""

# Query 3: Board Pattern
query = """
VILLAIN: domikan1
PATTERN:
  board_texture: two_tone + paired
  spr: low
  position: OOP
  action_sequence: check_raise
SHOW: showdowns_only
"""
```

**Parser de Query:**

```python
class QueryParser:
    def parse(self, query_str):
        """
        Converte query string em estrutura executável
        """
        parsed = {
            "villain": None,
            "tree": [],
            "filters": {},
            "show": "all"
        }

        # Parse villain
        if "VILLAIN:" in query_str:
            parsed["villain"] = extract_villain(query_str)

        # Parse tree
        if "TREE:" in query_str:
            parsed["tree"] = extract_tree(query_str)

        # Parse filters
        if "FILTERS:" in query_str:
            parsed["filters"] = extract_filters(query_str)

        # Parse show mode
        if "SHOW:" in query_str:
            parsed["show"] = extract_show_mode(query_str)

        return parsed
```

### 6.2. Query Builder (Interface Visual)

**Componente 1: Tree Builder**
```
┌─────────────────────────────────────────────────────────┐
│ 🌳 TREE BUILDER                                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  PREFLOP:                                              │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐       │
│  │ Hero SB    │→ │ Villain BB │→ │ Hero       │       │
│  │ Limp       │  │ ISO 3bb    │  │ Call       │       │
│  └────────────┘  └────────────┘  └────────────┘       │
│                                                         │
│  FLOP: [K♥][9♥][4♥]                                    │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐       │
│  │ Hero       │→ │ Villain    │→ │ Hero       │       │
│  │ Check      │  │ Bet 8bb    │  │ Call       │       │
│  └────────────┘  └────────────┘  └────────────┘       │
│                                                         │
│  TURN: [2♠]                                            │
│  ┌────────────┐  ┌────────────┐                       │
│  │ Hero       │→ │ Villain    │                       │
│  │ Check      │  │    ???     │ ← QUERY POINT         │
│  └────────────┘  └────────────┘                       │
│                                                         │
│  [+ Add Action] [Clear Tree] [Search Similar]          │
└─────────────────────────────────────────────────────────┘
```

**Componente 2: Filter Panel**
```
┌─────────────────────────────────────────────────────────┐
│ 🔍 FILTERS                                              │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Villain: [gasgas        ▼]                            │
│                                                         │
│  SPR Range: [5] ──────●──── [10]                       │
│                                                         │
│  Board Texture:                                        │
│  ☑ Monotone  ☐ Two-tone  ☐ Rainbow                    │
│  ☑ Paired    ☐ Connected ☐ Dry                        │
│                                                         │
│  Min Similarity: [0.8] ──────●──── [1.0]               │
│                                                         │
│  Show:                                                 │
│  ○ All Hands  ● Showdowns Only  ○ Known Hands         │
│                                                         │
│  [Apply Filters] [Reset]                               │
└─────────────────────────────────────────────────────────┘
```

### 6.3. Tipos de Queries Suportadas

**1. Exact Match Query**
```python
# Busca exata por contexto específico
query = {
    "type": "exact",
    "villain": "gasgas",
    "street": "flop",
    "board": ["Kh", "9h", "4h"],
    "action_sequence": ["check", "bet"],
    "hero_action": "call"
}
# Retorna: Mãos onde contexto é EXATAMENTE igual
```

**2. Similarity Query**
```python
# Busca por similaridade (fuzzy)
query = {
    "type": "similarity",
    "villain": "Tipatushka",
    "tree": [...],
    "min_similarity": 0.75,
    "k": 50
}
# Retorna: Top 50 contextos mais similares (similarity >= 0.75)
```

**3. Pattern Query**
```python
# Busca por padrões abstratos
query = {
    "type": "pattern",
    "villain": "domikan1",
    "pattern": {
        "board_texture": "wet",
        "position": "OOP",
        "spr": "low",
        "action_type": "check_raise"
    }
}
# Retorna: Todas as mãos que satisfazem o padrão abstrato
```

**4. Range Query**
```python
# Busca por range de mãos mostradas
query = {
    "type": "range",
    "villain": "gasgas",
    "context": {...},
    "action": "triple_barrel",
    "show": "showdowns_only"
}
# Retorna: Distribuição de mãos que vilão mostrou ao fazer essa ação
```

---

## 7. DASHBOARD MODERNA

### 7.1. Stack Tecnológico

**Frontend:**
- **React 18** - Framework UI
- **TypeScript** - Type safety
- **TanStack Query** - Data fetching
- **Zustand** - State management
- **TailwindCSS** - Styling
- **Recharts** - Data visualization
- **Framer Motion** - Animações

**Backend:**
- **FastAPI** - API REST (async, rápido)
- **Python 3.11+**
- **FAISS** - Vector search
- **DuckDB** - SQL analytics
- **Pydantic** - Data validation

**Deployment:**
- **Docker** - Containerização
- **Nginx** - Reverse proxy
- **PostgreSQL** - Metadata (opcional)

### 7.2. Interface da Dashboard

**Layout Principal:**
```
┌─────────────────────────────────────────────────────────────────┐
│ 🎯 SpinAnalyzer - Pattern Search Engine            [User] [⚙]  │
├──────────┬──────────────────────────────────────────────────────┤
│          │                                                      │
│  MENU    │              MAIN WORKSPACE                          │
│          │                                                      │
│  🏠 Home │  ┌────────────────────────────────────────────────┐ │
│  🔍 Search│  │                                                │ │
│  📊 Stats │  │      QUERY BUILDER                             │ │
│  👤 Villains│ │                                                │ │
│  📁 Hands │  │   [Tree Builder Component]                    │ │
│  ⚙ Settings│ │                                                │ │
│          │  └────────────────────────────────────────────────┘ │
│          │                                                      │
│          │  ┌────────────────────────────────────────────────┐ │
│          │  │                                                │ │
│          │  │      RESULTS PANEL                             │ │
│          │  │                                                │ │
│          │  │   [Results Explorer Component]                 │ │
│          │  │                                                │ │
│          │  └────────────────────────────────────────────────┘ │
│          │                                                      │
│          │  ┌──────────────┐  ┌──────────────┐               │
│          │  │   INSIGHTS   │  │  HAND REPLAY │               │
│          │  │              │  │              │               │
│          │  └──────────────┘  └──────────────┘               │
└──────────┴──────────────────────────────────────────────────────┘
```

### 7.3. Telas Principais

**TELA 1: Query Builder**
```
┌─────────────────────────────────────────────────────────┐
│ 🔍 BUILD YOUR QUERY                                     │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Step 1: Select Villain                                │
│  ┌─────────────────────────────────────────────────┐   │
│  │ [Search villain...        ]  [🔄 Load All]      │   │
│  │                                                 │   │
│  │  ● gasgas (609 hands)                          │   │
│  │  ○ Tipatushka (2,340 hands)                    │   │
│  │  ○ domikan1 (134 hands)                        │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  Step 2: Build Decision Tree                           │
│  ┌─────────────────────────────────────────────────┐   │
│  │ [Visual Tree Builder - Drag & Drop Interface]  │   │
│  │                                                 │   │
│  │ PREFLOP → FLOP → TURN → RIVER                  │   │
│  │   ↓       ↓      ↓       ↓                     │   │
│  │ [+]     [+]    [+]     [+]                     │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  Step 3: Set Filters                                   │
│  ┌─────────────────────────────────────────────────┐   │
│  │ SPR: [min] to [max]                            │   │
│  │ Board Texture: [checkboxes]                    │   │
│  │ Similarity: [slider]                           │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  [🚀 SEARCH PATTERNS] [Clear] [Save Query]             │
└─────────────────────────────────────────────────────────┘
```

**TELA 2: Results Explorer**
```
┌─────────────────────────────────────────────────────────┐
│ 📊 RESULTS (23 similar hands found)                     │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ACTION DISTRIBUTION                                   │
│  ┌─────────────────────────────────────────────────┐   │
│  │                                                 │   │
│  │  Check: ████████████ 12 hands (52%)            │   │
│  │  Bet:   ███████ 8 hands (35%)                  │   │
│  │  Raise: ██ 3 hands (13%)                       │   │
│  │                                                 │   │
│  │  [View Details] [Export CSV]                   │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  SHOWDOWN ANALYSIS (15/23 went to showdown - 65%)     │
│  ┌─────────────────────────────────────────────────┐   │
│  │                                                 │   │
│  │  ACTION    │ HANDS │ VALUE  │ BLUFF  │ DRAW   │   │
│  │  ─────────────────────────────────────────────│   │
│  │  Check     │  7    │ 3 (43%)│ 4 (57%)│ 0      │   │
│  │  Bet       │  5    │ 4 (80%)│ 0      │ 1 (20%)│   │
│  │  Raise     │  3    │ 3 (100%)│ 0     │ 0      │   │
│  │                                                 │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  HAND LIST                                             │
│  ┌─────────────────────────────────────────────────┐   │
│  │ #  │ Hand ID    │ Action │ Cards  │ Similarity │   │
│  │────────────────────────────────────────────────│   │
│  │ 1  │ 11514...91 │ Check  │ Ah Qh  │ 0.94      │   │
│  │ 2  │ 11514...37 │ Bet    │ Kh Jh  │ 0.91      │   │
│  │ 3  │ 11514...82 │ Check  │ —      │ 0.89      │   │
│  │                                                 │   │
│  │ [View Hand] [Compare] [Add to Notebook]        │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

**TELA 3: Hand Replayer**
```
┌─────────────────────────────────────────────────────────┐
│ 🎬 HAND REPLAYER - Hand #11514545369                    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │                POKER TABLE                      │   │
│  │                                                 │   │
│  │         BOARD: [K♥] [9♥] [4♥]                  │   │
│  │                                                 │   │
│  │  Villain (BB)                   Hero (BTN)     │   │
│  │  Stack: 85bb                    Stack: 92bb    │   │
│  │  [?][?]                         [A♠][K♠]       │   │
│  │                                                 │   │
│  │         POT: 12.5bb                            │   │
│  │                                                 │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ACTION TIMELINE                                       │
│  ┌─────────────────────────────────────────────────┐   │
│  │ PREFLOP:                                        │   │
│  │   Hero raises 3bb → Villain calls               │   │
│  │                                                 │   │
│  │ FLOP: [K♥ 9♥ 4♥]                               │   │
│  │   Villain checks → Hero bets 8bb → Villain ??  │   │
│  │                                      ↑          │   │
│  │                                   [YOU ARE HERE]│   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  [⏮ Prev] [⏸ Pause] [▶ Play] [⏭ Next] [⏩ End]       │
│                                                         │
│  CONTEXT INFO                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │ SPR: 6.8                                        │   │
│  │ Position: Villain OOP                          │   │
│  │ Board: WET (monotone flush possible)           │   │
│  │ Draws: Hero has nut flush draw                 │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

**TELA 4: Insights Generator**
```
┌─────────────────────────────────────────────────────────┐
│ 💡 INSIGHTS - Villain: gasgas                           │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Based on 23 similar contexts:                         │
│                                                         │
│  🎯 KEY FINDINGS                                       │
│  ┌─────────────────────────────────────────────────┐   │
│  │                                                 │   │
│  │ 1. ⚠️ HIGH GIVE-UP RATE (52%)                  │   │
│  │    Villain checks 12/23 times after Hero calls │   │
│  │    flop bet in wet boards.                     │   │
│  │                                                 │   │
│  │    💰 EXPLOIT: Call flop bet, then bet turn    │   │
│  │    when villain checks (70%+ fold expected)    │   │
│  │                                                 │   │
│  │ 2. ✅ VALUE-HEAVY WHEN BETS (80%)              │   │
│  │    When villain bets turn, he has made hand    │   │
│  │    or strong draw 4/5 times.                   │   │
│  │                                                 │   │
│  │    ⚠️ CAUTION: Respect turn bets, fold weak   │   │
│  │    hands. Only continue with decent equity.    │   │
│  │                                                 │   │
│  │ 3. 🚨 RARE CHECK-RAISES (3/23)                │   │
│  │    All check-raises had nuts or near-nuts.     │   │
│  │                                                 │   │
│  │    ❌ AVOID: Bluff catching vs check-raise    │   │
│  │                                                 │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  📈 CONFIDENCE METRICS                                 │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Sample Size: 23 hands ⚠️ (Moderate)            │   │
│  │ Showdown Rate: 65% ✅ (High)                   │   │
│  │ Avg Similarity: 0.87 ✅ (Excellent)            │   │
│  │                                                 │   │
│  │ Recommendation: Insights are RELIABLE but      │   │
│  │ would benefit from more data (50+ ideal).      │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  [Export Report] [Save to Notebook] [Share]            │
└─────────────────────────────────────────────────────────┘
```

### 7.4. Features Avançadas da Dashboard

**1. Saved Queries (Queries Salvos)**
- Salvar queries complexas para reutilização
- Compartilhar queries com outros usuários
- Templates pré-definidos (ex: "3-Barrel Analysis", "Flop C-bet Pattern")

**2. Notebook Mode**
- Ambiente para análise exploratória
- Combinar múltiplas queries
- Gerar relatórios customizados
- Exportar para PDF/Markdown

**3. Comparison Mode**
- Comparar padrões de 2+ vilões lado a lado
- Identificar diferenças táticas
- Gerar relatórios comparativos

**4. Live Analysis**
- Importar mão em tempo real
- Buscar padrões instantaneamente
- Sugerir linha de jogo baseada em histórico

**5. Auto-Tagging**
- Sistema automático de tags para mãos
- Ex: "bluff_3barrel", "valuetown", "hero_call"
- Facilita buscas futuras

---

## 8. PIPELINE DE IMPLEMENTAÇÃO

### 8.1. Data Processing Pipeline

```
INPUT: D:\code\python\spinAnalyzer\dataset\original_hands\final
  ├─ XMLs (iPoker)
  ├─ ZIP (archives)
  └─ Outros formatos

         ↓

STEP 1: UNIFIED PARSER
  Script: src/parsers/unified_parser.py
  ├─ Detecta formato automaticamente (XML, TXT, ZIP)
  ├─ Converte para PHH (TOML)
  ├─ Filtra apenas Heads-Up
  └─ Output: dataset/phh_hands/

         ↓

STEP 2: CONTEXT EXTRACTION
  Script: src/context/context_extractor.py
  ├─ Lê arquivos PHH
  ├─ Identifica decision points do vilão
  ├─ Extrai contexto completo de cada DP
  └─ Output: dataset/decision_points.parquet

  Schema:
  ┌─────────────────────────────────────────────┐
  │ decision_id (PK)                            │
  │ hand_id (FK)                                │
  │ villain_name                                │
  │ step_idx                                    │
  │ street                                      │
  │ context_json (JSONB)                        │
  │ context_vector (ARRAY[180])                 │
  │ villain_action                              │
  │ villain_bet_size_bb                         │
  │ went_to_showdown                            │
  │ villain_hand (if known)                     │
  │ villain_hand_strength                       │
  │ similarity_hash (for dedup)                 │
  └─────────────────────────────────────────────┘

         ↓

STEP 3: VECTORIZATION
  Script: src/vectorization/vectorizer.py
  ├─ Para cada decision point:
  │  ├─ Extrai features
  │  ├─ Aplica one-hot encoding
  │  ├─ Gera embedding de sequence
  │  └─ Concatena em vetor final (180 dim)
  ├─ Normaliza vetores
  └─ Atualiza decision_points.parquet (coluna context_vector)

         ↓

STEP 4: FAISS INDEXING
  Script: src/indexing/build_indices.py
  ├─ Agrupa decision points por vilão
  ├─ Para cada vilão:
  │  ├─ Cria índice FAISS (HNSW)
  │  ├─ Adiciona vetores
  │  └─ Salva índice: indices/{villain_name}.faiss
  └─ Salva metadata: indices/metadata.json

         ↓

STEP 5: VALIDATION & TESTING
  Script: src/validation/validate_pipeline.py
  ├─ Valida integridade dos dados
  ├─ Testa queries de exemplo
  ├─ Verifica performance (latency)
  └─ Gera relatório de validação
```

### 8.2. API Endpoints (FastAPI)

```python
# src/api/main.py

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import faiss
import numpy as np

app = FastAPI(title="SpinAnalyzer API")

# ============================================
# MODELS
# ============================================

class QueryTree(BaseModel):
    villain: str
    tree: List[dict]  # Sequência de ações
    filters: dict
    k: int = 50
    min_similarity: float = 0.7

class SearchResult(BaseModel):
    decision_id: str
    hand_id: str
    similarity_score: float
    villain_action: str
    villain_hand: Optional[List[str]]
    context: dict

class AggregatedResults(BaseModel):
    total_hands: int
    actions_distribution: dict
    showdown_hands: List[dict]
    avg_similarity: float
    insights: List[str]

# ============================================
# ENDPOINTS
# ============================================

@app.post("/search/similarity", response_model=List[SearchResult])
async def search_similarity(query: QueryTree):
    """
    Busca por similaridade usando FAISS
    """
    # 1. Construir vetor de query
    query_vector = vectorize_tree(query.tree)

    # 2. Carregar índice do vilão
    index = load_faiss_index(query.villain)

    # 3. Buscar k-nearest neighbors
    distances, ids = index.search(
        query_vector.reshape(1, -1),
        query.k
    )

    # 4. Recuperar decision points
    results = []
    for i, dp_id in enumerate(ids[0]):
        dp = get_decision_point(dp_id)

        # Filtrar por similaridade mínima
        if distances[0][i] >= query.min_similarity:
            results.append(SearchResult(
                decision_id=dp.id,
                hand_id=dp.hand_id,
                similarity_score=float(distances[0][i]),
                villain_action=dp.villain_action,
                villain_hand=dp.villain_hand,
                context=dp.context_json
            ))

    return results

@app.post("/search/aggregate", response_model=AggregatedResults)
async def search_aggregate(query: QueryTree):
    """
    Busca + agregação de resultados
    """
    # Buscar
    results = await search_similarity(query)

    # Agregar
    aggregated = aggregate_results(results)

    # Gerar insights
    insights = generate_insights(aggregated)
    aggregated["insights"] = insights

    return aggregated

@app.get("/villains", response_model=List[dict])
async def get_villains():
    """
    Lista todos os vilões disponíveis
    """
    return [
        {
            "name": "gasgas",
            "total_hands": 609,
            "total_decision_points": 1834,
            "showdown_rate": 0.35
        },
        # ...
    ]

@app.get("/hand/{hand_id}", response_model=dict)
async def get_hand(hand_id: str):
    """
    Retorna detalhes completos de uma mão
    """
    hand = load_hand(hand_id)
    return {
        "hand_id": hand_id,
        "players": hand.players,
        "actions": hand.actions,
        "board": hand.board,
        "outcome": hand.outcome
    }

@app.get("/stats/villain/{villain_name}", response_model=dict)
async def get_villain_stats(villain_name: str):
    """
    Estatísticas gerais do vilão
    """
    return {
        "villain": villain_name,
        "total_hands": count_hands(villain_name),
        "decision_points_breakdown": {
            "preflop": 234,
            "flop": 567,
            "turn": 345,
            "river": 123
        },
        "most_common_actions": [
            {"action": "check", "count": 456},
            {"action": "bet", "count": 234},
            # ...
        ]
    }

# ============================================
# HELPERS
# ============================================

def vectorize_tree(tree: List[dict]) -> np.ndarray:
    """Converte árvore de decisão em vetor"""
    # Implementação da vetorização
    pass

def load_faiss_index(villain_name: str):
    """Carrega índice FAISS do vilão"""
    index_path = f"indices/{villain_name}.faiss"
    return faiss.read_index(index_path)

def get_decision_point(dp_id: str):
    """Recupera decision point do banco"""
    # Query DuckDB ou Parquet
    pass

def aggregate_results(results: List[SearchResult]) -> dict:
    """Agrega resultados"""
    pass

def generate_insights(aggregated: dict) -> List[str]:
    """Gera insights automáticos"""
    # Regras heurísticas + LLM (opcional)
    pass
```

### 8.3. Frontend React Structure

```
src/
├── components/
│   ├── QueryBuilder/
│   │   ├── TreeBuilder.tsx       # Construtor visual de árvore
│   │   ├── FilterPanel.tsx       # Painel de filtros
│   │   ├── VillainSelector.tsx   # Seletor de vilão
│   │   └── ActionNode.tsx        # Nó de ação na árvore
│   │
│   ├── Results/
│   │   ├── ResultsExplorer.tsx   # Explorador de resultados
│   │   ├── ActionDistribution.tsx # Distribuição de ações
│   │   ├── ShowdownAnalysis.tsx  # Análise de showdowns
│   │   └── HandList.tsx          # Lista de mãos
│   │
│   ├── HandReplayer/
│   │   ├── Table.tsx             # Mesa de poker
│   │   ├── Timeline.tsx          # Timeline de ações
│   │   └── ContextInfo.tsx       # Info de contexto
│   │
│   └── Insights/
│       ├── InsightCard.tsx       # Card de insight
│       ├── ConfidenceMetrics.tsx # Métricas de confiança
│       └── ExportPanel.tsx       # Painel de export
│
├── hooks/
│   ├── useQuery.ts               # Hook para queries
│   ├── useSearch.ts              # Hook para busca
│   └── useHand.ts                # Hook para mãos
│
├── services/
│   ├── api.ts                    # Cliente API
│   ├── vectorization.ts          # Vetorização client-side
│   └── storage.ts                # LocalStorage wrapper
│
├── store/
│   ├── queryStore.ts             # State de queries (Zustand)
│   ├── resultsStore.ts           # State de resultados
│   └── uiStore.ts                # State de UI
│
└── pages/
    ├── SearchPage.tsx            # Página de busca
    ├── VillainsPage.tsx          # Página de vilões
    ├── HandsPage.tsx             # Biblioteca de mãos
    └── SettingsPage.tsx          # Configurações
```

---

## 9. TECNOLOGIAS E STACK

### 9.1. Backend Stack

```yaml
Core:
  - Python: 3.11+
  - FastAPI: 0.104+
  - Pydantic: 2.0+

Data Processing:
  - Pandas: 2.1+
  - Polars: 0.19+ (alternativa mais rápida)
  - DuckDB: 0.9+ (SQL analytics em Parquet)
  - PyArrow: 13.0+ (Parquet I/O)

Vector Search:
  - FAISS: 1.7+ (CPU e GPU)
  - NumPy: 1.24+
  - SciPy: 1.11+ (distance metrics)

Machine Learning (Opcional):
  - Scikit-learn: 1.3+ (embeddings)
  - Sentence-Transformers: 2.2+ (se usar transformers)

Parsing:
  - tomli / tomli_w: TOML (PHH format)
  - lxml: XML parsing
  - BeautifulSoup4: HTML parsing (se necessário)

Database (Metadata):
  - SQLAlchemy: 2.0+ (ORM)
  - Alembic: Migrations
  - PostgreSQL: 14+ (opcional, para metadata)

Utilities:
  - tqdm: Progress bars
  - Rich: Terminal formatting
  - loguru: Logging
  - python-dotenv: Config
```

### 9.2. Frontend Stack

```yaml
Core:
  - React: 18.2+
  - TypeScript: 5.0+
  - Vite: 5.0+ (build tool)

State Management:
  - Zustand: 4.4+ (lightweight)
  - TanStack Query: 5.0+ (data fetching)

UI Components:
  - TailwindCSS: 3.3+
  - HeadlessUI: 1.7+ (accessible components)
  - Radix UI: 1.0+ (primitives)
  - Framer Motion: 10.0+ (animations)

Data Visualization:
  - Recharts: 2.8+ (charts)
  - D3.js: 7.8+ (advanced viz)
  - React Flow: 11.0+ (árvores de decisão)

Forms:
  - React Hook Form: 7.47+
  - Zod: 3.22+ (validation)

Utilities:
  - Axios: 1.5+ (HTTP client)
  - date-fns: 2.30+ (date manipulation)
  - clsx: 2.0+ (className utility)
```

### 9.3. DevOps & Deployment

```yaml
Containerization:
  - Docker: 24+
  - Docker Compose: 2.21+

Web Server:
  - Nginx: 1.25+ (reverse proxy)
  - Gunicorn: 21+ (WSGI server)
  - Uvicorn: 0.23+ (ASGI server)

CI/CD:
  - GitHub Actions (ou GitLab CI)
  - Pre-commit hooks

Testing:
  - Pytest: 7.4+ (backend)
  - Vitest: 0.34+ (frontend)
  - Playwright: 1.38+ (E2E)

Monitoring:
  - Prometheus: Metrics
  - Grafana: Dashboards
  - Sentry: Error tracking
```

---

## 10. ROADMAP DE DESENVOLVIMENTO

### 10.1. FASE 1: Foundation (4-6 semanas)

**Semana 1-2: Data Pipeline**
```
✅ Tasks:
├─ Unified Parser (XML, TXT, ZIP)
├─ PHH Converter refactored
├─ Context Extractor implementation
├─ Decision Points Parquet schema
└─ Batch processing (1000+ mãos)

📦 Deliverables:
├─ dataset/decision_points.parquet (10k+ rows)
├─ src/parsers/unified_parser.py
├─ src/context/context_extractor.py
└─ Tests + validation scripts
```

**Semana 3-4: Vectorization & Indexing**
```
✅ Tasks:
├─ Vectorization engine (180 dim)
├─ Feature engineering refinement
├─ FAISS index builder
├─ Index partitioning by villain
└─ Performance benchmarks

📦 Deliverables:
├─ src/vectorization/vectorizer.py
├─ src/indexing/build_indices.py
├─ indices/{villain}.faiss (múltiplos)
└─ Benchmark report (<100ms search)
```

**Semana 5-6: API Backend**
```
✅ Tasks:
├─ FastAPI setup
├─ Search endpoints (/search/similarity)
├─ Aggregation endpoints (/search/aggregate)
├─ CRUD endpoints (hands, villains)
└─ API tests + documentation

📦 Deliverables:
├─ src/api/main.py
├─ OpenAPI documentation
├─ Postman collection
└─ API tests (Pytest)
```

### 10.2. FASE 2: Dashboard MVP (4-5 semanas)

**Semana 7-8: Frontend Setup & Query Builder**
```
✅ Tasks:
├─ React + Vite setup
├─ Component library (TailwindCSS)
├─ Tree Builder component
├─ Filter Panel component
└─ API integration (TanStack Query)

📦 Deliverables:
├─ src/components/QueryBuilder/
├─ Functional query builder UI
└─ Integration with backend API
```

**Semana 9-10: Results & Hand Replayer**
```
✅ Tasks:
├─ Results Explorer component
├─ Action Distribution charts
├─ Showdown Analysis tables
├─ Hand Replayer (table + timeline)
└─ Data visualization (Recharts)

📦 Deliverables:
├─ src/components/Results/
├─ src/components/HandReplayer/
└─ Interactive results display
```

**Semana 11: Insights & Polish**
```
✅ Tasks:
├─ Insights Generator (backend)
├─ Insights Display (frontend)
├─ Export functionality (CSV, PDF)
├─ UI polish + animations
└─ Responsive design

📦 Deliverables:
├─ src/components/Insights/
├─ Export endpoints
└─ Polished UI
```

### 10.3. FASE 3: Advanced Features (6-8 semanas)

**Semana 12-13: Query Language & Templates**
```
✅ Tasks:
├─ Query DSL parser
├─ Saved queries (CRUD)
├─ Query templates
├─ Query sharing
└─ Advanced filters

📦 Deliverables:
├─ Query language spec
├─ Templates library
└─ Sharing functionality
```

**Semana 14-15: Notebook Mode**
```
✅ Tasks:
├─ Multi-query canvas
├─ Notes & annotations
├─ Report generator
├─ PDF export
└─ Markdown export

📦 Deliverables:
├─ Notebook interface
├─ Report templates
└─ Export functionality
```

**Semana 16-17: Comparison & Live Analysis**
```
✅ Tasks:
├─ Multi-villain comparison
├─ Side-by-side view
├─ Live hand import
├─ Real-time analysis
└─ Suggestion engine

📦 Deliverables:
├─ Comparison mode
├─ Live analysis
└─ Suggestion API
```

**Semana 18-19: Optimizations & Scaling**
```
✅ Tasks:
├─ FAISS GPU acceleration
├─ Caching layer (Redis)
├─ Query optimization
├─ Database partitioning
└─ Load testing

📦 Deliverables:
├─ Performance improvements
├─ Scalability to 100k+ hands
└─ Load test reports
```

### 10.4. FASE 4: Production Ready (2-3 semanas)

**Semana 20-21: Testing & QA**
```
✅ Tasks:
├─ Unit tests (coverage >80%)
├─ Integration tests
├─ E2E tests (Playwright)
├─ Security audit
└─ Bug fixes

📦 Deliverables:
├─ Test suite completo
├─ Security report
└─ Bug fixes
```

**Semana 22: Deployment & Documentation**
```
✅ Tasks:
├─ Docker containers
├─ Docker Compose setup
├─ Deployment guide
├─ User documentation
└─ Video tutorials

📦 Deliverables:
├─ Dockerfiles + docker-compose.yml
├─ Deployment docs
├─ User manual
└─ Tutorial videos
```

---

## 11. MÉTRICAS DE SUCESSO

### 11.1. Performance Targets

| Métrica | Target | Critical |
|---------|--------|----------|
| **Search Latency** | <100ms (p95) | ✅ |
| **Query Build Time** | <500ms | ✅ |
| **Index Build Time** | <10min para 10k mãos | ⚠️ |
| **Memory Usage** | <4GB (backend) | ✅ |
| **Concurrent Users** | 10+ simultâneos | ⚠️ |

### 11.2. Quality Metrics

| Métrica | Target |
|---------|--------|
| **Search Precision** | >80% relevante |
| **Search Recall** | >70% de mãos similares encontradas |
| **Code Coverage** | >80% |
| **Bug Rate** | <5 bugs/mês após launch |
| **User Satisfaction** | >4.0/5.0 |

### 11.3. Data Metrics

| Métrica | Inicial | 6 meses | 12 meses |
|---------|---------|---------|----------|
| **Total Hands** | 10k | 50k | 200k |
| **Decision Points** | 30k | 150k | 600k |
| **Villains Tracked** | 50 | 200 | 500 |
| **Avg Hands/Villain** | 200 | 250 | 400 |

---

## 12. RISCOS E MITIGAÇÕES

### 12.1. Riscos Técnicos

| Risco | Impacto | Probabilidade | Mitigação |
|-------|---------|---------------|-----------|
| **FAISS performance degrada com scale** | Alto | Médio | Particionar índices, usar GPU, considerar Milvus |
| **Vetorização inadequada** | Alto | Médio | Validar com queries manuais, iterar features |
| **Parquet files corruptos** | Médio | Baixo | Checksums, backups, validação |
| **API latency alto** | Médio | Médio | Caching, otimização de queries |

### 12.2. Riscos de Produto

| Risco | Impacto | Probabilidade | Mitigação |
|-------|---------|---------------|-----------|
| **UX complexa demais** | Alto | Alto | User testing, iteração, tutorials |
| **Resultados não relevantes** | Alto | Médio | Tuning de weights, user feedback |
| **Falta de dados de vilão** | Médio | Alto | Clear messaging, suggest data collection |
| **Slow adoption** | Médio | Médio | Marketing, tutorials, free tier |

---

## 13. PRÓXIMOS PASSOS IMEDIATOS

### 13.1. Esta Semana (Semana 1)

**Segunda-feira:**
```bash
✅ Tasks:
1. Criar estrutura de diretórios do projeto
2. Setup ambiente Python (venv, requirements.txt)
3. Implementar unified_parser.py (básico)
4. Testar com dataset/original_hands/final

⏱ Estimativa: 6-8 horas
```

**Terça-feira:**
```bash
✅ Tasks:
1. Implementar context_extractor.py
2. Definir schema de decision_points.parquet
3. Processar primeiras 100 mãos
4. Validar extração de contextos

⏱ Estimativa: 6-8 horas
```

**Quarta-feira:**
```bash
✅ Tasks:
1. Implementar vectorizer.py (v1)
2. Criar features de 180 dim
3. Testar vetorização em 100 decision points
4. Validar distribuição de vetores

⏱ Estimativa: 6-8 horas
```

**Quinta-feira:**
```bash
✅ Tasks:
1. Implementar build_indices.py
2. Criar primeiro índice FAISS
3. Testar busca simples
4. Benchmark de performance

⏱ Estimativa: 6-8 horas
```

**Sexta-feira:**
```bash
✅ Tasks:
1. Processar dataset completo (1000+ mãos)
2. Criar índices para top 5 vilões
3. Testes de integração
4. Documentação e planning próxima semana

⏱ Estimativa: 6-8 horas
```

### 13.2. Semana 2

- FastAPI setup
- Endpoints básicos (/search/similarity)
- Testes de API
- Documentação OpenAPI

### 13.3. Semana 3-4

- React frontend setup
- Query Builder MVP
- Integração com API
- Primeiros testes de UX

---

## 14. CONCLUSÃO

Este plano detalha a construção de um **sistema de busca de padrões contextuais** robusto e escalável para análise de poker Heads-Up.

**Diferenciais do Sistema:**
1. ✅ **Busca Semântica** - Não é busca exata, é por similaridade
2. ✅ **Context-Aware** - Entende o contexto completo do jogo
3. ✅ **Escalável** - FAISS permite milhões de decision points
4. ✅ **Player-Specific** - Análise individualizada por vilão
5. ✅ **Interactive** - Dashboard moderna e intuitiva

**Estimativas:**
- **Tempo total**: 20-22 semanas (~5-6 meses)
- **Complexidade**: Alta (mas viável)
- **ROI**: Alto (ferramenta única no mercado)

**Próximo passo:** Validar este plano e iniciar Fase 1 - Foundation.

---

**Versão:** 1.0
**Data:** 15/11/2025
**Autor:** SpinAnalyzer Team
