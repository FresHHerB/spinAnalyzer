# 🔄 Exemplo Prático de Conversão: PokerStars → PHH

**Objetivo:** Demonstrar passo a passo a conversão de uma mão real do PokerStars para o formato PHH

---

## 1. Mão Original (PokerStars)

### Input: Texto Bruto
```
PokerStars Hand #255558737638: Tournament #3875187542, $4.60+$0.40 USD Hold'em No Limit - Level III (20/40) - 2025/04/02 9:32:46 ET
Table '3875187542 1' 3-max Seat #2 is the button
Seat 2: FresHHerB (590 in chips)
Seat 3: d1mitris (910 in chips)
FresHHerB: posts small blind 20
d1mitris: posts big blind 40
*** HOLE CARDS ***
Dealt to FresHHerB [Jh Js]
FresHHerB: calls 20
d1mitris: checks
*** FLOP *** [4c Tc Jd]
d1mitris: checks
FresHHerB: bets 40
d1mitris: calls 40
*** TURN *** [4c Tc Jd] [5h]
d1mitris: checks
FresHHerB: bets 136
d1mitris: raises 136 to 272
FresHHerB: calls 136
*** RIVER *** [4c Tc Jd 5h] [Ts]
d1mitris: bets 558 and is all-in
FresHHerB: calls 238 and is all-in
Uncalled bet (320) returned to d1mitris
*** SHOW DOWN ***
d1mitris: shows [4d 5d] (two pair, Tens and Fives)
FresHHerB: shows [Jh Js] (a full house, Jacks full of Tens)
FresHHerB collected 1180 from pot
*** SUMMARY ***
Total pot 1180 | Rake 0
Board [4c Tc Jd 5h Ts]
Seat 2: FresHHerB (button) (small blind) showed [Jh Js] and won (1180) with a full house, Jacks full of Tens
Seat 3: d1mitris (big blind) showed [4d 5d] and lost with two pair, Tens and Fives
```

---

## 2. Parsing Detalhado (Passo a Passo)

### 2.1. Extração de Metadados

**Regex aplicado:**
```python
header_pattern = r"PokerStars Hand #(\d+): Tournament #(\d+), \$([0-9.]+)\+\$([0-9.]+) USD .* Level ([IVX]+) \((\d+)/(\d+)\) - (.+)"
```

**Resultado:**
```python
metadata = {
    'hand_id': '255558737638',
    'tournament_id': '3875187542',
    'buyin_prize': 4.60,
    'buyin_fee': 0.40,
    'level': 'III',
    'sb': 20,
    'bb': 40,
    'timestamp': '2025/04/02 9:32:46 ET',
    'table_name': '3875187542 1',
    'max_players': 3,
    'button_seat': 2
}
```

### 2.2. Extração de Jogadores

**Linhas analisadas:**
```
Seat 2: FresHHerB (590 in chips)
Seat 3: d1mitris (910 in chips)
```

**Resultado:**
```python
players = [
    {
        'seat': 2,
        'name': 'FresHHerB',
        'stack': 590,
        'is_btn': True,   # Seat #2 is the button
        'is_hero': True   # Dealt to FresHHerB
    },
    {
        'seat': 3,
        'name': 'd1mitris',
        'stack': 910,
        'is_btn': False,
        'is_hero': False
    }
]
```

### 2.3. Reconstrução Cronológica

#### **Preflop:**
```
FresHHerB: posts small blind 20
d1mitris: posts big blind 40
*** HOLE CARDS ***
Dealt to FresHHerB [Jh Js]
FresHHerB: calls 20
d1mitris: checks
```

**Estrutura PHH:**
```python
preflop_actions = [
    {'event': 'action', 'street': 'preflop', 'player': 'FresHHerB',
     'action': 'posts_sb', 'amount': 20},
    {'event': 'action', 'street': 'preflop', 'player': 'd1mitris',
     'action': 'posts_bb', 'amount': 40},
    {'event': 'cards', 'street': 'preflop', 'player': 'FresHHerB',
     'cards': ['Jh', 'Js']},
    {'event': 'action', 'street': 'preflop', 'player': 'FresHHerB',
     'action': 'call', 'amount': 20},  # Completou SB
    {'event': 'action', 'street': 'preflop', 'player': 'd1mitris',
     'action': 'check', 'amount': 0},
]
```

#### **Flop:**
```
*** FLOP *** [4c Tc Jd]
d1mitris: checks
FresHHerB: bets 40
d1mitris: calls 40
```

