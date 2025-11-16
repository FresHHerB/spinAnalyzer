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
            # Verificar conteúdo para distinguir PokerStars de iPoker
            with open(file_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
                first_line = f.readline()

                if "PokerStars Hand #" in first_line:
                    return HandFormat.TXT_POKERSTARS
                elif "GAME #" in first_line:
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
        """
        Parser para XML do iPoker

        Delega para o parser existente (simplificado aqui)
        """
        try:
            import xml.etree.ElementTree as ET

            tree = ET.parse(file_path)
            root = tree.getroot()

            # Contar mãos
            games = root.findall('.//game')
            self.stats['total_hands'] += len(games)

            phh_files = []

            for game in games:
                # Verificar se é HU
                if filters and filters.get('heads_up_only', False):
                    players = game.findall('.//player')
                    if len(players) != 2:
                        continue

                self.stats['hu_hands'] += 1

                # Converter para PHH
                phh_data = self._xml_game_to_phh(game)

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

    def _xml_game_to_phh(self, game_element) -> Optional[Dict]:
        """
        Converte elemento <game> do XML iPoker para formato PHH

        (Simplificado - versão completa usaria o código de etl_process.ipynb)
        """
        try:
            # Extrair metadados
            hand_id = game_element.get('gamecode', '')

            # Extrair jogadores
            players = []
            for player_elem in game_element.findall('.//player'):
                players.append({
                    'name': player_elem.get('name', ''),
                    'seat': int(player_elem.get('seat', '0')),
                    'stack': float(player_elem.get('chips', '0')),
                    'is_btn': player_elem.get('dealer', '') == 'true'
                })

            # Estrutura PHH básica
            phh_data = {
                'metadata': {
                    'hand_id': hand_id,
                    'game': 'NLHE',
                    'room': 'iPoker',
                    'sb': 0.0,
                    'bb': 0.0,
                    'ante': 0.0,
                    'hero': ''
                },
                'players': players,
                'actions': [],
                'showdown': {'winners': [], 'hands': []}
            }

            # TODO: Implementação completa de parsing de ações
            # Por ora, retornar estrutura básica

            return phh_data

        except Exception as e:
            logger.debug(f"Erro ao converter XML game: {e}")
            return None

    def _pokerstars_hand_to_phh(self, hand_text: str) -> Optional[Dict]:
        """
        Converte texto de mão do PokerStars para formato PHH

        (Simplificado - versão completa usaria test_pokerstars_parser.py)
        """
        try:
            # Extrair hand ID
            hand_id_match = re.search(r"PokerStars Hand #(\d+):", hand_text)
            if not hand_id_match:
                return None

            hand_id = hand_id_match.group(1)

            # Estrutura PHH básica
            phh_data = {
                'metadata': {
                    'hand_id': hand_id,
                    'game': 'NLHE',
                    'room': 'PokerStars',
                    'sb': 0.0,
                    'bb': 0.0,
                    'ante': 0.0,
                    'hero': ''
                },
                'players': [],
                'actions': [],
                'showdown': {'winners': [], 'hands': []}
            }

            # TODO: Implementação completa de parsing
            # Por ora, retornar estrutura básica

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
