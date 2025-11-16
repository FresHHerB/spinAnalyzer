# 📊 Análise Comparativa: PokerStars vs iPoker

**Data:** 14/11/2025
**Objetivo:** Entender as diferenças estruturais entre formatos de histórico e propor estratégia de conversão unificada para PHH

---

## 1. Visão Geral dos Formatos

### 1.1. Características Gerais

| Aspecto | PokerStars | iPoker |
|---------|------------|--------|
| **Formato** | Texto plano (.txt) | XML estruturado (.xml) |
| **Encoding** | UTF-8 com BOM | UTF-8 |
| **Estrutura** | Linha por linha, marcadores textuais | Tags XML hierárquicas |
| **Tamanho Médio** | ~11.7MB (14,158 mãos) | ~25KB (17 mãos) |
| **Parsing** | Regex + parsing textual | ElementTree XML |
| **Delimitadores** | Marcadores `***` | Tags XML `<round>`, `<action>` |
| **Complexidade** | Média (padrões textuais) | Baixa (estrutura bem definida) |

---

## 2. Análise Estrutural Detalhada

### 2.1. Cabeçalho da Mão

#### **PokerStars:**
```
PokerStars Hand #255558656104: Tournament #3875187542, $4.60+$0.40 USD Hold'em No Limit - Level I (10/20) - 2025/04/02 9:23:50 ET
Table '3875187542 1' 3-max Seat #1 is the button
```

**Campos Extraíveis:**
- ✅ `hand_id`: `255558656104`
- ✅ `tournament_id`: `3875187542`
- ✅ `buyin`: `$4.60+$0.40 USD`
- ✅ `game_type`: `Hold'em No Limit`
- ✅ `level`: `Level I (10/20)` → SB=10, BB=20
- ✅ `timestamp`: `2025/04/02 9:23:50 ET`
- ✅ `table_name`: `3875187542 1`
- ✅ `max_players`: `3-max`
- ✅ `button_seat`: `Seat #1`

**Parsing:**
```python
import re

header_pattern = r"PokerStars Hand #(\d+): Tournament #(\d+), \$([0-9.]+)\+\$([0-9.]+) USD .* Level [IVX]+ \((\d+)/(\d+)\) - (.+)"
match = re.search(header_pattern, line)

hand_id = match.group(1)
tournament_id = match.group(2)
buyin_prize = match.group(3)
buyin_fee = match.group(4)
sb = int(match.group(5))
bb = int(match.group(6))
timestamp = match.group(7)
```

#### **iPoker:**
```xml
<game gamecode="11514533315">
  <general>
    <startdate>2025-06-16 01:28:37</startdate>
    <round>1</round>
    ...
  </general>
```

**Campos Extraíveis:**
- ✅ `hand_id`: `gamecode="11514533315"`
- ✅ `timestamp`: `<startdate>`
- ❌ `tournament_id`: Disponível apenas no `<session>` pai
- ❌ `buyin`: Disponível apenas no `<session>` pai
- ❌ `level/blinds`: Extraído de ações tipo `1` (SB) e `2` (BB)

**Diferença Chave:**
- **PokerStars**: Informações completas no cabeçalho de cada mão
- **iPoker**: Informações distribuídas entre `<session>` e `<game>`

---

### 2.2. Jogadores

#### **PokerStars:**
```
Seat 1: bandy752 (500 in chips)
Seat 2: FresHHerB (500 in chips)
Seat 3: d1mitris (500 in chips)
```

**Estrutura:**
- Formato: `Seat {number}: {name} ({stack} in chips)`
- Button: Identificado na linha da tabela `Seat #1 is the button`
- Hero: Identificado em `Dealt to {hero_name} [cards]`

**Parsing:**
```python
player_pattern = r"Seat (\d+): (\w+) \((\d+) in chips\)"
for line in lines:
    match = re.search(player_pattern, line)
    if match:
        seat = int(match.group(1))
        name = match.group(2)
        stack = int(match.group(3))
```

#### **iPoker:**
```xml
<players>
  <player seat="10" name="GenaroM" chips="500" dealer="0" win="0"
          bet="320" muck="1" rebuy="0" addon="0" merge="0"
          rebuychips="0" reg_code="8384733613"/>
  <player seat="3" name="oreiasccp" chips="500" dealer="1" win="650"
          bet="320" muck="0" .../>
  <player seat="6" name="domikan1" chips="500" dealer="0" .../>
</players>
```

**Estrutura:**
- Formato: Atributos XML estruturados
- Button: `dealer="1"`
- Hero: `<nickname>` no `<session>`
- **Extra:** `win`, `bet`, `muck`, `rebuy`, `addon` (informações de fim de mão)

