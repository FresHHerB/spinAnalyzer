"""
Unified Parser - Detecta e processa múltiplos formatos de hand history

Suporta:
- XML (iPoker)
- TXT (PokerStars)
- ZIP (archives)
"""

import re
import zipfile
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from enum import Enum
import tomli_w
from loguru import logger


class HandFormat(Enum):
    """Formatos de hand history suportados"""
    XML_IPOKER = "xml_ipoker"
    TXT_IPOKER = "txt_ipoker"
    TXT_POKERSTARS = "txt_pokerstars"
    PHH = "phh"
    UNKNOWN = "unknown"


class UnifiedParser:
    """
    Parser unificado que detecta formato automaticamente e converte para PHH
    """

    def __init__(self, output_dir: Path):
        """
        Args:
            output_dir: Diretório para salvar arquivos PHH convertidos
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.stats = {
            "total_files": 0,
            "total_hands": 0,
            "hu_hands": 0,
            "converted": 0,
            "errors": 0,
            "by_format": {}
        }

    def detect_format(self, file_path: Path) -> HandFormat:
        """
        Detecta formato do arquivo baseado em extensão e conteúdo

        Args:
            file_path: Caminho do arquivo

        Returns:
            HandFormat enum
        """
        # Por extensão
        ext = file_path.suffix.lower()

        if ext == ".xml":
            return HandFormat.XML_IPOKER

        if ext in [".txt", ".log"]:
            # Read more than one line — PokerStars files often start
            # with a "Hand #N:" pre-header before "PokerStars Hand #".
            with open(file_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
                head = f.read(2048)

            if "PokerStars Hand #" in head:
                return HandFormat.TXT_POKERSTARS
            if "GAME #" in head:
                return HandFormat.TXT_IPOKER

        if ext == ".phh":
            return HandFormat.PHH

        if ext == ".zip":
            # ZIP pode conter múltiplos formatos
            # Será processado separadamente
            pass

        return HandFormat.UNKNOWN

    def parse_file(self, file_path: Path, filters: Optional[Dict] = None) -> List[Path]:
        """
        Processa um arquivo e retorna lista de arquivos PHH gerados

        Args:
            file_path: Arquivo de input
            filters: Filtros (ex: {'heads_up_only': True})

        Returns:
            Lista de caminhos para arquivos PHH gerados
        """
        file_path = Path(file_path)

        if not file_path.exists():
            logger.error(f"Arquivo não encontrado: {file_path}")
            return []

        # Detectar formato
        format_type = self.detect_format(file_path)
        logger.info(f"Processando {file_path.name} | Formato: {format_type.value}")

        self.stats["total_files"] += 1
        self.stats["by_format"][format_type.value] = \
            self.stats["by_format"].get(format_type.value, 0) + 1

        # Processar baseado no formato
        if format_type == HandFormat.XML_IPOKER:
            return self._parse_xml_ipoker(file_path, filters)

        elif format_type == HandFormat.TXT_IPOKER:
            return self._parse_txt_ipoker(file_path, filters)

        elif format_type == HandFormat.TXT_POKERSTARS:
            return self._parse_txt_pokerstars(file_path, filters)

        elif format_type == HandFormat.PHH:
            # Já está em PHH, apenas copiar se passar filtros
            return self._copy_phh_if_valid(file_path, filters)

        elif file_path.suffix.lower() == ".zip":
            return self._parse_zip_archive(file_path, filters)

        else:
            logger.warning(f"Formato não suportado: {file_path}")
            return []

    def parse_directory(self, input_dir: Path, filters: Optional[Dict] = None) -> List[Path]:
        """
        Processa todos os arquivos de um diretório recursivamente

        Args:
            input_dir: Diretório de input
            filters: Filtros para aplicar

        Returns:
            Lista de todos os arquivos PHH gerados
        """
        input_dir = Path(input_dir)
        all_phh_files = []

        # Buscar todos os arquivos suportados
        supported_extensions = [".xml", ".txt", ".log", ".zip", ".phh"]

        for ext in supported_extensions:
            for file_path in input_dir.rglob(f"*{ext}"):
                if file_path.is_file():
                    phh_files = self.parse_file(file_path, filters)
                    all_phh_files.extend(phh_files)

        logger.info(f"\n{'='*60}")
        logger.info(f"RESUMO DO PROCESSAMENTO")
        logger.info(f"{'='*60}")
        logger.info(f"Total de arquivos processados: {self.stats['total_files']}")
        logger.info(f"Total de mãos encontradas: {self.stats['total_hands']}")
        logger.info(f"Mãos HU filtradas: {self.stats['hu_hands']}")
        logger.info(f"Mãos convertidas: {self.stats['converted']}")
        logger.info(f"Erros: {self.stats['errors']}")
        logger.info(f"\nPor formato:")
        for fmt, count in self.stats['by_format'].items():
            logger.info(f"  {fmt}: {count} arquivo(s)")
        logger.info(f"{'='*60}\n")

        return all_phh_files

    # ============================================
    # PARSERS ESPECÍFICOS POR FORMATO
    # ============================================

    def _parse_xml_ipoker(self, file_path: Path, filters: Optional[Dict]) -> List[Path]:
        """Parser for iPoker session XML files (one session = many <game>s)."""
        try:
            import xml.etree.ElementTree as ET

            tree = ET.parse(file_path)
            root = tree.getroot()

            # Hero name lives in the session-level <general><nickname>.
            session_general = root.find('./general')
            hero_name = ''
            if session_general is not None:
                nick = session_general.find('nickname')
                if nick is not None and nick.text:
                    hero_name = nick.text.strip()

            games = root.findall('.//game')
            self.stats['total_hands'] += len(games)

            phh_files = []
            for game in games:
                if filters and filters.get('heads_up_only', False):
                    players = game.findall('.//player')
                    if len(players) != 2:
                        continue

                self.stats['hu_hands'] += 1

                phh_data = self._xml_game_to_phh(game, hero_name=hero_name)
                if phh_data:
                    hand_id = phh_data['metadata']['hand_id']
                    phh_path = self.output_dir / f"{hand_id}.phh"
                    with open(phh_path, 'wb') as f:
                        tomli_w.dump(phh_data, f)
                    phh_files.append(phh_path)
                    self.stats['converted'] += 1

            return phh_files

        except Exception as e:
            logger.error(f"Erro ao processar XML {file_path}: {e}")
            self.stats['errors'] += 1
            return []

    def _parse_txt_pokerstars(self, file_path: Path, filters: Optional[Dict]) -> List[Path]:
        """
        Parser para TXT do PokerStars

        Usa o parser existente test_pokerstars_parser.py como base
        """
        try:
            # Ler arquivo
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                content = f.read()

            # Separar mãos
            hands = self._split_pokerstars_hands(content)
            self.stats['total_hands'] += len(hands)

            phh_files = []

            for hand_text in hands:
                # Verificar se é HU
                if filters and filters.get('heads_up_only', False):
                    if not self._is_heads_up_pokerstars(hand_text):
                        continue

                self.stats['hu_hands'] += 1

                # Converter para PHH
                phh_data = self._pokerstars_hand_to_phh(hand_text)

                if phh_data:
                    # Salvar PHH
                    hand_id = phh_data['metadata']['hand_id']
                    phh_path = self.output_dir / f"{hand_id}.phh"

                    with open(phh_path, 'wb') as f:
                        tomli_w.dump(phh_data, f)

                    phh_files.append(phh_path)
                    self.stats['converted'] += 1

            return phh_files

        except Exception as e:
            logger.error(f"Erro ao processar TXT {file_path}: {e}")
            self.stats['errors'] += 1
            return []

    def _parse_txt_ipoker(self, file_path: Path, filters: Optional[Dict]) -> List[Path]:
        """
        Parser para TXT do iPoker (formato GAME #)
        """
        try:
            # Ler arquivo
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                content = f.read()

            # Separar mãos
            hands = self._split_ipoker_hands(content)
            self.stats['total_hands'] += len(hands)

            phh_files = []

            for hand_text in hands:
                # Verificar se é HU
                if filters and filters.get('heads_up_only', False):
                    if not self._is_heads_up_ipoker(hand_text):
                        continue

                self.stats['hu_hands'] += 1

                # Converter para PHH
                phh_data = self._ipoker_hand_to_phh(hand_text)

                if phh_data:
                    # Salvar PHH
                    hand_id = phh_data['metadata']['hand_id']
                    phh_path = self.output_dir / f"{hand_id}.phh"

                    with open(phh_path, 'wb') as f:
                        tomli_w.dump(phh_data, f)

                    phh_files.append(phh_path)
                    self.stats['converted'] += 1

            return phh_files

        except Exception as e:
            logger.error(f"Erro ao processar iPoker TXT {file_path}: {e}")
            self.stats['errors'] += 1
            return []

    def _parse_zip_archive(self, zip_path: Path, filters: Optional[Dict]) -> List[Path]:
        """
        Extrai e processa arquivos de um ZIP

        Args:
            zip_path: Caminho para arquivo ZIP
            filters: Filtros para aplicar

        Returns:
            Lista de arquivos PHH gerados
        """
        try:
            import tempfile
            import shutil

            all_phh_files = []

            # Criar diretório temporário
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # Extrair ZIP
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_path)

                logger.info(f"ZIP extraído: {zip_path.name}")

                # Processar arquivos extraídos
                for file_path in temp_path.rglob('*'):
                    if file_path.is_file():
                        phh_files = self.parse_file(file_path, filters)
                        all_phh_files.extend(phh_files)

            return all_phh_files

        except Exception as e:
            logger.error(f"Erro ao processar ZIP {zip_path}: {e}")
            self.stats['errors'] += 1
            return []

    def _copy_phh_if_valid(self, phh_path: Path, filters: Optional[Dict]) -> List[Path]:
        """
        Copia arquivo PHH se passar nos filtros

        Args:
            phh_path: Caminho para arquivo PHH
            filters: Filtros para aplicar

        Returns:
            Lista com o caminho do arquivo (se válido) ou vazia
        """
        try:
            import tomli

            with open(phh_path, 'rb') as f:
                phh_data = tomli.load(f)

            # Aplicar filtros
            if filters and filters.get('heads_up_only', False):
                players = phh_data.get('players', [])
                if len(players) != 2:
                    return []

            self.stats['total_hands'] += 1
            self.stats['hu_hands'] += 1

            # Copiar para output_dir
            import shutil
            dest_path = self.output_dir / phh_path.name
            shutil.copy2(phh_path, dest_path)

            self.stats['converted'] += 1
            return [dest_path]

        except Exception as e:
            logger.error(f"Erro ao validar PHH {phh_path}: {e}")
            self.stats['errors'] += 1
            return []

    # ============================================
    # HELPERS - CONVERTERS
    # ============================================

    # iPoker XML action type → PHH verb. Verified against
    # dataset/original_hands/final/*.xml in this repo.
    _XML_ACTION_TYPE_MAP = {
        '0': 'fold',
        '1': 'posts_sb',
        '2': 'posts_bb',
        '3': 'call',
        '4': 'check',
        '5': 'bet',
        '7': 'all_in',
        '15': 'ante',
        '23': 'raise',
    }
    # iPoker round numbering → PHH street. Round 0 holds antes/blinds
    # (preflop), round 1 holds preflop hole + actions.
    _XML_ROUND_TO_STREET = {
        '0': 'preflop',
        '1': 'preflop',
        '2': 'flop',
        '3': 'turn',
        '4': 'river',
    }

    def _xml_game_to_phh(self, game_element, hero_name: str = '') -> Optional[Dict]:
        """Convert one <game> element from iPoker XML into a PHH dict.

        The game element structure (verified):
            <game gamecode="X">
              <general>
                <players>
                  <player seat="N" name="..." chips="..." dealer="0|1" win="..." muck="0|1"/>
                </players>
              </general>
              <round no="0"><action no="..." player="..." type="15" sum="5"/>...</round>  # antes
              <round no="1"><cards type="Pocket" player="X">RANK SUIT</cards>... <action .../></round>
              <round no="2"><cards type="Flop">...</cards><action .../></round>
              ...
            </game>
        """
        try:
            hand_id = game_element.get('gamecode', '')
            if not hand_id:
                return None

            def _parse_num(s: str) -> float:
                """iPoker uses ',' as thousands separator (e.g. '1,460')."""
                if not s:
                    return 0.0
                try:
                    return float(s.replace(',', ''))
                except ValueError:
                    return 0.0

            # Players (per-game <general><players><player ...>)
            players = []
            for player_elem in game_element.findall('./general/players/player'):
                players.append({
                    'name': player_elem.get('name', ''),
                    'seat': int(player_elem.get('seat', '0')),
                    'stack': _parse_num(player_elem.get('chips', '0')),
                    'is_btn': player_elem.get('dealer', '0') == '1',
                })
            if len(players) < 2:
                return None

            # Showdown winners (player has win > 0 AND muck == 0)
            winners: list[str] = []
            for player_elem in game_element.findall('./general/players/player'):
                if _parse_num(player_elem.get('win', '0')) > 0 and player_elem.get('muck', '0') == '0':
                    winners.append(player_elem.get('name', ''))

            # Walk rounds, build actions stream + capture sb/bb/ante.
            actions: list[dict] = []
            sb_amount = 0.0
            bb_amount = 0.0
            ante_amount = 0.0
            shown_hands: list[dict] = []

            for round_elem in game_element.findall('./round'):
                round_no = round_elem.get('no', '')
                street = self._XML_ROUND_TO_STREET.get(round_no)
                if street is None:
                    continue

                # Cards events first within a round.
                for cards_elem in round_elem.findall('./cards'):
                    card_type = (cards_elem.get('type') or '').lower()
                    raw_text = (cards_elem.text or '').strip()
                    if not raw_text or raw_text.upper() == 'X X':
                        # Hole cards present but unrevealed for this player.
                        if card_type == 'pocket':
                            actions.append({
                                'event': 'cards',
                                'street': 'preflop',
                                'cards': [],
                                'player': cards_elem.get('player', ''),
                            })
                        continue
                    parts = raw_text.split()
                    cards = [self._normalize_card(c) for c in parts if c.upper() != 'X']
                    if card_type == 'pocket':
                        player_name = cards_elem.get('player', '')
                        # Filter out the placeholder X-cards
                        cards = [c for c in cards if c and c != 'X']
                        actions.append({
                            'event': 'cards',
                            'street': 'preflop',
                            'cards': cards,
                            'player': player_name,
                        })
                        if cards and len(cards) == 2:
                            shown_hands.append({
                                'player': player_name,
                                'cards': cards,
                            })
                    elif card_type in ('flop', 'turn', 'river'):
                        actions.append({
                            'event': 'cards',
                            'street': card_type,
                            'cards': cards,
                        })

                # Then action events.
                for action_elem in round_elem.findall('./action'):
                    type_code = action_elem.get('type', '')
                    verb = self._XML_ACTION_TYPE_MAP.get(type_code)
                    if verb is None:
                        continue
                    amount = _parse_num(action_elem.get('sum', '0'))
                    actions.append({
                        'event': 'action',
                        'street': street,
                        'player': action_elem.get('player', ''),
                        'action': verb,
                        'amount': amount,
                    })
                    # Capture blind/ante amounts as we see them.
                    if verb == 'ante' and amount > 0 and ante_amount == 0:
                        ante_amount = amount
                    elif verb == 'posts_sb' and amount > 0 and sb_amount == 0:
                        sb_amount = amount
                    elif verb == 'posts_bb' and amount > 0 and bb_amount == 0:
                        bb_amount = amount

            phh_data = {
                'metadata': {
                    'hand_id': hand_id,
                    'game': 'NLHE',
                    'room': 'iPoker',
                    'sb': sb_amount,
                    'bb': bb_amount,
                    'ante': ante_amount,
                    'hero': hero_name,
                },
                'players': players,
                'actions': actions,
                'showdown': {
                    'winners': winners,
                    'hands': shown_hands,
                },
            }
            return phh_data

        except Exception as e:
            logger.debug(f"Erro ao converter XML game: {e}")
            return None

    def _pokerstars_hand_to_phh(self, hand_text: str) -> Optional[Dict]:
        """Convert one PokerStars hand history block into a PHH dict.

        Format observed (verified against
        dataset/original_hands/ps/handHistory-*.txt):

            PokerStars Hand #ID: ... Hold'em No Limit - Level I (sb/bb) - ...
            Table '...' N-max Seat #N is the button
            Seat N: NAME (X in chips)
            NAME: posts small blind X
            NAME: posts big blind X
            *** HOLE CARDS ***
            Dealt to NAME [c1 c2]
            NAME: folds | checks | calls X | bets X | raises X to Y [and is all-in]
            *** FLOP *** [c c c]
            *** TURN *** [c c c] [c]
            *** RIVER *** [c c c c] [c]
            *** SHOW DOWN ***
            NAME: shows [c c] (...)
            NAME collected X from pot
        """
        try:
            hand_id_match = re.search(r"PokerStars Hand #(\d+):", hand_text)
            if not hand_id_match:
                return None
            hand_id = hand_id_match.group(1)

            # Stake level: "Level I (10/20)"
            stake_match = re.search(r"\((\d+)/(\d+)\)", hand_text)
            sb = float(stake_match.group(1)) if stake_match else 0.0
            bb = float(stake_match.group(2)) if stake_match else 0.0

            # Button seat: "Seat #X is the button"
            button_match = re.search(r"Seat #(\d+) is the button", hand_text)
            button_seat = int(button_match.group(1)) if button_match else 0

            # Players: "Seat N: NAME (X in chips)"
            players: list[dict] = []
            for m in re.finditer(
                r"^Seat (\d+): (\S+) \((\d+(?:\.\d+)?) in chips\)",
                hand_text,
                re.MULTILINE,
            ):
                seat = int(m.group(1))
                players.append({
                    'name': m.group(2),
                    'seat': seat,
                    'stack': float(m.group(3)),
                    'is_btn': seat == button_seat,
                })
            if len(players) < 2:
                return None

            # Hero: "Dealt to NAME [c1 c2]"
            hero_match = re.search(r"Dealt to (\S+) \[(\S+) (\S+)\]", hand_text)
            hero_name = hero_match.group(1) if hero_match else ''
            hero_cards = (
                [hero_match.group(2), hero_match.group(3)] if hero_match else []
            )

            # Build action stream by parsing each line in order.
            actions: list[dict] = []
            ante_amount = 0.0
            current_street = 'preflop'
            hero_dealt = False

            for line in hand_text.split('\n'):
                line = line.rstrip()
                if not line:
                    continue

                # Street markers
                if line.startswith('*** HOLE CARDS ***'):
                    # Emit hero hole-cards event right after this marker
                    if hero_match and not hero_dealt:
                        actions.append({
                            'event': 'cards',
                            'street': 'preflop',
                            'cards': hero_cards,
                            'player': hero_name,
                        })
                        hero_dealt = True
                    continue
                m = re.match(r"\*\*\* FLOP \*\*\* \[(\S+) (\S+) (\S+)\]", line)
                if m:
                    current_street = 'flop'
                    actions.append({
                        'event': 'cards',
                        'street': 'flop',
                        'cards': [m.group(1), m.group(2), m.group(3)],
                    })
                    continue
                m = re.match(r"\*\*\* TURN \*\*\* \[\S+ \S+ \S+\] \[(\S+)\]", line)
                if m:
                    current_street = 'turn'
                    actions.append({
                        'event': 'cards',
                        'street': 'turn',
                        'cards': [m.group(1)],
                    })
                    continue
                m = re.match(r"\*\*\* RIVER \*\*\* \[\S+ \S+ \S+ \S+\] \[(\S+)\]", line)
                if m:
                    current_street = 'river'
                    actions.append({
                        'event': 'cards',
                        'street': 'river',
                        'cards': [m.group(1)],
                    })
                    continue
                if line.startswith('*** SHOW DOWN ***'):
                    current_street = 'river'  # showdown is post-river
                    continue
                if line.startswith('*** SUMMARY ***'):
                    break

                # Action verbs
                m = re.match(r"(\S+): posts the ante (\d+(?:\.\d+)?)", line)
                if m:
                    amt = float(m.group(2))
                    actions.append({
                        'event': 'action', 'street': 'preflop',
                        'player': m.group(1), 'action': 'ante', 'amount': amt,
                    })
                    if ante_amount == 0:
                        ante_amount = amt
                    continue
                m = re.match(r"(\S+): posts small blind (\d+(?:\.\d+)?)", line)
                if m:
                    actions.append({
                        'event': 'action', 'street': 'preflop',
                        'player': m.group(1), 'action': 'posts_sb',
                        'amount': float(m.group(2)),
                    })
                    continue
                m = re.match(r"(\S+): posts big blind (\d+(?:\.\d+)?)", line)
                if m:
                    actions.append({
                        'event': 'action', 'street': 'preflop',
                        'player': m.group(1), 'action': 'posts_bb',
                        'amount': float(m.group(2)),
                    })
                    continue
                m = re.match(r"(\S+): folds", line)
                if m:
                    actions.append({
                        'event': 'action', 'street': current_street,
                        'player': m.group(1), 'action': 'fold', 'amount': 0.0,
                    })
                    continue
                m = re.match(r"(\S+): checks", line)
                if m:
                    actions.append({
                        'event': 'action', 'street': current_street,
                        'player': m.group(1), 'action': 'check', 'amount': 0.0,
                    })
                    continue
                m = re.match(r"(\S+): calls (\d+(?:\.\d+)?)(?:.*and is all-in)?", line)
                if m:
                    actions.append({
                        'event': 'action', 'street': current_street,
                        'player': m.group(1),
                        'action': 'call_allin' if 'all-in' in line else 'call',
                        'amount': float(m.group(2)),
                    })
                    continue
                m = re.match(r"(\S+): bets (\d+(?:\.\d+)?)(?:.*and is all-in)?", line)
                if m:
                    actions.append({
                        'event': 'action', 'street': current_street,
                        'player': m.group(1),
                        'action': 'bet',  # pokerkit_adapter handles all-in fallback
                        'amount': float(m.group(2)),
                    })
                    continue
                m = re.match(r"(\S+): raises \d+(?:\.\d+)? to (\d+(?:\.\d+)?)(?:.*and is all-in)?", line)
                if m:
                    actions.append({
                        'event': 'action', 'street': current_street,
                        'player': m.group(1),
                        'action': 'raise',
                        'amount': float(m.group(2)),  # 'to' total
                    })
                    continue
                m = re.match(r"(\S+): shows \[(\S+) (\S+)\]", line)
                if m:
                    if m.group(1) != hero_name:  # hero already emitted earlier
                        actions.append({
                            'event': 'cards',
                            'street': 'preflop',  # holdings are preflop info
                            'cards': [m.group(2), m.group(3)],
                            'player': m.group(1),
                        })
                    continue

            # Showdown: collect winners ("X collected Y from pot") and shown
            winners: list[str] = []
            for m in re.finditer(r"(\S+) collected (\d+(?:\.\d+)?) from pot", hand_text):
                if m.group(1) not in winners:
                    winners.append(m.group(1))
            shown: list[dict] = []
            for m in re.finditer(r"(\S+): shows \[(\S+) (\S+)\]", hand_text):
                shown.append({
                    'player': m.group(1),
                    'cards': [m.group(2), m.group(3)],
                })

            phh_data = {
                'metadata': {
                    'hand_id': hand_id,
                    'game': 'NLHE',
                    'room': 'PokerStars',
                    'sb': sb,
                    'bb': bb,
                    'ante': ante_amount,
                    'hero': hero_name,
                },
                'players': players,
                'actions': actions,
                'showdown': {
                    'winners': winners,
                    'hands': shown,
                },
            }
            return phh_data

        except Exception as e:
            logger.debug(f"Erro ao converter PokerStars hand: {e}")
            return None

    def _split_pokerstars_hands(self, content: str) -> List[str]:
        """
        Separa arquivo PokerStars em mãos individuais

        Args:
            content: Conteúdo completo do arquivo

        Returns:
            Lista de strings, cada uma contendo uma mão
        """
        hands = []
        current_hand = []

        for line in content.split('\n'):
            if line.startswith('PokerStars Hand #'):
                if current_hand:
                    hands.append('\n'.join(current_hand))
                current_hand = [line]
            else:
                current_hand.append(line)

        # Adicionar última mão
        if current_hand:
            hands.append('\n'.join(current_hand))

        return hands

    def _is_heads_up_pokerstars(self, hand_text: str) -> bool:
        """
        Verifica se uma mão do PokerStars é Heads-Up

        Args:
            hand_text: Texto da mão

        Returns:
            True se é HU, False caso contrário
        """
        # Contar "Seat X: PlayerName (stack in chips)"
        seats_with_chips = re.findall(
            r'^Seat \d+: \S+ \(\d+ in chips\)',
            hand_text,
            re.MULTILINE
        )

        return len(seats_with_chips) == 2

    def _split_ipoker_hands(self, content: str) -> List[str]:
        """
        Separa arquivo iPoker em mãos individuais

        Args:
            content: Conteúdo completo do arquivo

        Returns:
            Lista de strings, cada uma contendo uma mão
        """
        hands = []
        current_hand = []

        for line in content.split('\n'):
            if line.startswith('GAME #'):
                if current_hand:
                    hands.append('\n'.join(current_hand))
                current_hand = [line]
            else:
                if current_hand:  # Só adicionar se já começou uma mão
                    current_hand.append(line)

        # Adicionar última mão
        if current_hand:
            hands.append('\n'.join(current_hand))

        return hands

    def _is_heads_up_ipoker(self, hand_text: str) -> bool:
        """
        Verifica se uma mão do iPoker é Heads-Up

        Args:
            hand_text: Texto da mão

        Returns:
            True se é HU (2 jogadores ativos), False caso contrário
        """
        # Contar "Seat X: PlayerName (€XXX in chips)" - jogadores ativos
        seats = re.findall(
            r'^Seat \d+: \S+',
            hand_text,
            re.MULTILINE
        )

        return len(seats) == 2

    def _ipoker_hand_to_phh(self, hand_text: str) -> Optional[Dict]:
        """
        Converte texto de mão do iPoker para formato PHH

        Args:
            hand_text: Texto da mão no formato iPoker

        Returns:
            Dict com dados PHH ou None se erro
        """
        try:
            # Extrair hand ID
            hand_id_match = re.search(r'GAME #(\d+)', hand_text)
            if not hand_id_match:
                return None
            hand_id = hand_id_match.group(1)

            # Extrair hero (Dealt to)
            hero_match = re.search(r'Dealt to (\S+)', hand_text)
            hero = hero_match.group(1) if hero_match else ''

            # Extrair jogadores
            players = []
            seat_pattern = r'Seat (\d+): (\S+) \(€?([\d,\.]+) in chips\)\s*(DEALER)?'
            for match in re.finditer(seat_pattern, hand_text):
                seat_num = int(match.group(1))
                name = match.group(2)
                stack_str = match.group(3).replace(',', '')
                stack = float(stack_str)
                is_btn = bool(match.group(4))

                players.append({
                    'name': name,
                    'seat': seat_num,
                    'stack': stack,
                    'is_btn': is_btn
                })

            # Extrair blinds e antes
            sb_match = re.search(r'Post SB €?([\d,\.]+)', hand_text)
            bb_match = re.search(r'Post BB €?([\d,\.]+)', hand_text)
            ante_match = re.search(r'Post Ante €?([\d,\.]+)', hand_text)

            sb = float(sb_match.group(1).replace(',', '')) if sb_match else 0.0
            bb = float(bb_match.group(1).replace(',', '')) if bb_match else 0.0
            ante = float(ante_match.group(1).replace(',', '')) if ante_match else 0.0

            # Extrair ações
            actions = []

            # Padrões de ação
            action_patterns = [
                (r'(\S+): Post Ante €?([\d,\.]+)', 'ante'),
                (r'(\S+): Post SB €?([\d,\.]+)', 'sb'),
                (r'(\S+): Post BB €?([\d,\.]+)', 'bb'),
                (r'(\S+): Fold', 'fold'),
                (r'(\S+): Check', 'check'),
                (r'(\S+): Call €?([\d,\.]+)', 'call'),
                (r'(\S+): Raise(?:\s+\(NF\))? €?([\d,\.]+)', 'raise'),
                (r'(\S+): Bet €?([\d,\.]+)', 'bet'),
                (r'(\S+): All-in(?:\(raise\))? €?([\d,\.]+)', 'allin'),
            ]

            for line in hand_text.split('\n'):
                for pattern, action_type in action_patterns:
                    match = re.search(pattern, line)
                    if match:
                        player = match.group(1)
                        amount = 0.0
                        if len(match.groups()) > 1:
                            amount = float(match.group(2).replace(',', ''))

                        actions.append({
                            'player': player,
                            'action': action_type,
                            'amount': amount
                        })
                        break

            # Extrair board cards
            flop_match = re.search(r'\*\*\* FLOP \*\*\* \[([^\]]+)\]', hand_text)
            turn_match = re.search(r'\*\*\* TURN \*\*\* \[([^\]]+)\]', hand_text)
            river_match = re.search(r'\*\*\* RIVER \*\*\* \[([^\]]+)\]', hand_text)

            board = []
            if flop_match:
                flop_cards = flop_match.group(1).split()
                board.extend([self._normalize_card(c) for c in flop_cards])
            if turn_match:
                turn_card = turn_match.group(1).strip()
                board.append(self._normalize_card(turn_card))
            if river_match:
                river_card = river_match.group(1).strip()
                board.append(self._normalize_card(river_card))

            # Extrair showdown
            winners = []
            shown_hands = []

            winner_pattern = r'(\S+): wins €?([\d,\.]+)'
            for match in re.finditer(winner_pattern, hand_text):
                winners.append(match.group(1))

            shows_pattern = r'(\S+): Shows \[([^\]]+)\]'
            for match in re.finditer(shows_pattern, hand_text):
                player = match.group(1)
                cards_str = match.group(2)
                cards = [self._normalize_card(c) for c in cards_str.split()]
                shown_hands.append({
                    'player': player,
                    'cards': cards
                })

            # Estrutura PHH completa
            phh_data = {
                'metadata': {
                    'hand_id': hand_id,
                    'game': 'NLHE',
                    'room': 'iPoker',
                    'sb': sb,
                    'bb': bb,
                    'ante': ante,
                    'hero': hero
                },
                'players': players,
                'board': board,
                'actions': actions,
                'showdown': {
                    'winners': winners,
                    'hands': shown_hands
                }
            }

            return phh_data

        except Exception as e:
            logger.debug(f"Erro ao converter iPoker hand: {e}")
            return None

    def _normalize_card(self, card: str) -> str:
        """
        Normaliza carta do formato iPoker (D7, H10, SK) para formato padrão (7d, Th, Ks)

        Args:
            card: Carta no formato iPoker (suit + rank)

        Returns:
            Carta normalizada (rank + suit lowercase)
        """
        if len(card) < 2:
            return card

        # iPoker: D7 = 7 de ouros, H10 = 10 de copas
        # Formato: [Suit][Rank]
        suit_map = {
            'S': 's',  # Spades
            'H': 'h',  # Hearts
            'D': 'd',  # Diamonds
            'C': 'c'   # Clubs
        }

        suit = card[0]
        rank = card[1:]

        # Mapear rank especial
        if rank == '10':
            rank = 'T'

        normalized_suit = suit_map.get(suit, suit.lower())
        return f"{rank}{normalized_suit}"


# ============================================
# SCRIPT DE TESTE
# ============================================

if __name__ == "__main__":
    import sys

    # Configurar logging
    logger.remove()
    logger.add(sys.stderr, level="INFO")

    # Diretórios
    INPUT_DIR = Path(r"D:\code\python\spinAnalyzer\dataset\original_hands\final")
    OUTPUT_DIR = Path(r"D:\code\python\spinAnalyzer\dataset\phh_hands")

    # Criar parser
    parser = UnifiedParser(output_dir=OUTPUT_DIR)

    # Processar diretório
    filters = {
        'heads_up_only': True  # Apenas mãos HU
    }

    phh_files = parser.parse_directory(INPUT_DIR, filters=filters)

    logger.success(f"\n✅ Processamento concluído!")
    logger.success(f"📁 Arquivos PHH gerados: {len(phh_files)}")
    logger.success(f"📂 Localização: {OUTPUT_DIR}")
