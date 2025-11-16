"""
Context Extractor - Extrai decision points de mãos PHH

Um "decision point" é um momento onde o vil

ão precisa tomar uma decisão.
Cada decision point contém o contexto completo do jogo naquele momento.
"""

import tomli
import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from loguru import logger
import json


@dataclass
class DecisionPoint:
    """
    Representa um ponto de decisão completo

    Contém todo o contexto necessário para vetorização e busca de similaridade
    """
    # Identificação
    decision_id: str  # Único: {hand_id}_{step_idx}
    hand_id: str
    villain_name: str
    step_idx: int

    # Contexto temporal
    street: str  # preflop, flop, turn, river
    action_number_in_street: int

    # Estado do jogo
    pot_bb: float
    eff_stack_bb: float
    spr: Optional[float]

    # Posição
    villain_position: str  # IP, OOP, BTN, BB, SB
    hero_position: str

    # Histórico de ações até agora
    preflop_sequence: List[str]  # ["BTN_raise_3bb", "BB_call"]
    current_street_sequence: List[str]  # Ações na street atual

    # Agressor
    preflop_aggressor: Optional[str]  # 'hero', 'villain', None
    current_aggressor: Optional[str]

    # Board
    board_cards: List[str]  # ["Kh", "9h", "4h"]
    board_texture: Dict  # {monotone, paired, connected, etc}

    # Draws disponíveis (se mão do vilão for conhecida)
    villain_hand: Optional[List[str]]  # ["Ah", "Qh"] ou None
    villain_hand_strength: Optional[str]  # "FLUSH_DRAW", "TOP_PAIR", etc
    villain_draws: Optional[Dict]  # {flush_draw: True, oesd: False, ...}

    # Ação tomada pelo vilão (TARGET)
    villain_action: str  # check, call, bet, raise, fold, all_in
    villain_bet_size_bb: Optional[float]
    villain_bet_size_pot_pct: Optional[float]

    # Outcome
    went_to_showdown: bool
    villain_won: Optional[bool]

    # Context completo em JSON (para debug e storage)
    context_json: str

    def to_dict(self) -> Dict:
        """Converte para dicionário"""
        return asdict(self)