**Diferença Chave:**
- **PokerStars**: Informações básicas, outcome em seção separada
- **iPoker**: Informações completas (incluindo resultado) no nó do jogador

---

### 2.3. Blinds e Antes

#### **PokerStars:**
```
FresHHerB: posts small blind 10
d1mitris: posts big blind 20
```

**Padrão:**
- SB: `{player}: posts small blind {amount}`
- BB: `{player}: posts big blind {amount}`
- Antes (quando existem): `{player}: posts the ante {amount}`

**Parsing:**
```python
if "posts small blind" in line:
    player, amount = parse_action(line, r"(\w+): posts small blind (\d+)")
    sb = int(amount)

if "posts big blind" in line:
    player, amount = parse_action(line, r"(\w+): posts big blind (\d+)")
    bb = int(amount)
```

#### **iPoker:**
```xml
<round no="0">
  <action no="1" player="domikan1" type="1" sum="10"/>  <!-- SB -->
  <action no="2" player="GenaroM" type="2" sum="20"/>   <!-- BB -->
  <action no="3" player="oreiasccp" type="15" sum="5"/> <!-- Ante -->
</round>
```

**Padrão:**
- SB: `type="1"`
- BB: `type="2"`
- Ante: `type="15"`
- Round `no="0"` sempre contém blinds/antes

**Diferença Chave:**
- **PokerStars**: Descrição textual clara
- **iPoker**: Códigos numéricos, necessita mapeamento

---

### 2.4. Cartas do Jogador (Hole Cards)

#### **PokerStars:**
```
*** HOLE CARDS ***
Dealt to FresHHerB [3h 2s]
```

**Formato:**
- Marcador: `*** HOLE CARDS ***`
- Padrão: `Dealt to {hero} [{card1} {card2}]`
- Cartas: `{rank}{suit}` (3h = 3 de copas)
- **Apenas cartas do hero são mostradas inicialmente**

**Parsing:**
```python
if "*** HOLE CARDS ***" in line:
    next_line = next(iterator)
    match = re.search(r"Dealt to (\w+) \[(.+?)\]", next_line)
    hero = match.group(1)
    cards_str = match.group(2)  # "3h 2s"
    cards = cards_str.split()   # ['3h', '2s']
```

#### **iPoker:**
```xml
<round no="1">
  <cards type="Pocket" player="GenaroM">S9 H4</cards>
  <cards type="Pocket" player="domikan1">X X</cards>
  <cards type="Pocket" player="oreiasccp">D5 DQ</cards>
</round>
```

**Formato:**
- `type="Pocket"` indica hole cards
- Cartas conhecidas: `{suit}{rank}` (S9 = 9 de espadas, D5 = 5 de ouros)
- Cartas desconhecidas: `X X`
- **IMPORTANTE**: Formato invertido vs PokerStars!
  - **iPoker**: Suit primeiro (S9, D5, H4, C7)
  - **PokerStars**: Rank primeiro (9s, 5d, 4h, 7c)

**Conversão Necessária:**
```python
def convert_ipoker_card(card):
    """Converte S9 (iPoker) para 9s (padrão)"""
    if card == 'X':
        return None
    suit_map = {'S': 's', 'H': 'h', 'D': 'd', 'C': 'c'}
    suit = suit_map[card[0]]
    rank = card[1:].replace('10', 'T')
    return f"{rank}{suit}"

# S9 → 9s
# D10 → Td
# CA → Ac
```

---

### 2.5. Board Cards (Comunitárias)

#### **PokerStars:**
```
*** FLOP *** [Qc 9c Td]
*** TURN *** [Qc 9c Td] [Jc]
*** RIVER *** [Qc 9c Td Jc] [6s]
```

**Formato:**
- Marcadores claros: `*** FLOP ***`, `*** TURN ***`, `*** RIVER ***`
- Turn e River mostram board cumulativo + nova carta entre `[]`
- Cartas: `{rank}{suit}` (padrão PokerStars)

**Parsing:**
```python
if "*** FLOP ***" in line:
    match = re.search(r"\[(.+?)\]", line)
    flop_cards = match.group(1).split()  # ['Qc', '9c', 'Td']

if "*** TURN ***" in line:
    # Extrai apenas a nova carta (2º set de colchetes)
    matches = re.findall(r"\[(.+?)\]", line)
    turn_card = matches[1]  # 'Jc'

if "*** RIVER ***" in line:
    matches = re.findall(r"\[(.+?)\]", line)
    river_card = matches[1]  # '6s'
```

#### **iPoker:**
```xml
<round no="2">
  <cards type="Flop">HJ S5 C9</cards>
  ...
</round>
<round no="3">
  <cards type="Turn">H5</cards>
  ...
</round>
<round no="4">
  <cards type="River">CK</cards>
  ...
</round>
```