**Estrutura PHH:**
```python
flop_actions = [
    {'event': 'cards', 'street': 'flop', 'cards': ['4c', 'Tc', 'Jd']},
    {'event': 'action', 'street': 'flop', 'player': 'd1mitris',
     'action': 'check', 'amount': 0},
    {'event': 'action', 'street': 'flop', 'player': 'FresHHerB',
     'action': 'bet', 'amount': 40},
    {'event': 'action', 'street': 'flop', 'player': 'd1mitris',
     'action': 'call', 'amount': 40},
]
```

#### **Turn:**
```
*** TURN *** [4c Tc Jd] [5h]
d1mitris: checks
FresHHerB: bets 136
d1mitris: raises 136 to 272
FresHHerB: calls 136
```

**Estrutura PHH:**
```python
turn_actions = [
    {'event': 'cards', 'street': 'turn', 'cards': ['5h']},
    {'event': 'action', 'street': 'turn', 'player': 'd1mitris',
     'action': 'check', 'amount': 0},
    {'event': 'action', 'street': 'turn', 'player': 'FresHHerB',
     'action': 'bet', 'amount': 136},
    {'event': 'action', 'street': 'turn', 'player': 'd1mitris',
     'action': 'raise', 'amount': 272},  # Total, não incremental
    {'event': 'action', 'street': 'turn', 'player': 'FresHHerB',
     'action': 'call', 'amount': 136},
]
```

#### **River:**
```
*** RIVER *** [4c Tc Jd 5h] [Ts]
d1mitris: bets 558 and is all-in
FresHHerB: calls 238 and is all-in
Uncalled bet (320) returned to d1mitris
```

**Estrutura PHH:**
```python
river_actions = [
    {'event': 'cards', 'street': 'river', 'cards': ['Ts']},
    {'event': 'action', 'street': 'river', 'player': 'd1mitris',
     'action': 'bet_allin', 'amount': 558},
    {'event': 'action', 'street': 'river', 'player': 'FresHHerB',
     'action': 'call_allin', 'amount': 238},  # Stack restante
]
```

### 2.4. Showdown

```
*** SHOW DOWN ***
d1mitris: shows [4d 5d] (two pair, Tens and Fives)
FresHHerB: shows [Jh Js] (a full house, Jacks full of Tens)
FresHHerB collected 1180 from pot
```

**Estrutura PHH:**
```python
showdown = {
    'winners': ['FresHHerB'],
    'hands': [
        {
            'player': 'd1mitris',
            'cards': ['4d', '5d'],
            'rank': 'two pair'  # Opcional
        },
        {
            'player': 'FresHHerB',
            'cards': ['Jh', 'Js'],
            'rank': 'full house'  # Opcional
        }
    ]
}
```

---

## 3. Output Final (PHH)

### 3.1. Formato TOML Completo

```toml
[metadata]
hand_id = "255558737638"
timestamp = "2025/04/02 9:32:46 ET"
game = "NLHE"
room = "PokerStars"
tournament_id = "3875187542"
sb = 20.0
bb = 40.0
ante = 0.0
hero = "FresHHerB"
buyin_total = 5.0
level = "III"

[table]
name = "3875187542 1"
size = 2  # HU nesta mão (3rd player eliminado)

[[players]]
name = "FresHHerB"
seat = 2
stack = 590.0
is_btn = true

[[players]]
name = "d1mitris"
seat = 3
stack = 910.0
is_btn = false

# Preflop
[[actions]]
event = "action"
street = "preflop"
player = "FresHHerB"
action = "posts_sb"
amount = 20.0

[[actions]]
event = "action"
street = "preflop"
player = "d1mitris"
action = "posts_bb"
amount = 40.0

[[actions]]
event = "cards"
street = "preflop"
player = "FresHHerB"
cards = ["Jh", "Js"]

[[actions]]
event = "action"
street = "preflop"
player = "FresHHerB"
action = "call"
amount = 20.0

[[actions]]
event = "action"
street = "preflop"
player = "d1mitris"
action = "check"
amount = 0.0

# Flop
[[actions]]
event = "cards"
street = "flop"
cards = ["4c", "Tc", "Jd"]

[[actions]]
event = "action"
street = "flop"
player = "d1mitris"
action = "check"
amount = 0.0

[[actions]]
event = "action"
street = "flop"
player = "FresHHerB"
action = "bet"
amount = 40.0

[[actions]]
event = "action"
street = "flop"
player = "d1mitris"
action = "call"
amount = 40.0

# Turn
[[actions]]
event = "cards"
street = "turn"
cards = ["5h"]

[[actions]]
event = "action"
street = "turn"
player = "d1mitris"
action = "check"
amount = 0.0

[[actions]]
event = "action"
street = "turn"
player = "FresHHerB"
action = "bet"
amount = 136.0

[[actions]]
event = "action"
street = "turn"
player = "d1mitris"
action = "raise"
amount = 272.0

[[actions]]
event = "action"
street = "turn"
player = "FresHHerB"
action = "call"
amount = 136.0

# River
[[actions]]
event = "cards"
street = "river"
cards = ["Ts"]

[[actions]]
event = "action"
street = "river"
player = "d1mitris"
action = "bet_allin"
amount = 558.0

[[actions]]
event = "action"
street = "river"
player = "FresHHerB"
action = "call_allin"
amount = 238.0

# Showdown
[showdown]
winners = ["FresHHerB"]

[[showdown.hands]]
player = "d1mitris"
cards = ["4d", "5d"]

[[showdown.hands]]
player = "FresHHerB"
cards = ["Jh", "Js"]
```