class ContextExtractor:
    """
    Extrai decision points de arquivos PHH
    """

    def __init__(self):
        self.stats = {
            "hands_processed": 0,
            "decision_points": 0,
            "errors": 0,
            "by_street": {
                "preflop": 0,
                "flop": 0,
                "turn": 0,
                "river": 0
            }
        }

    def extract_from_phh_file(self, phh_path: Path, villain_name: Optional[str] = None) -> List[DecisionPoint]:
        """
        Extrai decision points de um arquivo PHH

        Args:
            phh_path: Caminho para arquivo .phh
            villain_name: Nome do vilão (se None, detecta automaticamente como não-hero)

        Returns:
            Lista de DecisionPoint objects
        """
        try:
            # Carregar PHH
            with open(phh_path, 'rb') as f:
                phh = tomli.load(f)

            self.stats["hands_processed"] += 1

            # Identificar hero e villain
            hero_name = phh.get('metadata', {}).get('hero', '')

            if villain_name is None:
                # Detectar villain como o outro jogador
                players = phh.get('players', [])
                for player in players:
                    if player['name'] != hero_name:
                        villain_name = player['name']
                        break

            if not villain_name:
                logger.warning(f"Não foi possível identificar vilão em {phh_path.name}")
                return []

            # Extrair decision points
            decision_points = self._extract_decision_points(phh, hero_name, villain_name)

            self.stats["decision_points"] += len(decision_points)

            return decision_points

        except Exception as e:
            logger.error(f"Erro ao processar {phh_path}: {e}")
            self.stats["errors"] += 1
            return []

    def extract_from_directory(self, phh_dir: Path, villain_name: Optional[str] = None) -> pd.DataFrame:
        """
        Extrai decision points de todos os arquivos .phh em um diretório

        Args:
            phh_dir: Diretório com arquivos .phh
            villain_name: Nome do vilão (opcional)

        Returns:
            DataFrame com todos os decision points
        """
        phh_dir = Path(phh_dir)
        all_decision_points = []

        # Processar todos os .phh
        phh_files = list(phh_dir.glob("*.phh"))

        logger.info(f"Processando {len(phh_files)} arquivos PHH...")

        for i, phh_path in enumerate(phh_files):
            if (i + 1) % 100 == 0:
                logger.info(f"  Processados: {i+1}/{len(phh_files)}")

            dps = self.extract_from_phh_file(phh_path, villain_name)
            all_decision_points.extend(dps)

        # Converter para DataFrame
        df = pd.DataFrame([dp.to_dict() for dp in all_decision_points])

        logger.info(f"\n{'='*60}")
        logger.info(f"EXTRAÇÃO COMPLETA")
        logger.info(f"{'='*60}")
        logger.info(f"Mãos processadas: {self.stats['hands_processed']}")
        logger.info(f"Decision points extraídos: {self.stats['decision_points']}")
        logger.info(f"Erros: {self.stats['errors']}")
        logger.info(f"\nPor street:")
        for street, count in self.stats['by_street'].items():
            logger.info(f"  {street}: {count}")
        logger.info(f"{'='*60}\n")

        return df

    def _extract_decision_points(self, phh: Dict, hero_name: str, villain_name: str) -> List[DecisionPoint]:
        """
        Extrai todos os decision points do vilão em uma mão

        Args:
            phh: Dicionário PHH
            hero_name: Nome do hero
            villain_name: Nome do vilão

        Returns:
            Lista de DecisionPoint objects
        """
        decision_points = []

        # Metadata
        hand_id = phh.get('metadata', {}).get('hand_id', 'unknown')
        sb = phh.get('metadata', {}).get('sb', 0)
        bb = phh.get('metadata', {}).get('bb', 0)

        # Players
        players = {p['name']: p for p in phh.get('players', [])}

        if villain_name not in players:
            return []

        # Stacks iniciais
        hero_stack = players[hero_name]['stack'] if hero_name in players else 0
        villain_stack = players[villain_name]['stack']
        eff_stack_bb = min(hero_stack, villain_stack) / bb if bb > 0 else 0

        # Position
        villain_is_btn = players[villain_name].get('is_btn', False)
        hero_is_btn = players[hero_name].get('is_btn', False) if hero_name in players else False

        # Actions
        actions = phh.get('actions', [])

        # Agrupar ações por street
        actions_by_street = self._group_actions_by_street(actions)

        # Board cards por street
        board_by_street = self._extract_board_by_street(phh)

        # Processar cada street
        for street in ['preflop', 'flop', 'turn', 'river']:
            street_actions = actions_by_street.get(street, [])

            # Pot size no início da street
            pot_bb = self._calculate_pot_at_street_start(
                actions_by_street, street, sb, bb
            ) / bb if bb > 0 else 0

            # Board atual
            board_cards = board_by_street.get(street, [])

            # Filtrar ações do vilão nesta street
            # Ignorar blinds/antes (sb, bb, ante) - apenas ações de decisão (call, raise, fold, bet, check)
            decision_actions = ['call', 'raise', 'fold', 'bet', 'check', 'all_in']
            villain_actions_in_street = [
                a for a in street_actions
                if a.get('player') == villain_name and a.get('action') in decision_actions
            ]

            # Para cada ação do vilão, criar um decision point
            for action_idx, villain_action in enumerate(villain_actions_in_street):
                dp = self._create_decision_point(
                    hand_id=hand_id,
                    villain_name=villain_name,
                    hero_name=hero_name,
                    street=street,
                    action_idx=action_idx,
                    villain_action=villain_action,
                    all_street_actions=street_actions,
                    board_cards=board_cards,
                    pot_bb=pot_bb,
                    eff_stack_bb=eff_stack_bb,
                    villain_is_btn=villain_is_btn,
                    hero_is_btn=hero_is_btn,
                    actions_by_street=actions_by_street,
                    phh=phh
                )

                if dp:
                    decision_points.append(dp)
                    self.stats['by_street'][street] += 1

        return decision_points

    def _create_decision_point(
        self,
        hand_id: str,
        villain_name: str,
        hero_name: str,
        street: str,
        action_idx: int,
        villain_action: Dict,
        all_street_actions: List[Dict],
        board_cards: List[str],
        pot_bb: float,
        eff_stack_bb: float,
        villain_is_btn: bool,
        hero_is_btn: bool,
        actions_by_street: Dict,
        phh: Dict
    ) -> Optional[DecisionPoint]:
        """
        Cria um DecisionPoint a partir do contexto

        (Função auxiliar para _extract_decision_points)
        """
        try:
            # Decision ID
            step_idx = villain_action.get('step_idx', action_idx)
            decision_id = f"{hand_id}_{step_idx}"

            # Ação do vilão
            action_type = villain_action.get('action', 'unknown')
            amount_bb = villain_action.get('amount', 0) / phh.get('metadata', {}).get('bb', 1)

            # Bet size % pot
            bet_size_pot_pct = (amount_bb / pot_bb * 100) if pot_bb > 0 and amount_bb > 0 else None

            # Position
            if street == 'preflop':
                villain_pos = 'BTN' if villain_is_btn else 'BB'
                hero_pos = 'BTN' if hero_is_btn else 'BB'
            else:
                villain_pos = 'IP' if villain_is_btn else 'OOP'
                hero_pos = 'IP' if hero_is_btn else 'OOP'

            # Action sequences
            preflop_seq = self._build_action_sequence(
                actions_by_street.get('preflop', []),
                hero_name,
                villain_name
            )

            current_seq = self._build_action_sequence(
                all_street_actions[:action_idx],  # Até esta ação
                hero_name,
                villain_name
            )

            # Agressor
            preflop_aggressor = self._identify_last_aggressor(
                actions_by_street.get('preflop', []),
                hero_name,
                villain_name
            )

            current_aggressor = self._identify_last_aggressor(
                all_street_actions[:action_idx],
                hero_name,
                villain_name
            )

            # Board texture
            board_texture = self._analyze_board_texture(board_cards)

            # SPR
            spr = eff_stack_bb / pot_bb if pot_bb > 0 else None

            # Mão do vilão (se conhecida)
            villain_hand, villain_strength, villain_draws = self._extract_villain_hand_info(
                phh, villain_name, board_cards
            )

            # Showdown
            went_to_showdown, villain_won = self._check_showdown(phh, villain_name)

            # Context JSON
            context_json = json.dumps({
                "hand_id": hand_id,
                "street": street,
                "board": board_cards,
                "pot_bb": pot_bb,
                "spr": spr,
                "villain_pos": villain_pos,
                "action": action_type,
                "amount_bb": amount_bb
            })

            # Criar DecisionPoint
            dp = DecisionPoint(
                decision_id=decision_id,
                hand_id=hand_id,
                villain_name=villain_name,
                step_idx=step_idx,
                street=street,
                action_number_in_street=action_idx,
                pot_bb=pot_bb,
                eff_stack_bb=eff_stack_bb,
                spr=spr,
                villain_position=villain_pos,
                hero_position=hero_pos,
                preflop_sequence=preflop_seq,
                current_street_sequence=current_seq,
                preflop_aggressor=preflop_aggressor,
                current_aggressor=current_aggressor,
                board_cards=board_cards,
                board_texture=board_texture,
                villain_hand=villain_hand,
                villain_hand_strength=villain_strength,
                villain_draws=villain_draws,
                villain_action=action_type,
                villain_bet_size_bb=amount_bb if amount_bb > 0 else None,
                villain_bet_size_pot_pct=bet_size_pot_pct,
                went_to_showdown=went_to_showdown,
                villain_won=villain_won,
                context_json=context_json
            )

            return dp

        except Exception as e:
            logger.debug(f"Erro ao criar decision point: {e}")
            return None

    # ============================================
    # HELPERS
    # ============================================

    def _group_actions_by_street(self, actions: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Agrupa ações por street

        Como o PHH atual não tem campo 'street', todas as ações são tratadas como preflop
        TODO: Implementar detecção de streets baseado em padrões de ação
        """
        by_street = {
            'preflop': [],
            'flop': [],
            'turn': [],
            'river': []
        }

        # Por ora, tratar todas as ações como preflop
        by_street['preflop'] = actions

        return by_street

    def _extract_board_by_street(self, phh: Dict) -> Dict[str, List[str]]:
        """
        Extrai board cards por street

        O board está em phh['board'] como lista plana [flop1, flop2, flop3, turn, river]
        """
        board_cards = phh.get('board', [])

        board = {
            'preflop': [],
            'flop': [],
            'turn': [],
            'river': []
        }

        # Distribuir cartas por street
        if len(board_cards) >= 3:
            board['flop'] = board_cards[:3]
            board['turn'] = board_cards[:3]
            board['river'] = board_cards[:3]

        if len(board_cards) >= 4:
            board['turn'] = board_cards[:4]
            board['river'] = board_cards[:4]

        if len(board_cards) >= 5:
            board['river'] = board_cards[:5]

        return board

    def _calculate_pot_at_street_start(
        self, actions_by_street: Dict, current_street: str, sb: float, bb: float
    ) -> float:
        """Calcula pot size no início de uma street"""
        pot = 0

        street_order = ['preflop', 'flop', 'turn', 'river']
        current_idx = street_order.index(current_street)

        # Somar TODAS as ações (incluindo blinds/antes) de streets anteriores e atual
        for street in street_order[:current_idx + 1]:
            for action in actions_by_street.get(street, []):
                pot += action.get('amount', 0)

        return pot

    def _build_action_sequence(
        self, actions: List[Dict], hero_name: str, villain_name: str
    ) -> List[str]:
        """
        Constrói sequência de ações em formato legível

        Ex: ["BTN_raise_3bb", "BB_call", "BB_check", "BTN_bet_8bb"]
        """
        sequence = []

        for action in actions:
            player = action.get('player', '')
            action_type = action.get('action', '')
            amount = action.get('amount', 0)

            # Mapear player para hero/villain
            if player == hero_name:
                player_label = 'HERO'
            elif player == villain_name:
                player_label = 'VILLAIN'
            else:
                player_label = player

            # Formato: HERO_bet_8 ou VILLAIN_call
            if action_type in ['bet', 'raise'] and amount > 0:
                sequence.append(f"{player_label}_{action_type}_{int(amount)}")
            else:
                sequence.append(f"{player_label}_{action_type}")

        return sequence

    def _identify_last_aggressor(
        self, actions: List[Dict], hero_name: str, villain_name: str
    ) -> Optional[str]:
        """
        Identifica o último agressor (quem deu bet/raise por último)

        Returns:
            'hero', 'villain', ou None
        """
        last_aggressor = None

        for action in actions:
            player = action.get('player', '')
            action_type = action.get('action', '')

            if action_type in ['bet', 'raise']:
                if player == hero_name:
                    last_aggressor = 'hero'
                elif player == villain_name:
                    last_aggressor = 'villain'

        return last_aggressor

    def _analyze_board_texture(self, board_cards: List[str]) -> Dict:
        """
        Analisa textura do board

        (Simplificado - versão completa em src/classification/classifiers.py)
        """
        if not board_cards:
            return {}

        # Extrair naipes e ranks
        suits = [card[1] for card in board_cards if len(card) == 2]
        ranks = [card[0] for card in board_cards if len(card) == 2]

        # Análise básica
        texture = {
            "monotone": len(set(suits)) == 1 and len(suits) >= 3,
            "two_tone": len(set(suits)) == 2 and len(suits) == 3,
            "rainbow": len(set(suits)) == 3 and len(suits) == 3,
            "paired": len(ranks) != len(set(ranks)),
            "board_size": len(board_cards)
        }

        return texture

    def _extract_villain_hand_info(
        self, phh: Dict, villain_name: str, board_cards: List[str]
    ) -> Tuple[Optional[List[str]], Optional[str], Optional[Dict]]:
        """
        Extrai informações da mão do vilão (se conhecida)

        Returns:
            (villain_hand, hand_strength, draws)
        """
        # TODO: Implementar extração de cartas do showdown
        # Por ora, retornar None
        return None, None, None

    def _check_showdown(self, phh: Dict, villain_name: str) -> Tuple[bool, Optional[bool]]:
        """
        Verifica se foi ao showdown e se vilão ganhou

        Returns:
            (went_to_showdown, villain_won)
        """
        showdown = phh.get('showdown', {})
        winners = showdown.get('winners', [])

        went_to_showdown = len(showdown.get('hands', [])) > 0
        villain_won = villain_name in winners if went_to_showdown else None

        return went_to_showdown, villain_won


# ============================================
# SCRIPT DE TESTE
# ============================================

if __name__ == "__main__":
    import sys

    # Configurar logging
    logger.remove()
    logger.add(sys.stderr, level="INFO")

    # Diretórios
    PHH_DIR = Path(r"D:\code\python\spinAnalyzer\dataset\phh_hands")
    OUTPUT_FILE = Path(r"D:\code\python\spinAnalyzer\dataset\decision_points\decision_points.parquet")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Criar extractor
    extractor = ContextExtractor()

    # Processar diretório
    df = extractor.extract_from_directory(PHH_DIR)

    # Salvar como Parquet
    if len(df) > 0:
        df.to_parquet(OUTPUT_FILE, index=False)
        logger.success(f"\n✅ Decision points salvos em: {OUTPUT_FILE}")
        logger.success(f"📊 Total de decision points: {len(df)}")

        # Mostrar amostra
        logger.info(f"\nAmostra dos dados:")
        logger.info(f"\n{df.head()}")
        logger.info(f"\nColunas: {list(df.columns)}")
    else:
        logger.warning("Nenhum decision point extraído!")