**Formato:**
- `type="Flop"`, `type="Turn"`, `type="River"`
- Flop: 3 cartas separadas por espaço
- Turn/River: Apenas a nova carta
- Formato: `{suit}{rank}` (invertido)

**Parsing:**
```python
for round_node in game.findall("round"):
    round_no = round_node.get("no")
    for cards_node in round_node.findall("cards"):
        card_type = cards_node.get("type")
        cards_str = cards_node.text  # "HJ S5 C9"

        if card_type == "Flop":
            flop_cards = [convert_ipoker_card(c) for c in cards_str.split()]
        elif card_type == "Turn":
            turn_card = convert_ipoker_card(cards_str.strip())
        elif card_type == "River":
            river_card = convert_ipoker_card(cards_str.strip())
```

---

### 2.6. Ações (Actions)

#### **PokerStars:**
```
bandy752: raises 20 to 40
FresHHerB: folds
d1mitris: raises 460 to 500 and is all-in
bandy752: folds
Uncalled bet (460) returned to d1mitris
d1mitris collected 90 from pot
```

**Tipos de Ação:**
- `folds`
- `checks`
- `calls {amount}`
- `bets {amount}`
- `raises {from_amount} to {to_amount}`
- `raises {from_amount} to {to_amount} and is all-in`
- `calls {amount} and is all-in`

**Parsing:**
```python
def parse_pokerstars_action(line):
    player = line.split(':')[0]
    action_text = line.split(':')[1].strip()

    if "folds" in action_text:
        return {'player': player, 'action': 'fold', 'amount': 0}

    if "checks" in action_text:
        return {'player': player, 'action': 'check', 'amount': 0}

    if "calls" in action_text:
        match = re.search(r"calls (\d+)", action_text)
        amount = int(match.group(1))
        is_allin = "all-in" in action_text
        return {
            'player': player,
            'action': 'call_allin' if is_allin else 'call',
            'amount': amount
        }

    if "bets" in action_text:
        match = re.search(r"bets (\d+)", action_text)
        return {'player': player, 'action': 'bet', 'amount': int(match.group(1))}

    if "raises" in action_text:
        match = re.search(r"raises (\d+) to (\d+)", action_text)
        is_allin = "all-in" in action_text
        return {
            'player': player,
            'action': 'raise_allin' if is_allin else 'raise',
            'amount': int(match.group(2))  # Total amount
        }
```

#### **iPoker:**
```xml
<action no="3" player="oreiasccp" type="23" sum="40"/>   <!-- raise -->
<action no="4" player="domikan1" type="0" sum="0"/>     <!-- fold -->
<action no="5" player="GenaroM" type="3" sum="20"/>     <!-- call -->
<action no="6" player="GenaroM" type="4" sum="0"/>      <!-- check -->
<action no="7" player="oreiasccp" type="5" sum="20"/>   <!-- bet -->
<action no="8" player="GenaroM" type="7" sum="180"/>    <!-- call allin -->
```

**Mapeamento de Códigos:**
```python
IPOKER_ACTION_MAP = {
    "0": "fold",
    "1": "posts_sb",
    "2": "posts_bb",
    "3": "call",
    "4": "check",
    "5": "bet",
    "7": "call_allin",
    "15": "ante",
    "23": "raise",
}
```

**Diferença Chave:**
- **PokerStars**: Texto descritivo, valores absolutos, indica all-in
- **iPoker**: Códigos numéricos, necessita lógica para detectar all-in (comparar `sum` com stack)

---

### 2.7. Showdown

#### **PokerStars:**
```
*** SHOW DOWN ***
d1mitris: shows [Jd 2d] (a pair of Jacks)
FresHHerB: mucks hand
d1mitris collected 160 from pot

*** SUMMARY ***
Total pot 160 | Rake 0
Board [Qd 5h Js 3h 6s]
Seat 2: FresHHerB (button) (small blind) mucked [9h 7c]
Seat 3: d1mitris (big blind) showed [Jd 2d] and won (160) with a pair of Jacks
```

**Informações Disponíveis:**
- ✅ Cartas mostradas: `shows [{cards}] ({hand description})`
- ✅ Cartas mucked: `mucks hand` (podem aparecer no SUMMARY)
- ✅ Vencedor: `collected {amount} from pot`
- ✅ Hand ranking: `(a pair of Jacks)`
- ✅ Board completo no summary

