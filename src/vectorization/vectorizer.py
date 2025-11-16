"""
Vectorizer - Transforma DecisionPoints em vetores de 180 dimensões

Estratégia:
- One-hot encoding para features categóricas
- Normalização para features numéricas
- Embeddings para sequências de ações
- Weights configuráveis por categoria
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import json
from loguru import logger
from sklearn.preprocessing import StandardScaler


@dataclass
class FeatureConfig:
    """Configuração de features e seus pesos"""

    # Pesos por categoria (usados para similarity scoring)
    weights: Dict[str, float] = None

    # Dimensões por categoria
    dimensions: Dict[str, int] = None

    # Índices de início/fim para cada categoria no vetor
    indices: Dict[str, Tuple[int, int]] = None

    def __post_init__(self):
        if self.weights is None:
            self.weights = {
                "street": 10.0,
                "position": 5.0,
                "board_texture": 8.0,
                "spr": 6.0,
                "action_sequence": 7.0,
                "aggressor": 5.0,
                "pot_size": 3.0,
                "stack_size": 3.0,
                "draws": 6.0,
                "board_cards": 4.0,
                "hand_strength": 7.0,
                "previous_hero_action": 4.0,
                "bet_sizing": 5.0,
                "action_count": 2.0
            }

        if self.dimensions is None:
            self.dimensions = {
                "street": 4,              # One-hot: preflop, flop, turn, river
                "position": 4,            # One-hot: IP, OOP, BTN, BB
                "board_texture": 10,      # Multi-hot: monotone, paired, etc
                "spr": 5,                 # One-hot buckets
                "action_sequence": 30,    # Embedding-like encoding
                "aggressor": 3,           # One-hot: hero, villain, none
                "pot_size": 1,            # Normalized float
                "stack_size": 1,          # Normalized float
                "draws": 4,               # Binary flags
                "board_cards": 12,        # 3 cards × 4 (rank+suit)
                "hand_strength": 9,       # One-hot: categories
                "previous_hero_action": 8, # One-hot: common actions
                "bet_sizing": 6,          # One-hot buckets
                "action_count": 2         # Normalized counts
            }

        # Calcular índices
        if self.indices is None:
            self.indices = {}
            current_idx = 0

            for category, dim in self.dimensions.items():
                self.indices[category] = (current_idx, current_idx + dim)
                current_idx += dim

    @property
    def total_dimensions(self) -> int:
        """Total de dimensões do vetor"""
        return sum(self.dimensions.values())


class Vectorizer:
    """
    Vetoriza decision points em vetores de alta dimensão
    """

    def __init__(self, config: Optional[FeatureConfig] = None):
        """
        Args:
            config: Configuração de features (usa default se None)
        """
        self.config = config or FeatureConfig()
        self.scaler = StandardScaler()
        self.is_fitted = False

        logger.info(f"Vectorizer inicializado")
        logger.info(f"Total de dimensões: {self.config.total_dimensions}")

    def fit(self, decision_points_df: pd.DataFrame):
        """
        Fit do scaler com dados de treinamento

        Args:
            decision_points_df: DataFrame com decision points
        """
        logger.info("Fitting scaler com dados de treinamento...")

        # Extrair features numéricas para fit
        numeric_features = []

        for _, row in decision_points_df.iterrows():
            pot_bb = row.get('pot_bb', 0)
            eff_stack_bb = row.get('eff_stack_bb', 0)

            numeric_features.append([pot_bb, eff_stack_bb])

        if numeric_features:
            self.scaler.fit(numeric_features)
            self.is_fitted = True
            logger.success("Scaler fitted com sucesso")

    def vectorize_decision_point(self, dp: Dict) -> np.ndarray:
        """
        Vetoriza um único decision point

        Args:
            dp: Dicionário representando um DecisionPoint

        Returns:
            Vetor numpy de dimensão [config.total_dimensions]
        """
        vector = np.zeros(self.config.total_dimensions, dtype=np.float32)

        # 1. Street (4 dim) - One-hot
        street_vec = self._encode_street(dp.get('street', 'preflop'))
        start, end = self.config.indices['street']
        vector[start:end] = street_vec

        # 2. Position (4 dim) - One-hot
        position_vec = self._encode_position(
            dp.get('villain_position', 'OOP'),
            dp.get('hero_position', 'IP')
        )
        start, end = self.config.indices['position']
        vector[start:end] = position_vec

        # 3. Board Texture (10 dim) - Multi-hot
        board_texture = dp.get('board_texture', {})
        texture_vec = self._encode_board_texture(board_texture)
        start, end = self.config.indices['board_texture']
        vector[start:end] = texture_vec

        # 4. SPR (5 dim) - One-hot buckets
        spr = dp.get('spr', None)
        spr_vec = self._encode_spr(spr)
        start, end = self.config.indices['spr']
        vector[start:end] = spr_vec

        # 5. Action Sequence (30 dim) - Embedding-like
        action_seq = dp.get('current_street_sequence', [])
        action_vec = self._encode_action_sequence(action_seq)
        start, end = self.config.indices['action_sequence']
        vector[start:end] = action_vec

        # 6. Aggressor (3 dim) - One-hot
        aggressor = dp.get('current_aggressor', None)
        aggressor_vec = self._encode_aggressor(aggressor)
        start, end = self.config.indices['aggressor']
        vector[start:end] = aggressor_vec

        # 7. Pot Size (1 dim) - Normalized
        pot_bb = dp.get('pot_bb', 0)
        pot_vec = self._encode_pot_size(pot_bb)
        start, end = self.config.indices['pot_size']
        vector[start:end] = pot_vec

        # 8. Stack Size (1 dim) - Normalized
        stack_bb = dp.get('eff_stack_bb', 0)
        stack_vec = self._encode_stack_size(stack_bb)
        start, end = self.config.indices['stack_size']
        vector[start:end] = stack_vec

        # 9. Draws (4 dim) - Binary flags
        draws = dp.get('villain_draws', {})
        draws_vec = self._encode_draws(draws)
        start, end = self.config.indices['draws']
        vector[start:end] = draws_vec

        # 10. Board Cards (12 dim) - Encoded
        board_cards = dp.get('board_cards', [])
        board_vec = self._encode_board_cards(board_cards)
        start, end = self.config.indices['board_cards']
        vector[start:end] = board_vec

        # 11. Hand Strength (9 dim) - One-hot
        hand_strength = dp.get('villain_hand_strength', None)
        strength_vec = self._encode_hand_strength(hand_strength)
        start, end = self.config.indices['hand_strength']
        vector[start:end] = strength_vec

        # 12. Previous Hero Action (8 dim) - One-hot
        hero_action = self._extract_previous_hero_action(
            dp.get('current_street_sequence', [])
        )
        hero_action_vec = self._encode_hero_action(hero_action)
        start, end = self.config.indices['previous_hero_action']
        vector[start:end] = hero_action_vec

        # 13. Bet Sizing (6 dim) - One-hot buckets
        bet_size_pct = dp.get('villain_bet_size_pot_pct', None)
        bet_size_vec = self._encode_bet_sizing(bet_size_pct)
        start, end = self.config.indices['bet_sizing']
        vector[start:end] = bet_size_vec

        # 14. Action Count (2 dim) - Normalized
        action_count_vec = self._encode_action_count(
            len(dp.get('current_street_sequence', [])),
            dp.get('action_number_in_street', 0)
        )
        start, end = self.config.indices['action_count']
        vector[start:end] = action_count_vec

        return vector

    def vectorize_batch(self, decision_points_df: pd.DataFrame) -> np.ndarray:
        """
        Vetoriza múltiplos decision points

        Args:
            decision_points_df: DataFrame com decision points

        Returns:
            Array numpy de shape [n_samples, total_dimensions]
        """
        vectors = []

        for idx, row in decision_points_df.iterrows():
            dp_dict = row.to_dict()

            # Parse JSON fields se necessário
            if isinstance(dp_dict.get('board_texture'), str):
                dp_dict['board_texture'] = json.loads(dp_dict['board_texture'])

            if isinstance(dp_dict.get('villain_draws'), str):
                dp_dict['villain_draws'] = json.loads(dp_dict['villain_draws'])

            vector = self.vectorize_decision_point(dp_dict)
            vectors.append(vector)

        return np.array(vectors, dtype=np.float32)

    # ============================================
    # ENCODING FUNCTIONS
    # ============================================

    def _encode_street(self, street: str) -> np.ndarray:
        """One-hot encoding de street"""
        streets = ['preflop', 'flop', 'turn', 'river']
        vec = np.zeros(4, dtype=np.float32)

        if street in streets:
            vec[streets.index(street)] = 1.0

        return vec

    def _encode_position(self, villain_pos: str, hero_pos: str) -> np.ndarray:
        """One-hot encoding de posição"""
        positions = ['IP', 'OOP', 'BTN', 'BB']
        vec = np.zeros(4, dtype=np.float32)

        # Codificar posição do vilão
        if villain_pos in positions:
            vec[positions.index(villain_pos)] = 1.0

        return vec

    def _encode_board_texture(self, texture: Dict) -> np.ndarray:
        """Multi-hot encoding de board texture"""
        vec = np.zeros(10, dtype=np.float32)

        # Flags booleanas
        flags = [
            'monotone',      # 0
            'two_tone',      # 1
            'rainbow',       # 2
            'paired',        # 3
            'trips',         # 4
            'connected',     # 5
            'disconnected',  # 6
            'high_broadway', # 7
            'low',           # 8
            'wet'            # 9
        ]

        for i, flag in enumerate(flags):
            if texture.get(flag, False):
                vec[i] = 1.0

        return vec

    def _encode_spr(self, spr: Optional[float]) -> np.ndarray:
        """One-hot encoding de SPR em buckets"""
        vec = np.zeros(5, dtype=np.float32)

        if spr is None:
            vec[0] = 1.0  # Unknown
        elif spr < 2:
            vec[1] = 1.0  # Micro
        elif spr < 5:
            vec[2] = 1.0  # Low
        elif spr < 10:
            vec[3] = 1.0  # Medium
        else:
            vec[4] = 1.0  # High

        return vec

    def _encode_action_sequence(self, sequence: List[str]) -> np.ndarray:
        """
        Encoding de sequência de ações

        Estratégia simplificada: hash das últimas N ações
        Versão avançada usaria LSTM embeddings
        """
        vec = np.zeros(30, dtype=np.float32)

        # Usar últimas 5 ações
        recent_actions = sequence[-5:] if len(sequence) > 5 else sequence

        # Hash simples: mapear ações para índices
        action_types = [
            'check', 'call', 'bet', 'raise', 'fold',
            'bet_small', 'bet_medium', 'bet_large',
            'raise_small', 'raise_medium', 'raise_large',
            'all_in'
        ]

        for i, action_str in enumerate(recent_actions):
            # Extrair tipo de ação do formato "HERO_bet_8"
            for action_type in action_types:
                if action_type in action_str.lower():
                    # Ativar dimensão correspondente
                    idx = (i * 6 + action_types.index(action_type)) % 30
                    vec[idx] = 1.0
                    break

        return vec

    def _encode_aggressor(self, aggressor: Optional[str]) -> np.ndarray:
        """One-hot encoding de aggressor"""
        vec = np.zeros(3, dtype=np.float32)

        aggressors = ['hero', 'villain', None]

        if aggressor in aggressors:
            vec[aggressors.index(aggressor)] = 1.0
        else:
            vec[2] = 1.0  # None

        return vec

    def _encode_pot_size(self, pot_bb: float) -> np.ndarray:
        """Normalização de pot size"""
        # Log scale normalizado
        normalized = np.log1p(pot_bb) / 10.0
        return np.array([normalized], dtype=np.float32)

    def _encode_stack_size(self, stack_bb: float) -> np.ndarray:
        """Normalização de stack size"""
        # Dividir por 100 para normalizar
        normalized = stack_bb / 100.0
        return np.array([normalized], dtype=np.float32)

    def _encode_draws(self, draws: Optional[Dict]) -> np.ndarray:
        """Binary flags para draws"""
        vec = np.zeros(4, dtype=np.float32)

        if draws:
            vec[0] = 1.0 if draws.get('flush_draw', False) else 0.0
            vec[1] = 1.0 if draws.get('oesd', False) else 0.0
            vec[2] = 1.0 if draws.get('gutshot', False) else 0.0
            vec[3] = 1.0 if draws.get('combo_draw', False) else 0.0

        return vec

    def _encode_board_cards(self, board_cards: List[str]) -> np.ndarray:
        """
        Encoding de board cards

        Estratégia: 3 cartas × 4 dim (rank value + suit one-hot)
        """
        vec = np.zeros(12, dtype=np.float32)

        rank_values = {
            '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7,
            '8': 8, '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14
        }

        suits = ['c', 'd', 'h', 's']

        # Processar primeiras 3 cartas (flop)
        for i, card in enumerate(board_cards[:3]):
            if len(card) == 2:
                rank, suit = card[0], card[1].lower()

                # Rank value normalizado [0, 1]
                rank_val = rank_values.get(rank, 0) / 14.0
                vec[i * 4] = rank_val

                # Suit one-hot (3 dimensões restantes)
                if suit in suits:
                    suit_idx = suits.index(suit)
                    if suit_idx < 3:  # Usar apenas 3 das 4 dimensões
                        vec[i * 4 + 1 + suit_idx] = 1.0

        return vec

    def _encode_hand_strength(self, strength: Optional[str]) -> np.ndarray:
        """One-hot encoding de hand strength"""
        vec = np.zeros(9, dtype=np.float32)

        strengths = [
            'HIGH_CARD', 'ONE_PAIR', 'TWO_PAIR', 'THREE_OF_A_KIND',
            'STRAIGHT', 'FLUSH', 'FULL_HOUSE', 'FOUR_OF_A_KIND',
            'STRAIGHT_FLUSH'
        ]

        if strength in strengths:
            vec[strengths.index(strength)] = 1.0

        return vec

    def _extract_previous_hero_action(self, sequence: List[str]) -> Optional[str]:
        """Extrai última ação do hero da sequência"""
        for action in reversed(sequence):
            if 'HERO_' in action:
                # Extrair tipo de ação
                action_type = action.split('_')[1]
                return action_type

        return None

    def _encode_hero_action(self, action: Optional[str]) -> np.ndarray:
        """One-hot encoding de hero action"""
        vec = np.zeros(8, dtype=np.float32)

        actions = [
            'fold', 'check', 'call', 'bet', 'raise',
            'all_in', 'limp', 'iso'
        ]

        if action in actions:
            vec[actions.index(action)] = 1.0

        return vec

    def _encode_bet_sizing(self, bet_size_pct: Optional[float]) -> np.ndarray:
        """One-hot encoding de bet sizing"""
        vec = np.zeros(6, dtype=np.float32)

        if bet_size_pct is None:
            vec[0] = 1.0  # No bet
        elif bet_size_pct <= 33:
            vec[1] = 1.0  # Small (≤1/3 pot)
        elif bet_size_pct <= 50:
            vec[2] = 1.0  # Medium (~1/2 pot)
        elif bet_size_pct <= 75:
            vec[3] = 1.0  # Large (~2/3 pot)
        elif bet_size_pct <= 100:
            vec[4] = 1.0  # Pot
        else:
            vec[5] = 1.0  # Overbet

        return vec

    def _encode_action_count(self, current_count: int, total_count: int) -> np.ndarray:
        """Normalização de action counts"""
        current_normalized = current_count / 10.0
        total_normalized = total_count / 20.0

        return np.array([current_normalized, total_normalized], dtype=np.float32)

    def calculate_weighted_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Calcula similaridade ponderada entre dois vetores

        Args:
            vec1, vec2: Vetores de decisão

        Returns:
            Score de similaridade [0, 1]
        """
        total_score = 0.0
        total_weight = 0.0

        for category, weight in self.config.weights.items():
            start, end = self.config.indices[category]

            # Extrair sub-vetores
            sub_vec1 = vec1[start:end]
            sub_vec2 = vec2[start:end]

            # Cosine similarity
            norm1 = np.linalg.norm(sub_vec1)
            norm2 = np.linalg.norm(sub_vec2)

            if norm1 > 0 and norm2 > 0:
                cosine_sim = np.dot(sub_vec1, sub_vec2) / (norm1 * norm2)
                total_score += cosine_sim * weight
                total_weight += weight

        return total_score / total_weight if total_weight > 0 else 0.0


