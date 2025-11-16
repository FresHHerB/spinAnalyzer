"""
Range Analysis Module - Análise avançada de tendências e holdings
"""
from typing import Dict, List, Optional
import pandas as pd


def analyze_range_distribution(
    df: pd.DataFrame,
    filters: Dict
) -> Dict:
    """
    Analisa a distribuição de mãos/ranges baseado em filtros

    Returns:
        {
            'total_samples': int,
            'hand_strength_distribution': {...},
            'draws_distribution': {...},
            'board_texture_distribution': {...},
            'examples': [...]
        }
    """
    # Handle empty dataframe
    if df.empty or len(df) == 0:
        return {
            'total_samples': 0,
            'hand_strength_distribution': {},
            'draws_distribution': {},
            'board_texture_distribution': {},
            'action_distribution': {},
            'examples': []
        }

    # Aplicar filtros
    filtered = df.copy()

    if filters.get('villain_name') and 'villain_name' in filtered.columns:
        filtered = filtered[filtered['villain_name'] == filters['villain_name']]

    if filters.get('street'):
        filtered = filtered[filtered['street'] == filters['street']]

    if filters.get('position'):
        filtered = filtered[filtered['villain_position'] == filters['position']]

    if filters.get('action'):
        # Filtrar por tipo de ação (bet, raise, call, check, fold)
        action_lower = filters['action'].lower()
        filtered = filtered[filtered['villain_action'].str.lower().str.contains(action_lower, na=False)]

    if filters.get('pot_bb_min') is not None:
        filtered = filtered[filtered['pot_bb'] >= filters['pot_bb_min']]

    if filters.get('pot_bb_max') is not None:
        filtered = filtered[filtered['pot_bb'] <= filters['pot_bb_max']]

    total_samples = len(filtered)

    if total_samples == 0:
        return {
            'total_samples': 0,
            'hand_strength_distribution': {},
            'draws_distribution': {},
            'board_texture_distribution': {},
            'action_distribution': {},
            'examples': []
        }

    # Distribuição de força de mão
    hand_strength_dist = {}
    if 'villain_hand_strength' in filtered.columns:
        strength_counts = filtered['villain_hand_strength'].value_counts().to_dict()
        # Converter para percentuais
        hand_strength_dist = {
            str(k): {
                'count': int(v),
                'percentage': round((v / total_samples) * 100, 1)
            }
            for k, v in strength_counts.items()
            if pd.notna(k)
        }

    # Distribuição de draws
    draws_dist = {}
    if 'villain_draws' in filtered.columns:
        # Parse draws (pode estar como lista ou string)
        all_draws = []
        for draws in filtered['villain_draws'].dropna():
            if isinstance(draws, str):
                if draws and draws != 'None' and draws != '[]':
                    all_draws.extend([d.strip() for d in draws.strip('[]').replace("'", "").split(',')])
            elif isinstance(draws, list):
                all_draws.extend(draws)

        draw_counts = pd.Series(all_draws).value_counts().to_dict()
        draws_dist = {
            str(k): {
                'count': int(v),
                'percentage': round((v / total_samples) * 100, 1)
            }
            for k, v in draw_counts.items()
            if k and k.strip()
        }

    # Distribuição de texturas de board
    board_texture_dist = {}
    if 'board_texture' in filtered.columns:
        texture_features = {}
        for texture in filtered['board_texture'].dropna():
            if isinstance(texture, str):
                # Parse string representation of dict
                import ast
                try:
                    texture_dict = ast.literal_eval(texture)
                except:
                    continue
            else:
                texture_dict = texture

            if isinstance(texture_dict, dict):
                for key, value in texture_dict.items():
                    if value and value != 'None':
                        feature_key = f"{key}_{value}"
                        texture_features[feature_key] = texture_features.get(feature_key, 0) + 1

        board_texture_dist = {
            str(k): {
                'count': int(v),
                'percentage': round((v / total_samples) * 100, 1)
            }
            for k, v in texture_features.items()
        }

    # Distribuição de ações (para contexto)
    action_dist = {}
    if 'villain_action' in filtered.columns:
        action_counts = filtered['villain_action'].value_counts().to_dict()
        action_dist = {
            str(k): {
                'count': int(v),
                'percentage': round((v / total_samples) * 100, 1)
            }
            for k, v in action_counts.items()
        }

    # Pegar exemplos reais (máximo 10)
    examples = []
    sample_size = min(10, total_samples)
    sample_df = filtered.sample(n=sample_size) if total_samples > sample_size else filtered

    for _, row in sample_df.iterrows():
        example = {
            'hand_id': str(row.get('hand_id', '')),
            'street': str(row.get('street', '')),
            'action': str(row.get('villain_action', '')),
            'pot_bb': float(row.get('pot_bb', 0)),
            'villain_hand': str(row.get('villain_hand', 'Unknown')),
            'hand_strength': str(row.get('villain_hand_strength', 'Unknown')),
            'board': str(row.get('board_cards', '')),
            'draws': str(row.get('villain_draws', '')),
        }
        examples.append(example)

    return {
        'total_samples': int(total_samples),
        'hand_strength_distribution': hand_strength_dist,
        'draws_distribution': draws_dist,
        'board_texture_distribution': board_texture_dist,
        'action_distribution': action_dist,
        'examples': examples
    }


def categorize_hand_strength(strength: str) -> str:
    """
    Categoriza força de mão em grupos para análise
    """
    if not strength or strength == 'None':
        return 'Unknown'

    strength_upper = strength.upper()

    # Mãos fortes
    if any(x in strength_upper for x in ['STRAIGHT_FLUSH', 'FOUR_OF_A_KIND', 'FULL_HOUSE']):
        return 'Nuts/Very Strong'

    # Mãos value forte
    if any(x in strength_upper for x in ['FLUSH', 'STRAIGHT', 'THREE_OF_A_KIND']):
        return 'Strong Value'

    # Two pair
    if 'TWO_PAIR' in strength_upper:
        return 'Medium Value (Two Pair)'

    # One pair
    if 'ONE_PAIR' in strength_upper or 'PAIR' in strength_upper:
        # Tentar identificar se é top, middle ou bottom pair (requer mais contexto)
        return 'Pair'

    # High card / Air
    if 'HIGH_CARD' in strength_upper:
        return 'High Card / Bluff'

    return strength


def get_range_category(strength: str, draws: str, action: str) -> str:
    """
    Classifica em categoria de range (Value/Draw/Bluff)
    """
    strength_cat = categorize_hand_strength(strength)
    has_draw = draws and draws != 'None' and draws != '[]' and draws != 'none' and draws.strip()

    # Value hands
    if any(x in strength_cat for x in ['Nuts', 'Strong', 'Medium']):
        return 'Value Bet'

    # Draws
    if has_draw:
        if 'Pair' in strength_cat:
            return 'Semi-Bluff (Pair + Draw)'
        return 'Draw / Semi-Bluff'

    # Bluffs
    if 'High Card' in strength_cat or 'Unknown' in strength_cat:
        if 'bet' in action.lower() or 'raise' in action.lower():
            return 'Pure Bluff'
        return 'Showdown Value'

    # Pair sem draw
    if 'Pair' in strength_cat:
        if 'check' in action.lower() or 'call' in action.lower():
            return 'Showdown Value'
        return 'Thin Value / Bluff'

    return 'Unknown'