**Parsing:**
```python
if "*** SHOW DOWN ***" in line:
    in_showdown = True

if in_showdown:
    # Cartas mostradas
    if "shows" in line:
        match = re.search(r"(\w+): shows \[(.+?)\] \((.+?)\)", line)
        player = match.group(1)
        cards = match.group(2).split()
        hand_desc = match.group(3)

    # Vencedor
    if "collected" in line:
        match = re.search(r"(\w+) collected (\d+) from pot", line)
        winner = match.group(1)
        pot = int(match.group(2))
```

#### **iPoker:**
```xml
<player seat="3" name="oreiasccp" chips="500" dealer="1"
        win="650" bet="320" muck="0" .../>
<player seat="10" name="GenaroM" chips="500" dealer="0"
        win="0" bet="320" muck="1" .../>
```

**Informações Disponíveis:**
- ✅ Vencedor: `win > 0`
- ✅ Se mostrou: `muck="0"` (mostrou), `muck="1"` (não mostrou)
- ❌ Hand ranking: **NÃO disponível no XML**
- ❌ Cartas do vilão: Apenas se `muck="0"` E cartas foram gravadas

**Parsing:**
```python
for player_node in players_node.findall("player"):
    player_name = player_node.get('name')
    win_amount = float(player_node.get('win', '0'))
    muck = player_node.get('muck') == '1'

    if win_amount > 0:
        winners.append(player_name)

    if not muck and player_name in pocket_cards:
        # Jogador mostrou as cartas
        showdown_hands[player_name] = pocket_cards[player_name]
```

**Diferença Chave:**
- **PokerStars**: Showdown detalhado com hand rankings
- **iPoker**: Informação binária (ganhou/perdeu, mostrou/mucou)

---

## 3. Tabela Comparativa Completa

| Feature | PokerStars | iPoker | Complexidade Conversão |
|---------|------------|--------|------------------------|
| **Hand ID** | Único por mão | Único por mão | ✅ Trivial |
| **Timestamp** | Texto no cabeçalho | Tag XML | ✅ Trivial |
| **Tournament Info** | No cabeçalho | No `<session>` | 🟡 Requer contexto |
| **Blinds/Antes** | Texto descritivo | Códigos numéricos | 🟡 Mapeamento |
| **Jogadores** | Lista textual | XML estruturado | ✅ Direto |
| **Button** | Texto `Seat #X is the button` | `dealer="1"` | ✅ Trivial |
| **Hero** | `Dealt to {name}` | `<nickname>` | 🟡 Requer contexto |
| **Hole Cards** | `[{rank}{suit}]` | `{suit}{rank}` | 🔴 **INVERSÃO** |
| **Board** | `[cards]` cumulativo | Tags por street | 🟡 Reconstrução |
| **Actions** | Texto descritivo | Códigos numéricos | 🟡 Mapeamento |
| **All-in Detection** | Explícito `and is all-in` | Implícito (sum = stack) | 🔴 Lógica complexa |
| **Showdown Cards** | Detalhado no SHOW DOWN | `muck` attribute | 🟡 Estratégias diferentes |
| **Hand Ranking** | Texto `(pair of Jacks)` | ❌ Ausente | ❌ Calcular manualmente |
| **Pot Size** | `Total pot X` | Soma de `win` | ✅ Trivial |
| **Rake** | Explícito | Implícito | 🟡 Calcular |

**Legenda:**
- ✅ Trivial: Conversão direta
- 🟡 Médio: Requer lógica adicional
- 🔴 Complexo: Transformação não-trivial

---

## 4. Estratégia de Conversão PokerStars → PHH

### 4.1. Arquitetura Proposta

```
┌──────────────────────────────────────────────────────┐
│  Input: handHistory-147171.txt (14,158 mãos)        │
└──────────────────────────────────────────────────────┘
                     ↓
┌──────────────────────────────────────────────────────┐
│  ETAPA 1: Splitting                                  │
│  - Identificar delimitador de mãos                   │
│  - Separar em blocos individuais                     │
│  - Output: List[str] (uma string por mão)           │
└──────────────────────────────────────────────────────┘
                     ↓
┌──────────────────────────────────────────────────────┐
│  ETAPA 2: Parsing por Seção                         │
│  - Header (hand_id, blinds, timestamp)              │
│  - Players (seat, name, stack, button)              │
│  - Preflop (blinds, antes, hole cards, ações)       │
│  - Flop (board, ações)                              │
│  - Turn (board, ações)                              │
│  - River (board, ações)                             │
│  - Showdown (cartas, vencedores)                    │
│  - Summary (validação)                              │
└──────────────────────────────────────────────────────┘
                     ↓
┌──────────────────────────────────────────────────────┐
│  ETAPA 3: Normalização para PHH                     │
│  - Converter formatos de cartas                      │
│  - Mapear ações para vocabulário PHH                │
│  - Reconstruir cronologia                           │
│  - Calcular hand rankings (se necessário)           │
└──────────────────────────────────────────────────────┘
                     ↓
┌──────────────────────────────────────────────────────┐
│  Output: {hand_id}.phh (formato TOML)               │
└──────────────────────────────────────────────────────┘
```