---

## 4. Comparação: PokerStars vs iPoker → PHH

### 4.1. Mesma Mão em iPoker (Simulada)

**XML equivalente:**
```xml
<game gamecode="255558737638">
  <general>
    <startdate>2025-04-02 09:32:46</startdate>
    <round>1</round>
    <players>
      <player seat="2" name="FresHHerB" chips="590" dealer="1"
              win="1180" bet="590" muck="0"/>
      <player seat="3" name="d1mitris" chips="910" dealer="0"
              win="0" bet="590" muck="0"/>
    </players>
  </general>

  <!-- Preflop -->
  <round no="0">
    <action no="1" player="FresHHerB" type="1" sum="20"/>  <!-- SB -->
    <action no="2" player="d1mitris" type="2" sum="40"/>   <!-- BB -->
  </round>

  <round no="1">
    <cards type="Pocket" player="FresHHerB">HJ HJ</cards>
    <cards type="Pocket" player="d1mitris">D4 D5</cards>
    <action no="3" player="FresHHerB" type="3" sum="20"/>  <!-- call -->
    <action no="4" player="d1mitris" type="4" sum="0"/>    <!-- check -->
  </round>

  <!-- Flop -->
  <round no="2">
    <cards type="Flop">C4 CT CJ</cards>
    <action no="5" player="d1mitris" type="4" sum="0"/>    <!-- check -->
    <action no="6" player="FresHHerB" type="5" sum="40"/>  <!-- bet -->
    <action no="7" player="d1mitris" type="3" sum="40"/>   <!-- call -->
  </round>

  <!-- Turn -->
  <round no="3">
    <cards type="Turn">H5</cards>
    <action no="8" player="d1mitris" type="4" sum="0"/>    <!-- check -->
    <action no="9" player="FresHHerB" type="5" sum="136"/> <!-- bet -->
    <action no="10" player="d1mitris" type="23" sum="272"/> <!-- raise -->
    <action no="11" player="FresHHerB" type="3" sum="136"/> <!-- call -->
  </round>

  <!-- River -->
  <round no="4">
    <cards type="River">CT</cards>
    <action no="12" player="d1mitris" type="5" sum="558"/>  <!-- bet -->
    <action no="13" player="FresHHerB" type="7" sum="238"/> <!-- call allin -->
  </round>
</game>
```

### 4.2. PHH Resultante (Idêntico)

**Ponto Crucial:** Ambos os formatos (PokerStars e iPoker) devem gerar **exatamente o mesmo PHH**!

```toml
# Output é IDÊNTICO ao mostrado na seção 3.1
[metadata]
hand_id = "255558737638"
...
```

**Garantia de Uniformidade:**
- ✅ Mesma estrutura de dados
- ✅ Mesmas convenções (cartas, amounts, etc.)
- ✅ Mesmo vocabulário de ações
- ✅ Feature engineering idêntico na etapa seguinte

---

## 5. Diferenças de Implementação

### 5.1. Parsing de Cartas

**PokerStars:**
```python
# Input: "Jh Js" (rank + suit)
# Output direto: ['Jh', 'Js']
cards = hole_cards_str.split()
```

**iPoker:**
```python
# Input: "HJ HJ" (suit + rank)
# Precisa conversão:
def convert_ipoker_card(card):
    suit_map = {'S': 's', 'H': 'h', 'D': 'd', 'C': 'c'}
    suit = suit_map[card[0]]
    rank = card[1:].replace('10', 'T')
    return f"{rank}{suit}"

cards = [convert_ipoker_card(c) for c in "HJ HJ".split()]
# Output: ['Jh', 'Jh']
```

### 5.2. Detecção de All-In

**PokerStars:**
```python
# Explícito no texto
if "and is all-in" in action_text:
    action_type = "call_allin" if "calls" in text else "bet_allin"
```

**iPoker:**
```python
# Implícito - precisa calcular
def is_allin(player, amount, actions_before):
    stack_remaining = calculate_stack(player, actions_before)
    return amount >= stack_remaining

# type="7" também indica call all-in
if action_type == "7":
    action = "call_allin"
```