# ============================================
# SCRIPT DE TESTE
# ============================================

if __name__ == "__main__":
    import sys

    # Configurar logging
    logger.remove()
    logger.add(sys.stderr, level="INFO")

    # Carregar decision points
    DP_FILE = Path(r"D:\code\python\spinAnalyzer\dataset\decision_points\decision_points.parquet")
    OUTPUT_FILE = Path(r"D:\code\python\spinAnalyzer\dataset\decision_points\decision_points_vectorized.parquet")

    if not DP_FILE.exists():
        logger.error(f"Arquivo não encontrado: {DP_FILE}")
        logger.info("Execute context_extractor.py primeiro!")
        sys.exit(1)

    logger.info(f"Carregando decision points de {DP_FILE}...")
    df = pd.read_parquet(DP_FILE)

    logger.info(f"Decision points carregados: {len(df)}")

    # Criar vectorizer
    vectorizer = Vectorizer()

    # Fit (se necessário)
    vectorizer.fit(df)

    # Vetorizar
    logger.info("Vetorizando decision points...")
    vectors = vectorizer.vectorize_batch(df)

    logger.success(f"✅ Vetores criados: shape = {vectors.shape}")

    # Adicionar vetores ao DataFrame
    df['context_vector'] = list(vectors)

    # Salvar
    df.to_parquet(OUTPUT_FILE, index=False)

    logger.success(f"✅ Decision points vetorizados salvos em: {OUTPUT_FILE}")

    # Teste de similaridade
    if len(vectors) >= 2:
        logger.info("\nTeste de similaridade:")
        sim = vectorizer.calculate_weighted_similarity(vectors[0], vectors[1])
        logger.info(f"Similaridade entre DP[0] e DP[1]: {sim:.4f}")

        sim_self = vectorizer.calculate_weighted_similarity(vectors[0], vectors[0])
        logger.info(f"Similaridade entre DP[0] e DP[0] (deve ser ~1.0): {sim_self:.4f}")