### 4.2. Implementação - Splitting

```python
def split_pokerstars_hands(file_path):
    """
    Separa arquivo PokerStars em mãos individuais.

    Returns:
        List[str]: Lista de strings, cada uma contendo uma mão completa
    """
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        content = f.read()

    # Padrão de delimitador: "Hand #X:" seguido de linha vazia
    # Mas cuidado: há "Hand #X:" no summary também!

    # Estratégia: Split por "PokerStars Hand #" (início real de mão)
    hands = []
    current_hand = []

    for line in content.split('\n'):
        if line.startswith('PokerStars Hand #'):
            # Nova mão começou
            if current_hand:
                hands.append('\n'.join(current_hand))
            current_hand = [line]
        else:
            current_hand.append(line)

    # Adiciona última mão
    if current_hand:
        hands.append('\n'.join(current_hand))

    return hands

# Uso
hands = split_pokerstars_hands('handHistory-147171.txt')
print(f"Total mãos: {len(hands)}")  # 14,158
```

### 4.3. Implementação - Parser de Cabeçalho

```python
import re
from datetime import datetime

def parse_pokerstars_header(hand_text):
    """
    Extrai metadados do cabeçalho.
    """
    lines = hand_text.split('\n')

    # Linha 1: PokerStars Hand #...
    header_line = lines[0]

    # Pattern complexo para capturar todos os campos
    pattern = r"PokerStars Hand #(\d+): Tournament #(\d+), \$([0-9.]+)\+\$([0-9.]+) USD (.+?) - Level ([IVX]+) \((\d+)/(\d+)\) - (.+)"
    match = re.search(pattern, header_line)

    if not match:
        raise ValueError(f"Header inválido: {header_line}")

    metadata = {
        'hand_id': match.group(1),
        'tournament_id': match.group(2),
        'buyin_prize': float(match.group(3)),
        'buyin_fee': float(match.group(4)),
        'game_type': match.group(5),  # "Hold'em No Limit"
        'level': match.group(6),      # "I", "II", "III"
        'sb': int(match.group(7)),
        'bb': int(match.group(8)),
        'timestamp': match.group(9),  # "2025/04/02 9:23:50 ET"
    }

    # Linha 2: Table info
    table_line = lines[1]
    table_match = re.search(r"Table '(.+?)' (\d+)-max Seat #(\d+) is the button", table_line)

    metadata['table_name'] = table_match.group(1)
    metadata['max_players'] = int(table_match.group(2))
    metadata['button_seat'] = int(table_match.group(3))

    return metadata
```

### 4.4. Implementação - Parser de Jogadores

```python
def parse_pokerstars_players(hand_text):
    """
    Extrai informações dos jogadores.
    """
    players = []

    # Pattern: Seat X: PlayerName (stack in chips)
    player_pattern = r"Seat (\d+): (\w+) \((\d+) in chips\)"

    for match in re.finditer(player_pattern, hand_text):
        players.append({
            'seat': int(match.group(1)),
            'name': match.group(2),
            'stack': int(match.group(3)),
        })

    # Identificar hero (quem recebeu as cartas)
    hero_match = re.search(r"Dealt to (\w+)", hand_text)
    hero_name = hero_match.group(1) if hero_match else None

    # Marcar hero
    for player in players:
        player['is_hero'] = (player['name'] == hero_name)

    return players, hero_name
```

### 4.5. Implementação - Parser de Ações

```python
def parse_pokerstars_actions(hand_text):
    """
    Extrai todas as ações, organizadas por street.
    """
    actions = {
        'preflop': [],
        'flop': [],
        'turn': [],
        'river': []
    }

    current_street = None

    for line in hand_text.split('\n'):
        # Detectar mudança de street
        if "*** HOLE CARDS ***" in line:
            current_street = 'preflop'
            continue
        elif "*** FLOP ***" in line:
            current_street = 'flop'
            # Extrair board
            match = re.search(r"\[(.+?)\]", line)
            if match:
                flop_cards = match.group(1).split()
            continue
        elif "*** TURN ***" in line:
            current_street = 'turn'
            continue
        elif "*** RIVER ***" in line:
            current_street = 'river'
            continue
        elif "*** SHOW DOWN ***" in line or "*** SUMMARY ***" in line:
            break

        # Parsear ações (ignorar linhas de blind posts e dealt to)
        if current_street and ':' in line and not line.startswith('Seat'):
            # Linha de ação: "PlayerName: action details"
            parts = line.split(':', 1)
            if len(parts) == 2:
                player = parts[0].strip()
                action_text = parts[1].strip()

                action = parse_action_text(action_text, player)
                if action:
                    actions[current_street].append(action)

    return actions

def parse_action_text(text, player):
    """
    Converte texto de ação em estrutura.
    """
    # Implementação detalhada vista anteriormente
    if "folds" in text:
        return {'player': player, 'action': 'fold', 'amount': 0}

    if "checks" in text:
        return {'player': player, 'action': 'check', 'amount': 0}

    # ... outros tipos
```

