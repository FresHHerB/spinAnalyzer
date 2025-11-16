# Métodos de Análise e Identificação - SpinAnalyzer v2.0

## Visão Geral

O SpinAnalyzer utiliza um sistema **baseado em regras** para identificar forças de mãos, draws e texturas de board. Os dados são processados através de um pipeline ETL que extrai, transforma e vetoriza os decision points.

---

## 1. Glossário/Dicionário do Sistema

### 1.1 Hand Strength (Força da Mão)

O sistema classifica as mãos em **9 categorias** ordenadas por força:

```python
HAND_STRENGTHS = [
    'HIGH_CARD',        # 0 - Carta alta
    'ONE_PAIR',         # 1 - Um par
    'TWO_PAIR',         # 2 - Dois pares
    'THREE_OF_A_KIND',  # 3 - Trinca
    'STRAIGHT',         # 4 - Sequência
    'FLUSH',            # 5 - Flush
    'FULL_HOUSE',       # 6 - Full house
    'FOUR_OF_A_KIND',   # 7 - Quadra
    'STRAIGHT_FLUSH'    # 8 - Straight flush
]
```

**Onde:** `src/vectorization/vectorizer.py:427-430`

### 1.2 Draws (Possibilidades de Melhoria)

O sistema identifica **4 tipos de draws**:

```python
DRAW_TYPES = {
    'flush_draw': bool,    # 9 outs - 2 cartas do mesmo naipe
    'oesd': bool,          # 8 outs - Open-Ended Straight Draw
    'gutshot': bool,       # 4 outs - Gutshot Straight Draw
    'combo_draw': bool     # 12+ outs - Combinação de draws
}
```

**Onde:** `src/vectorization/vectorizer.py:380-386`

**Exemplos:**
- `flush_draw=True`: Vilão tem 2 paus, board tem 2 paus
- `oesd=True`: Vilão tem JT, board tem KQ9 (straight draw aberto)
- `gutshot=True`: Vilão tem JT, board tem K93 (gutshot para Q)
- `combo_draw=True`: Flush draw + straight draw

### 1.3 Board Texture (Textura do Board)

```python
BOARD_TEXTURES = {
    'monotone': bool,      # 3 cartas do mesmo naipe
    'two_tone': bool,      # 2 cartas de um naipe, 1 de outro
    'rainbow': bool,       # 3 naipes diferentes
    'paired': bool,        # Board com par
    'connected': bool,     # Cartas conectadas (ex: 987)
    'broadway': bool,      # Cartas altas (T+)
    'dry': bool,           # Board seco (poucas possibilidades)
    'wet': bool            # Board molhado (muitas possibilidades)
}
```

**Onde:** Calculado no `ContextExtractor` baseado nas cartas do board

### 1.4 Posições (Positions)

```python
POSITIONS = [
    'BTN',  # Button
    'SB',   # Small Blind
    'BB',   # Big Blind
    'IP',   # In Position (genérico)
    'OOP'   # Out of Position (genérico)
]
```

### 1.5 Actions (Ações)

```python
ACTIONS = [
    'check',
    'call',
    'bet',
    'raise',
    'fold',
    'all_in'
]
```

**Onde:** `src/vectorization/vectorizer.py` - encoding de ações

---

## 2. Processo de Análise

### 2.1 Pipeline ETL Completo

```
Arquivo Raw (TXT/XML)
    ↓
UnifiedParser
    ├── Detecção automática de formato
    ├── Extração de dados brutos
    └── Conversão para PHH (Poker Hand History)
    ↓
ContextExtractor
    ├── Identificação de decision points
    ├── Extração de contexto completo
    └── Criação de DecisionPoint objects
    ↓
Street Features Calculator
    ├── Avaliação de hand strength
    ├── Detecção de draws
    └── Análise de board texture
    ↓
Vectorizer
    ├── Encoding de features
    ├── Normalização de valores
    └── Criação de vector 99-dimensional
    ↓
FAISS Index
    ├── Armazenamento vetorial
    └── Busca por similaridade
```

### 2.2 Extração de Decision Points

**Arquivo:** `src/context/context_extractor.py`

Cada **Decision Point** representa um momento onde o vilão precisa tomar uma decisão e contém:

```python
@dataclass
class DecisionPoint:
    # Identificação
    decision_id: str
    hand_id: str
    villain_name: str
    step_idx: int

    # Contexto temporal
    street: str  # preflop, flop, turn, river
    action_number_in_street: int

    # Estado do jogo
    pot_bb: float
    eff_stack_bb: float
    spr: float  # Stack-to-Pot Ratio

    # Posição
    villain_position: str
    hero_position: str

    # Histórico
    preflop_sequence: List[str]
    current_street_sequence: List[str]

    # Board
    board_cards: List[str]
    board_texture: Dict

    # Mão do vilão (se conhecida)
    villain_hand: List[str]
    villain_hand_strength: str
    villain_draws: Dict

    # Ação do vilão (TARGET)
    villain_action: str
    villain_bet_size_bb: float
    villain_bet_size_pot_pct: float

    # Outcome
    went_to_showdown: bool
    villain_won: bool
```

---

## 3. Como Funciona a Detecção

### 3.1 Detecção de Flush Draw

O sistema verifica:

1. **Naipes no board:** Conta quantos de cada naipe
2. **Naipes na mão:** Verifica se vilão tem 2 cartas do mesmo naipe
3. **Regra:** Se board tem 2+ cartas do mesmo naipe E vilão tem 2 cartas desse naipe = `flush_draw = True`

**Exemplo:**
```python
Board: Kh 9h 4c
Mão vilão: Ah Qh

# Análise:
# - Board tem 2 hearts (Kh, 9h)
# - Vilão tem 2 hearts (Ah, Qh)
# - Total: 4 hearts
# Resultado: flush_draw = True (9 outs)
```

### 3.2 Detecção de Straight Draws

**OESD (Open-Ended Straight Draw):**
- Verifica se as cartas do vilão + board formam 4 cartas consecutivas
- Exemplo: JT com board KQ9 → pode fazer straight com 8 ou A

**Gutshot:**
- Verifica se falta 1 carta no meio da sequência
- Exemplo: JT com board K93 → pode fazer straight com Q

**Regras:**
```python
def detect_straight_draw(hole_cards, board_cards):
    all_cards = hole_cards + board_cards
    ranks = sorted([card_rank(c) for c in all_cards])

    # OESD: 4 cartas consecutivas
    if has_4_consecutive(ranks):
        return 'oesd'

    # Gutshot: 3 cartas consecutivas + 1 gap
    if has_gutshot_pattern(ranks):
        return 'gutshot'

    return None
```

### 3.3 Avaliação de Hand Strength

O sistema usa um **hand evaluator** baseado em regras:

```python
def evaluate_hand_strength(hole_cards, board_cards):
    all_cards = hole_cards + board_cards

    # 1. Conta frequências de ranks
    rank_counts = Counter([card_rank(c) for c in all_cards])

    # 2. Conta frequências de suits
    suit_counts = Counter([card_suit(c) for c in all_cards])

    # 3. Verifica em ordem de força (maior para menor)

    if is_straight_flush(all_cards):
        return 'STRAIGHT_FLUSH'

    if max(rank_counts.values()) == 4:
        return 'FOUR_OF_A_KIND'

    if max(rank_counts.values()) == 3 and 2 in rank_counts.values():
        return 'FULL_HOUSE'

    if max(suit_counts.values()) >= 5:
        return 'FLUSH'

    if is_straight(all_cards):
        return 'STRAIGHT'

    if max(rank_counts.values()) == 3:
        return 'THREE_OF_A_KIND'

    if list(rank_counts.values()).count(2) >= 2:
        return 'TWO_PAIR'

    if max(rank_counts.values()) == 2:
        return 'ONE_PAIR'

    return 'HIGH_CARD'
```

### 3.4 Análise de Board Texture