### 5.3. Extração de Showdown

**PokerStars:**
```python
# Seção dedicada *** SHOW DOWN ***
showdown_section = extract_section(hand_text, "*** SHOW DOWN ***", "*** SUMMARY ***")
for line in showdown_section:
    if "shows" in line:
        # "d1mitris: shows [4d 5d] (two pair, Tens and Fives)"
        player, cards, rank = parse_showdown_line(line)
```

**iPoker:**
```python
# Atributos do jogador
for player in players:
    if player.get("muck") == "0":  # Mostrou
        showdown_hands[player['name']] = pocket_cards[player['name']]
```

---

## 6. Código Unificado Proposto

### 6.1. Interface Comum

```python
from abc import ABC, abstractmethod

class HandHistoryParser(ABC):
    """
    Interface abstrata para parsers de diferentes formatos.
    """

    @abstractmethod
    def parse(self, input_data) -> dict:
        """
        Converte input específico para estrutura PHH.

        Returns:
            dict: Estrutura compatível com phh-std
        """
        pass

    def to_phh_file(self, input_data, output_path):
        """
        Converte e salva como arquivo .phh
        """
        phh_data = self.parse(input_data)

        with open(output_path, 'wb') as f:
            tomli_w.dump(phh_data, f)

        return output_path
```

### 6.2. Implementações Específicas

```python
class PokerStarsParser(HandHistoryParser):
    """
    Parser para formato PokerStars (texto plano).
    """

    def parse(self, hand_text: str) -> dict:
        metadata = self._parse_header(hand_text)
        players = self._parse_players(hand_text)
        actions = self._parse_actions(hand_text)
        showdown = self._parse_showdown(hand_text)

        return self._build_phh(metadata, players, actions, showdown)

    def _parse_header(self, text):
        # Implementação específica PokerStars
        ...

class IPokerParser(HandHistoryParser):
    """
    Parser para formato iPoker (XML).
    """

    def parse(self, xml_element: ET.Element) -> dict:
        metadata = self._parse_game_node(xml_element)
        players = self._parse_players(xml_element)
        actions = self._parse_rounds(xml_element)
        showdown = self._parse_showdown(xml_element)

        return self._build_phh(metadata, players, actions, showdown)

    def _parse_game_node(self, elem):
        # Implementação específica iPoker
        ...
```

### 6.3. Uso Unificado

```python
# Processar PokerStars
ps_parser = PokerStarsParser()
ps_parser.to_phh_file(pokerstars_hand_text, "output/255558737638.phh")

# Processar iPoker
ip_parser = IPokerParser()
ip_parser.to_phh_file(ipoker_game_node, "output/11514533315.phh")

# Feature engineering é IDÊNTICO para ambos!
from src.features import extract_features

phh_data = load_phh("output/255558737638.phh")
features = extract_features(phh_data)  # Funciona independente da origem
```

---

## 7. Validação

### 7.1. Checklist de Conformidade PHH

Após conversão, validar que PHH contém:

- [ ] `metadata.hand_id` (único)
- [ ] `metadata.sb`, `metadata.bb` (valores corretos)
- [ ] `metadata.hero` (nome do jogador principal)
- [ ] `table.size` (número de jogadores)
- [ ] `players` (lista completa com stacks)
- [ ] `actions` (cronologia correta)
- [ ] Cartas em formato padrão (`{rank}{suit}`)
- [ ] `showdown.winners` (se aplicável)
- [ ] Board completo se a mão foi além do preflop

### 7.2. Testes de Integridade

```python
def validate_phh(phh_data):
    """
    Valida estrutura PHH.
    """
    assert 'metadata' in phh_data
    assert 'hand_id' in phh_data['metadata']
    assert 'players' in phh_data
    assert len(phh_data['players']) >= 2  # Mínimo HU
    assert 'actions' in phh_data

    # Validar formato de cartas
    for action in phh_data['actions']:
        if action.get('event') == 'cards' and 'cards' in action:
            for card in action['cards']:
                assert len(card) in [2, 3]  # 'As', 'Td', '10h'
                assert card[-1] in ['s', 'h', 'd', 'c']  # Suit

    print("✅ PHH válido")
```

---

## 8. Próximos Passos

1. **Implementar parser PokerStars** seguindo estrutura acima
2. **Testar com 100 mãos** do arquivo real
3. **Validar % de sucesso** (target: >95%)
4. **Unificar com pipeline existente** (iPoker já funciona)
5. **Processar volume completo** (14k mãos → ~5.6k HU estimadas)

**Resultado Final:** Dataset combinado iPoker + PokerStars com **~5.7k mãos HU** prontas para análise!