### 4.6. Implementação - Conversão para PHH

```python
import tomli_w

def convert_pokerstars_to_phh(hand_text, output_dir):
    """
    Converte uma mão PokerStars para formato PHH.
    """
    # 1. Parsear todas as seções
    metadata = parse_pokerstars_header(hand_text)
    players, hero_name = parse_pokerstars_players(hand_text)
    actions = parse_pokerstars_actions(hand_text)
    board = extract_board(hand_text)
    showdown = parse_showdown(hand_text)

    # 2. Construir estrutura PHH
    phh_data = {
        'metadata': {
            'hand_id': metadata['hand_id'],
            'timestamp': metadata['timestamp'],
            'game': 'NLHE',
            'room': 'PokerStars',
            'tournament_id': metadata['tournament_id'],
            'sb': metadata['sb'],
            'bb': metadata['bb'],
            'ante': 0,  # Extrair se presente
            'hero': hero_name,
        },
        'table': {
            'name': metadata['table_name'],
            'size': metadata['max_players'],
        },
        'players': [],
        'actions': [],
        'showdown': {
            'winners': []
        }
    }

    # 3. Adicionar jogadores
    for player in players:
        phh_data['players'].append({
            'name': player['name'],
            'seat': player['seat'],
            'stack': player['stack'],
            'is_btn': (player['seat'] == metadata['button_seat']),
        })

    # 4. Reconstruir cronologia de ações
    # (combinando blinds, hole cards, board, ações de cada street)
    for street, street_actions in actions.items():
        for action in street_actions:
            phh_data['actions'].append({
                'event': 'action',
                'street': street,
                'player': action['player'],
                'action': action['action'],
                'amount': action['amount'],
            })

    # 5. Adicionar showdown
    if showdown:
        phh_data['showdown']['winners'] = showdown['winners']
        if 'hands' in showdown:
            phh_data['showdown']['hands'] = showdown['hands']

    # 6. Salvar como .phh
    output_path = output_dir / f"{metadata['hand_id']}.phh"
    with open(output_path, 'wb') as f:
        tomli_w.dump(phh_data, f)

    return output_path
```

---

## 5. Filtros para Heads-Up

### 5.1. Detecção de HU

**PokerStars:**
```python
def is_heads_up(hand_text):
    """
    Verifica se a mão é Heads-Up.
    """
    # Contar quantos jogadores sentaram
    player_count = len(re.findall(r"Seat \d+:", hand_text))

    # HU: exatamente 2 jogadores
    return player_count == 2
```

**iPoker:**
```python
def is_heads_up_ipoker(game_node):
    """
    Verifica se é HU no formato iPoker.
    """
    players_node = game_node.find("./general/players")
    if players_node is None:
        return False

    player_count = len(players_node.findall("player"))
    return player_count == 2
```

### 5.2. Processamento em Batch

```python
from pathlib import Path
from tqdm import tqdm

def process_pokerstars_file(input_file, output_dir):
    """
    Processa arquivo completo do PokerStars.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True, parents=True)

    # 1. Split em mãos individuais
    hands = split_pokerstars_hands(input_file)
    print(f"Total de mãos: {len(hands)}")

    # 2. Filtrar apenas HU
    hu_hands = [h for h in hands if is_heads_up(h)]
    print(f"Mãos HU: {len(hu_hands)} ({len(hu_hands)/len(hands)*100:.1f}%)")

    # 3. Converter para PHH
    converted = 0
    errors = 0

    for hand_text in tqdm(hu_hands, desc="Converting to PHH"):
        try:
            convert_pokerstars_to_phh(hand_text, output_dir)
            converted += 1
        except Exception as e:
            errors += 1
            # Log erro
            print(f"Erro: {e}")

    print(f"\n✅ Conversão concluída:")
    print(f"  - Convertidas: {converted}")
    print(f"  - Erros: {errors}")
    print(f"  - Taxa de sucesso: {converted/(converted+errors)*100:.1f}%")

# Uso
process_pokerstars_file(
    'handHistory-147171.txt',
    'dataset/phh_hands_pokerstars/'
)
```

---

## 6. Desafios Específicos do PokerStars

### 6.1. Variações de Formato

