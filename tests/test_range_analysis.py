"""
Unit Tests for Range Analysis Module
"""

import pytest
import pandas as pd
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api.range_analysis import (
    analyze_range_distribution,
    categorize_hand_strength,
    get_range_category
)


class TestRangeAnalysis:
    """Test range analysis functions"""

    @pytest.fixture
    def sample_df(self):
        """Create sample dataframe for testing"""
        data = {
            'decision_id': ['d1', 'd2', 'd3', 'd4', 'd5'],
            'hand_id': ['h1', 'h1', 'h2', 'h3', 'h4'],
            'villain_name': ['Player1', 'Player1', 'Player1', 'Player2', 'Player1'],
            'street': ['flop', 'turn', 'flop', 'flop', 'river'],
            'villain_position': ['BTN', 'BTN', 'BB', 'BTN', 'IP'],
            'villain_action': ['bet', 'raise', 'call', 'check', 'bet'],
            'pot_bb': [10.0, 15.0, 8.0, 12.0, 20.0],
            'villain_hand_strength': ['TWO_PAIR', 'FLUSH', 'ONE_PAIR', 'HIGH_CARD', 'STRAIGHT'],
            'villain_draws': ['none', 'none', 'flush_draw', 'none', 'none'],
            'board_texture': [
                {'board_size': 3, 'rainbow': True},
                {'board_size': 4, 'two_tone': True},
                {'board_size': 3, 'monotone': True},
                {'board_size': 3, 'paired': False},
                {'board_size': 5, 'rainbow': True}
            ],
            'board_cards': ['Kd 9s 3c', '7h 8s Kd 2h', '2d 9d 7c', '3d 7s 5c', '9h Td Jd Qc Ah']
        }
        return pd.DataFrame(data)

    def test_analyze_range_distribution_basic(self, sample_df):
        """Test basic range distribution analysis"""
        filters = {'villain_name': 'Player1'}
        result = analyze_range_distribution(sample_df, filters)

        assert result['total_samples'] == 4, "Should find 4 samples for Player1"
        assert 'hand_strength_distribution' in result
        assert 'draws_distribution' in result
        assert 'examples' in result

    def test_analyze_range_distribution_with_street_filter(self, sample_df):
        """Test range distribution with street filter"""
        filters = {'villain_name': 'Player1', 'street': 'flop'}
        result = analyze_range_distribution(sample_df, filters)

        assert result['total_samples'] == 2, "Should find 2 flop samples"

    def test_analyze_range_distribution_with_action_filter(self, sample_df):
        """Test range distribution with action filter"""
        filters = {'villain_name': 'Player1', 'action': 'bet'}
        result = analyze_range_distribution(sample_df, filters)

        assert result['total_samples'] == 2, "Should find 2 bet actions"

    def test_analyze_range_distribution_with_pot_filters(self, sample_df):
        """Test range distribution with pot size filters"""
        filters = {
            'villain_name': 'Player1',
            'pot_bb_min': 10.0,
            'pot_bb_max': 16.0
        }
        result = analyze_range_distribution(sample_df, filters)

        assert result['total_samples'] == 2, "Should find 2 samples in pot range 10-16 BB"

    def test_analyze_range_distribution_no_results(self, sample_df):
        """Test range distribution with no matching results"""
        filters = {'villain_name': 'NonExistent'}
        result = analyze_range_distribution(sample_df, filters)

        assert result['total_samples'] == 0
        assert len(result['examples']) == 0

    def test_analyze_range_distribution_hand_strength_percentages(self, sample_df):
        """Test that hand strength percentages add up correctly"""
        filters = {'villain_name': 'Player1'}
        result = analyze_range_distribution(sample_df, filters)

        total_percentage = sum(
            dist['percentage']
            for dist in result['hand_strength_distribution'].values()
        )

        # Allow small floating point error
        assert abs(total_percentage - 100.0) < 0.1, "Percentages should sum to ~100%"

    def test_categorize_hand_strength_nuts(self):
        """Test categorization of nuts hands"""
        assert categorize_hand_strength('STRAIGHT_FLUSH') == 'Nuts/Very Strong'
        assert categorize_hand_strength('FOUR_OF_A_KIND') == 'Nuts/Very Strong'
        assert categorize_hand_strength('FULL_HOUSE') == 'Nuts/Very Strong'

    def test_categorize_hand_strength_value(self):
        """Test categorization of value hands"""
        assert categorize_hand_strength('FLUSH') == 'Strong Value'
        assert categorize_hand_strength('STRAIGHT') == 'Strong Value'
        assert categorize_hand_strength('THREE_OF_A_KIND') == 'Strong Value'

    def test_categorize_hand_strength_pair(self):
        """Test categorization of pairs"""
        assert categorize_hand_strength('TWO_PAIR') == 'Medium Value (Two Pair)'
        assert categorize_hand_strength('ONE_PAIR') == 'Pair'

    def test_categorize_hand_strength_bluff(self):
        """Test categorization of bluffs"""
        assert categorize_hand_strength('HIGH_CARD') == 'High Card / Bluff'

    def test_categorize_hand_strength_unknown(self):
        """Test categorization of unknown/None hands"""
        assert categorize_hand_strength('None') == 'Unknown'
        assert categorize_hand_strength('') == 'Unknown'

    def test_get_range_category_value_bet(self):
        """Test range category for value bets"""
        category = get_range_category('FLUSH', 'none', 'bet')
        assert category == 'Value Bet'

        category = get_range_category('TWO_PAIR', 'none', 'raise')
        assert category == 'Value Bet'

    def test_get_range_category_draw(self):
        """Test range category for draws"""
        category = get_range_category('HIGH_CARD', 'flush_draw', 'bet')
        assert category == 'Draw / Semi-Bluff'

    def test_get_range_category_semi_bluff(self):
        """Test range category for semi-bluffs"""
        category = get_range_category('ONE_PAIR', 'oesd', 'bet')
        assert category == 'Semi-Bluff (Pair + Draw)'

    def test_get_range_category_pure_bluff(self):
        """Test range category for pure bluffs"""
        category = get_range_category('HIGH_CARD', 'none', 'bet')
        assert category == 'Pure Bluff'

        category = get_range_category('HIGH_CARD', 'none', 'raise')
        assert category == 'Pure Bluff'

    def test_get_range_category_showdown_value(self):
        """Test range category for showdown value"""
        category = get_range_category('ONE_PAIR', 'none', 'check')
        assert category == 'Showdown Value'

        category = get_range_category('ONE_PAIR', 'none', 'call')
        assert category == 'Showdown Value'

    def test_examples_limit(self, sample_df):
        """Test that examples are limited to 10"""
        # Create a larger dataset
        large_data = pd.concat([sample_df] * 5, ignore_index=True)
        filters = {'villain_name': 'Player1'}
        result = analyze_range_distribution(large_data, filters)

        assert len(result['examples']) <= 10, "Examples should be limited to 10"

    def test_examples_contain_required_fields(self, sample_df):
        """Test that examples contain all required fields"""
        filters = {'villain_name': 'Player1'}
        result = analyze_range_distribution(sample_df, filters)

        if result['examples']:
            example = result['examples'][0]
            required_fields = ['hand_id', 'street', 'action', 'pot_bb',
                              'villain_hand', 'hand_strength', 'board', 'draws']
            for field in required_fields:
                assert field in example, f"Example should contain {field}"


class TestRangeAnalysisEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_dataframe(self):
        """Test with empty dataframe"""
        df = pd.DataFrame()
        filters = {'villain_name': 'Player1'}

        # Should not crash
        result = analyze_range_distribution(df, filters)
        assert result['total_samples'] == 0

    def test_missing_columns(self):
        """Test with missing required columns"""
        df = pd.DataFrame({
            'villain_name': ['Player1'],
            'street': ['flop']
        })
        filters = {'villain_name': 'Player1'}

        # Should handle gracefully
        result = analyze_range_distribution(df, filters)
        assert result['total_samples'] == 1

    def test_null_values_in_hand_strength(self):
        """Test handling of null values in hand strength"""
        df = pd.DataFrame({
            'villain_name': ['Player1', 'Player1'],
            'street': ['flop', 'flop'],
            'villain_action': ['bet', 'call'],
            'pot_bb': [10.0, 12.0],
            'villain_hand_strength': [None, 'TWO_PAIR'],
            'villain_draws': ['none', 'none']
        })
        filters = {'villain_name': 'Player1'}

        result = analyze_range_distribution(df, filters)
        assert result['total_samples'] == 2
        # Should only count non-null hand strengths
        assert len(result['hand_strength_distribution']) == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