```python
def analyze_board_texture(board_cards):
    texture = {}

    suits = [card_suit(c) for c in board_cards]
    ranks = [card_rank(c) for c in board_cards]

    # Monotone: 3 cartas do mesmo naipe
    texture['monotone'] = max(Counter(suits).values()) == 3

    # Two-tone: 2 de um naipe
    texture['two_tone'] = max(Counter(suits).values()) == 2

    # Rainbow: 3 naipes diferentes
    texture['rainbow'] = len(set(suits)) == 3

    # Paired: Board com par
    texture['paired'] = max(Counter(ranks).values()) >= 2

    # Connected: Cartas conectadas
    sorted_ranks = sorted(ranks)
    texture['connected'] = any(
        sorted_ranks[i+1] - sorted_ranks[i] == 1
        for i in range(len(sorted_ranks)-1)
    )

    # Broadway: Cartas altas (T, J, Q, K, A)
    texture['broadway'] = any(r >= 10 for r in ranks)

    # Dry vs Wet
    draw_possibilities = (
        int(texture['monotone'] or texture['two_tone']) +  # Flush draw
        int(texture['connected']) +  # Straight draw
        int(len(set(ranks)) == 3)  # Sem pair = mais possibilidades
    )

    texture['wet'] = draw_possibilities >= 2
    texture['dry'] = not texture['wet']

    return texture
```

---

## 4. Vetorização

### 4.1 Vector de 99 Dimensões

Cada decision point é convertido em um vector de 99 dimensões:

```python
VECTOR_STRUCTURE = {
    'street': 4,              # One-hot: preflop, flop, turn, river
    'position': 5,            # One-hot: BTN, SB, BB, IP, OOP
    'preflop_aggressor': 3,   # One-hot: hero, villain, none
    'pot_size': 6,            # One-hot buckets
    'stack_size': 3,          # Normalized: low, medium, high
    'spr': 5,                 # One-hot buckets
    'aggression_level': 4,    # Normalized
    'board_texture': 7,       # Binary flags
    'action_count': 2,        # Normalized
    'draws': 4,               # Binary flags
    'board_cards': 12,        # 3 cards × 4 (rank+suit)
    'hand_strength': 9,       # One-hot categories
    'previous_hero_action': 8,# One-hot
    'bet_sizing': 6,          # One-hot buckets
    'action_sequence': 10,    # Encoded sequence
    'showdown_flag': 1,       # Binary
    'win_flag': 1             # Binary
}
# Total: 99 dimensions
```

**Onde:** `src/vectorization/vectorizer.py:48-69`

### 4.2 Exemplo de Encoding

**Hand Strength = "FLUSH":**
```python
hand_strength_vec = [0, 0, 0, 0, 0, 1, 0, 0, 0]
#                    HC P  2P 3K ST FL FH 4K SF
```

**Draws = {flush_draw: True, oesd: False}:**
```python
draws_vec = [1, 0, 0, 0]
#           FD OESD GS COMBO
```

**Board Texture = {monotone: True, wet: True}:**
```python
texture_vec = [1, 0, 0, 0, 0, 1, 0]
#             MON 2T RB PR CON DRY WET
```

---

## 5. Armazenamento dos Dados

### 5.1 Arquivos Gerados

```
dataset/
├── phh_hands/                      # PHH files convertidos
│   └── {hand_id}.phh
├── decision_points/                # Decision points extraídos
│   └── decision_points_vectorized.parquet
└── street_features.parquet         # Hand strength e draws calculados
```

### 5.2 Street Features

O arquivo `street_features.parquet` contém:

```python
STREET_FEATURES_SCHEMA = {
    'hand_id': str,
    'player': str,
    'street': str,
    'hand_strength_lbl': str,  # HIGH_CARD, ONE_PAIR, etc.
    'draw_type': str,          # 'none', 'flush_draw', 'oesd', etc.
    'fd_flag': bool,           # Flush draw flag
    'oe_flag': bool,           # OESD flag
    'gs_flag': bool            # Gutshot flag
}
```

Este arquivo é **pré-calculado** durante o pipeline ETL e depois **mergeado** com os decision points para análise.

---

## 6. Sistema de Busca por Similaridade

### 6.1 FAISS Indexing

```python
# 1. Cada decision point → vector 99D
decision_point → vectorizer → [0.1, 0.2, ..., 0.9]

# 2. Vectors agrupados por vilão
indices/
├── villain1.index      # FAISS index
├── villain1_ids.npy    # Decision IDs mapping
├── villain2.index
└── villain2_ids.npy

# 3. Busca por similaridade
query_vec = vectorizer.vectorize(new_decision_point)
distances, indices = faiss_index.search(query_vec, k=10)
similar_decisions = [decision_points[i] for i in indices]
```

### 6.2 Métricas de Similaridade

O FAISS usa **distância L2 (euclidiana)** no espaço vetorial 99D:

```python
distance = sqrt(sum((a[i] - b[i])^2 for i in range(99)))
```

Quanto **menor** a distância, **mais similar** o decision point.

---

## 7. Range Analysis

### 7.1 Como Funciona

O endpoint `/search/range-analysis` analisa **quais mãos o vilão realmente tinha** em situações similares:

```python
# 1. Filtra decision points
filtered = df[
    (df['villain_name'] == 'Player1') &
    (df['street'] == 'flop') &
    (df['villain_action'] == 'bet') &
    (df['pot_bb'] >= 10) &
    (df['pot_bb'] <= 30)
]

# 2. Agrupa por hand strength
distribution = filtered['villain_hand_strength'].value_counts()

# Resultado:
{
    'FLUSH': 45.2%,        # Value bets
    'TWO_PAIR': 28.6%,     # Value bets
    'ONE_PAIR': 14.3%,     # Thin value / bluffs
    'HIGH_CARD': 11.9%     # Pure bluffs
}
```

### 7.2 Categorias de Range

```python
def get_range_category(hand_strength, draws):
    has_draw = draws and draws != 'none'

    # Value hands
    if hand_strength in ['FLUSH', 'STRAIGHT', 'FULL_HOUSE', 'FOUR_OF_A_KIND', 'STRAIGHT_FLUSH']:
        return 'Nuts / Strong Value'

    if hand_strength in ['THREE_OF_A_KIND', 'TWO_PAIR']:
        return 'Value'

    # Showdown value
    if hand_strength == 'ONE_PAIR':
        if has_draw:
            return 'Semi-Bluff (Pair + Draw)'
        return 'Showdown Value'

    # Bluffs
    if has_draw:
        return 'Draw / Semi-Bluff'

    return 'Pure Bluff'
```

---

## 8. Exemplo Completo

### Input:
```python
Villain: "Player1"
Street: "flop"
Action: "bet"
Pot: 20 BB
Board: Kh 9h 4c
```

### Processamento:

1. **Busca decision points similares:**
   - Street = flop ✓
   - Pot 10-30 BB ✓
   - Action = bet ✓

2. **Encontra 14 samples:**
   ```
   Hand #1: Ah Qh → FLUSH_DRAW → bet 15 BB → won
   Hand #2: Kc Ks → THREE_OF_A_KIND → bet 18 BB → won
   Hand #3: Qd Jd → HIGH_CARD → bet 12 BB → lost
   ...
   ```

3. **Análise de distribuição:**
   ```json
   {
     "hand_strength_distribution": {
       "STRAIGHT_FLUSH": 92.9%,  // Nuts
       "HIGH_CARD": 7.1%          // Bluffs
     },
     "draws_distribution": {
       "flush_draw": 50%,
       "none": 50%
     },
     "total_samples": 14
   }
   ```

---

## 9. Resumo

### Sistema Baseado em Regras

✅ **Sim, é baseado em regras** definidas no código

### Glossário Completo

- **9 hand strengths** (HIGH_CARD até STRAIGHT_FLUSH)
- **4 draw types** (flush, OESD, gutshot, combo)
- **8 board textures** (monotone, paired, connected, etc.)
- **5 posições** (BTN, SB, BB, IP, OOP)
- **6 ações** (check, call, bet, raise, fold, all_in)

### Processo de Detecção

1. **Hand Strength:** Avaliador baseado em contagem de ranks e suits
2. **Draws:** Detecção por padrões de cartas consecutivas e naipes
3. **Board Texture:** Análise combinatória das características do board

### Vetorização

- Vector de **99 dimensões**
- Encoding: One-hot, binary flags, normalized floats
- Armazenamento: FAISS indices para busca vetorial

### Range Analysis

- Agrupa mãos reais por situação
- Mostra distribuição de hand strengths
- Categoriza em value/bluff/semi-bluff

---

## 10. Arquivos Relevantes

| Arquivo | Responsabilidade |
|---------|------------------|
| `src/context/context_extractor.py` | Extração de decision points |
| `src/vectorization/vectorizer.py` | Vetorização e encoding |
| `src/api/range_analysis.py` | Análise de range |
| `dataset/street_features.parquet` | Hand strength pré-calculado |
| `src/indexing/build_indices.py` | Construção de índices FAISS |

---

**Sistema 100% baseado em regras determin��sticas, sem machine learning.**