**Problema:** PokerStars tem variações sutis dependendo do tipo de jogo:

1. **Cash Games vs Tournaments:**
   ```
   # Tournament
   PokerStars Hand #XXX: Tournament #YYY, $X+$Y USD ...

   # Cash Game
   PokerStars Hand #XXX: Hold'em No Limit ($0.05/$0.10 USD) ...
   ```

2. **Zoom/Fast Poker:**
   ```
   PokerStars Zoom Hand #XXX: ...
   ```

3. **Spin & Go:**
   ```
   PokerStars Hand #XXX: Tournament #YYY, $1+$0 USD ...
   Spin & Go #YYY, $1+$0
   ```

**Solução:** Regex flexível com grupos opcionais

```python
# Pattern universal
header_pattern = r"PokerStars(?: Zoom)? Hand #(\d+): (?:Tournament #(\d+), )?(.*?) - (.+)"
```

### 6.2. Múltiplos Idiomas

**Problema:** PokerStars exporta em diferentes idiomas:

```
# Inglês
Dealt to Hero [Kh As]
Hero: folds

# Português
Distribuídas para Hero [Kh As]
Hero: desiste

# Espanhol
Repartió a Hero [Kh As]
Hero: se retira
```

**Solução:** Detectar idioma e usar dicionário de traduções

```python
LANGUAGE_PATTERNS = {
    'en': {
        'dealt': 'Dealt to',
        'folds': 'folds',
        'checks': 'checks',
        'calls': 'calls',
        'raises': 'raises',
        'bets': 'bets',
    },
    'pt': {
        'dealt': 'Distribuídas para',
        'folds': 'desiste',
        'checks': 'passa',
        'calls': 'paga',
        'raises': 'aumenta',
        'bets': 'aposta',
    }
}

def detect_language(hand_text):
    if 'Dealt to' in hand_text:
        return 'en'
    elif 'Distribuídas para' in hand_text:
        return 'pt'
    # ... outros idiomas
```

### 6.3. Cartas Não Mostradas

**Problema:** Quando um jogador muca (não mostra), PokerStars pode ou não revelar:

```
# Caso 1: Não revela
Hero: mucks hand

# Caso 2: Revela no summary
Seat 1: Hero mucked [9h 7c]

# Caso 3: Não mostra de jeito nenhum
Hero: doesn't show hand
```

**Solução:** Tentar extrair do SUMMARY

```python
def extract_mucked_cards(hand_text, player_name):
    """
    Tenta encontrar cartas mucked no summary.
    """
    # Pattern: Seat X: PlayerName mucked [cards]
    pattern = rf"Seat \d+: {re.escape(player_name)} mucked \[(.+?)\]"
    match = re.search(pattern, hand_text)

    if match:
        return match.group(1).split()

    return None
```

---

## 7. Validação e Testes

### 7.1. Test Cases

```python
# Test 1: Mão simples preflop fold
test_hand_1 = """
PokerStars Hand #255558656104: Tournament #3875187542, $4.60+$0.40 USD Hold'em No Limit - Level I (10/20) - 2025/04/02 9:23:50 ET
Table '3875187542 1' 3-max Seat #1 is the button
Seat 1: bandy752 (500 in chips)
Seat 2: FresHHerB (500 in chips)
FresHHerB: posts small blind 10
bandy752: posts big blind 20
*** HOLE CARDS ***
Dealt to FresHHerB [3h 2s]
FresHHerB: folds
bandy752 collected 10 from pot
*** SUMMARY ***
Total pot 10 | Rake 0
Seat 1: bandy752 (button) (big blind) collected (10)
Seat 2: FresHHerB (small blind) folded before Flop
"""

# Test 2: Mão com showdown
test_hand_2 = """
PokerStars Hand #255558667663: Tournament #3875187542, $4.60+$0.40 USD Hold'em No Limit - Level I (10/20) - 2025/04/02 9:25:06 ET
Table '3875187542 1' 3-max Seat #2 is the button
Seat 1: bandy752 (490 in chips)
Seat 2: d1mitris (640 in chips)
d1mitris: posts small blind 10
bandy752: posts big blind 20
*** HOLE CARDS ***
Dealt to FresHHerB [3d 9c]
d1mitris: calls 10
bandy752: checks
*** FLOP *** [Jd 6d Ad]
d1mitris: checks
bandy752: bets 20
d1mitris: calls 20
*** TURN *** [Jd 6d Ad] [7s]
d1mitris: bets 40
bandy752: calls 40
*** RIVER *** [Jd 6d Ad 7s] [7c]
d1mitris: checks
bandy752: bets 80
d1mitris: raises 100 to 180
bandy752: raises 230 to 410 and is all-in
d1mitris: calls 230
*** SHOW DOWN ***
bandy752: shows [Qs 7d] (three of a kind, Sevens)
d1mitris: shows [Qd 9d] (a flush, Ace high)
d1mitris collected 980 from pot
*** SUMMARY ***
Total pot 980 | Rake 0
Board [Jd 6d Ad 7s 7c]
Seat 1: bandy752 (big blind) showed [Qs 7d] and lost with three of a kind, Sevens
Seat 2: d1mitris (button) (small blind) showed [Qd 9d] and won (980) with a flush, Ace high
"""

def test_parser():
    """
    Testa conversão completa.
    """
    # Test parsing
    metadata1 = parse_pokerstars_header(test_hand_1)
    assert metadata1['hand_id'] == '255558656104'
    assert metadata1['sb'] == 10
    assert metadata1['bb'] == 20

    players1, hero1 = parse_pokerstars_players(test_hand_1)
    assert len(players1) == 2
    assert hero1 == 'FresHHerB'

    # Test HU detection
    assert is_heads_up(test_hand_1) == True

    # Test showdown
    showdown2 = parse_showdown(test_hand_2)
    assert 'd1mitris' in showdown2['winners']
    assert len(showdown2['hands']) == 2

    print("✅ Todos os testes passaram!")
```

---

## 8. Estatísticas Estimadas

### 8.1. Volume Esperado

**Arquivo Analisado:**
- Tamanho: 11.7MB
- Total de mãos: 14,158
- Formato: 3-max (Spin & Go)

**Estimativa de HU:**
```python
# Assumindo distribuição típica de Spin & Go 3-max:
# - Início: 3 jogadores
# - Após eliminação 1: HU começa
# - Duração média: ~40% das mãos são HU

total_hands = 14158
estimated_hu_pct = 0.40
estimated_hu_hands = int(total_hands * estimated_hu_pct)

print(f"Estimativa de mãos HU: {estimated_hu_hands} (~{estimated_hu_pct*100}%)")
# Output: ~5,663 mãos HU
```

**Validação:** Processar arquivo completo e contar

---

## 9. Roadmap de Implementação

### Fase 1: Parser Básico (1 semana)
- [ ] Implementar `split_pokerstars_hands()`
- [ ] Implementar `parse_pokerstars_header()`
- [ ] Implementar `parse_pokerstars_players()`
- [ ] Testes unitários

### Fase 2: Parser de Ações (1 semana)
- [ ] Implementar `parse_pokerstars_actions()`
- [ ] Suporte para todas as ações (fold, check, call, bet, raise, all-in)
- [ ] Extração de board cards
- [ ] Testes com mãos complexas

### Fase 3: Showdown e Conversão PHH (3 dias)
- [ ] Implementar `parse_showdown()`
- [ ] Implementar `convert_pokerstars_to_phh()`
- [ ] Validação contra PHH standard
- [ ] Comparação com conversão iPoker (mesma estrutura)

### Fase 4: Processamento em Batch (2 dias)
- [ ] Implementar `process_pokerstars_file()`
- [ ] Filtro de HU
- [ ] Logging de erros
- [ ] Progress bar (tqdm)

### Fase 5: Validação e Unificação (3 dias)
- [ ] Processar arquivo completo (14k mãos)
- [ ] Validar % de HU real vs estimado
- [ ] Unificar com pipeline iPoker existente
- [ ] Documentação completa

**Total Estimado:** 2.5 semanas

---

## 10. Conclusão

### 10.1. Comparação Final

| Aspecto | PokerStars | iPoker | Vencedor |
|---------|------------|--------|----------|
| **Estrutura** | Texto plano | XML | 🏆 iPoker (mais fácil parsing) |
| **Completude** | Muito completa | Completa | 🏆 PokerStars (hand rankings) |
| **Formato de Cartas** | {rank}{suit} | {suit}{rank} | 🏆 PokerStars (padrão) |
| **Detecção All-in** | Explícito | Implícito | 🏆 PokerStars |
| **Volume** | 11.7MB (14k mãos) | 25KB (17 mãos) | 🏆 PokerStars |
| **Padronização** | Consistente | Consistente | 🤝 Empate |
| **Complexidade Parser** | Média | Baixa | 🏆 iPoker |

### 10.2. Recomendação

**Estratégia Dual Parser:**

1. **Manter parser iPoker** (XML) - Já funcional
2. **Implementar parser PokerStars** (TXT) - Maior volume de dados
3. **Normalizar ambos para PHH** - Formato unificado
4. **Feature engineering idêntico** - Mesma pipeline após PHH

**Vantagem:** Duplicar volume de dados disponível mantendo qualidade

---

**FIM DA ANÁLISE**
