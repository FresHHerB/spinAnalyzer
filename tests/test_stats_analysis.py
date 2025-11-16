"""
Análise Estatística dos Dados - SpinAnalyzer v2.0

Testes e análises estatísticas adicionais:
1. Distribuição de ações por street
2. Análise de pot sizes
3. SPR distribution
4. Board texture distribution
5. Position analysis
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from loguru import logger

DP_FILE = Path("dataset/decision_points/decision_points.parquet")


def analyze_action_distribution():
    """Analisa distribuição de ações por street"""
    logger.info("\n" + "="*80)
    logger.info("ANÁLISE 1: DISTRIBUIÇÃO DE AÇÕES")
    logger.info("="*80)

    df = pd.read_parquet(DP_FILE)

    for street in ['preflop', 'flop', 'turn', 'river']:
        street_df = df[df['street'] == street]

        if len(street_df) == 0:
            continue

        logger.info(f"\n{street.upper()} ({len(street_df)} decision points)")
        logger.info(f"{'-'*40}")

        # Ações do vilão
        action_counts = street_df['villain_action'].value_counts()

        for action, count in action_counts.head(10).items():
            pct = (count / len(street_df)) * 100
            bar = "█" * int(pct / 3)
            logger.info(f"  {action:>15}: {count:>3} ({pct:>5.1f}%) {bar}")


def analyze_pot_sizes():
    """Analisa distribuição de pot sizes"""
    logger.info("\n" + "="*80)
    logger.info("ANÁLISE 2: POT SIZES")
    logger.info("="*80)

    df = pd.read_parquet(DP_FILE)

    pot_sizes = df['pot_bb'].dropna()

    logger.info(f"\nTotal de decisões com pot size: {len(pot_sizes)}")
    logger.info(f"\nEstatísticas (em BB):")
    logger.info(f"  Min:     {pot_sizes.min():.2f}")
    logger.info(f"  Max:     {pot_sizes.max():.2f}")
    logger.info(f"  Median:  {pot_sizes.median():.2f}")
    logger.info(f"  Mean:    {pot_sizes.mean():.2f}")
    logger.info(f"  Std:     {pot_sizes.std():.2f}")

    # Buckets
    logger.info(f"\nDistribuição por tamanho:")
    bins = [0, 5, 10, 20, 50, 100, 1000]
    labels = ['0-5 BB', '5-10 BB', '10-20 BB', '20-50 BB', '50-100 BB', '100+ BB']

    pot_categories = pd.cut(pot_sizes, bins=bins, labels=labels, include_lowest=True)
    for cat, count in pot_categories.value_counts().sort_index().items():
        pct = (count / len(pot_sizes)) * 100
        bar = "█" * int(pct / 2)
        logger.info(f"  {cat:>12}: {count:>3} ({pct:>5.1f}%) {bar}")


def analyze_spr():
    """Analisa distribuição de SPR"""
    logger.info("\n" + "="*80)
    logger.info("ANÁLISE 3: SPR (Stack-to-Pot Ratio)")
    logger.info("="*80)

    df = pd.read_parquet(DP_FILE)

    spr_values = df['spr'].dropna()

    logger.info(f"\nDecisões com SPR conhecido: {len(spr_values)}")
    logger.info(f"\nEstatísticas:")
    logger.info(f"  Min:     {spr_values.min():.2f}")
    logger.info(f"  Max:     {spr_values.max():.2f}")
    logger.info(f"  Median:  {spr_values.median():.2f}")
    logger.info(f"  Mean:    {spr_values.mean():.2f}")

    # Categorias de SPR (comum em poker)
    logger.info(f"\nCategorias:")

    low_spr = len(spr_values[spr_values <= 5])
    med_spr = len(spr_values[(spr_values > 5) & (spr_values <= 15)])
    high_spr = len(spr_values[spr_values > 15])

    logger.info(f"  Low SPR (≤5):    {low_spr:>3} ({low_spr/len(spr_values)*100:>5.1f}%)")
    logger.info(f"  Medium SPR (5-15): {med_spr:>3} ({med_spr/len(spr_values)*100:>5.1f}%)")
    logger.info(f"  High SPR (>15):  {high_spr:>3} ({high_spr/len(spr_values)*100:>5.1f}%)")


def analyze_positions():
    """Analisa distribuição de posições"""
    logger.info("\n" + "="*80)
    logger.info("ANÁLISE 4: POSIÇÕES DO VILÃO")
    logger.info("="*80)

    df = pd.read_parquet(DP_FILE)

    position_counts = df['villain_position'].value_counts()

    logger.info(f"\nTotal: {len(df)} decision points")
    logger.info(f"\nDistribuição:")

    for position, count in position_counts.items():
        pct = (count / len(df)) * 100
        bar = "█" * int(pct / 2)
        logger.info(f"  {position:>5}: {count:>3} ({pct:>5.1f}%) {bar}")


def analyze_board_textures():
    """Analisa board textures"""
    logger.info("\n" + "="*80)
    logger.info("ANÁLISE 5: BOARD TEXTURES")
    logger.info("="*80)

    df = pd.read_parquet(DP_FILE)

    # Filtrar apenas decision points pós-flop
    postflop_df = df[df['street'].isin(['flop', 'turn', 'river'])]

    logger.info(f"\nDecision points pós-flop: {len(postflop_df)}")

    if len(postflop_df) == 0:
        logger.warning("Sem decision points pós-flop para analisar")
        return

    # Extrair features de board texture
    textures = []

    for idx, row in postflop_df.iterrows():
        bt = row.get('board_texture')
        if bt and isinstance(bt, dict):
            textures.append(bt)

    if len(textures) == 0:
        logger.warning("Sem board textures disponíveis")
        return

    # Contar ocorrências de cada feature
    logger.info(f"\nBoard texture features:")

    for feature in ['monotone', 'paired', 'connected', 'high', 'wet', 'dry']:
        count = sum(1 for t in textures if t.get(feature, False))
        pct = (count / len(textures)) * 100
        logger.info(f"  {feature:>10}: {count:>3}/{len(textures)} ({pct:>5.1f}%)")


def analyze_villain_stats():
    """Análise por vilão"""
    logger.info("\n" + "="*80)
    logger.info("ANÁLISE 6: ESTATÍSTICAS POR VILÃO")
    logger.info("="*80)

    df = pd.read_parquet(DP_FILE)

    for villain in df['villain_name'].value_counts().head(5).index:
        villain_df = df[df['villain_name'] == villain]

        logger.info(f"\n{villain} ({len(villain_df)} decision points)")
        logger.info(f"{'-'*60}")

        # Streets
        streets = villain_df['street'].value_counts()
        logger.info(f"  Streets: {', '.join([f'{s}={c}' for s, c in streets.items()])}")

        # Positions
        positions = villain_df['villain_position'].value_counts()
        logger.info(f"  Positions: {', '.join([f'{p}={c}' for p, c in positions.items()])}")

        # Top ações
        actions = villain_df['villain_action'].value_counts().head(5)
        logger.info(f"  Top actions: {', '.join([f'{a}={c}' for a, c in actions.items()])}")

        # Avg pot size
        avg_pot = villain_df['pot_bb'].mean()
        logger.info(f"  Avg pot size: {avg_pot:.2f} BB")


def run_all_analyses():
    """Executa todas as análises"""

    logger.remove()
    logger.add(sys.stderr, level="INFO")

    logger.info("\n" + "="*80)
    logger.info("📊 ANÁLISE ESTATÍSTICA - SpinAnalyzer v2.0")
    logger.info("="*80)

    try:
        analyze_action_distribution()
        analyze_pot_sizes()
        analyze_spr()
        analyze_positions()
        analyze_board_textures()
        analyze_villain_stats()

        logger.info("\n" + "="*80)
        logger.success("✅ TODAS AS ANÁLISES CONCLUÍDAS!")
        logger.info("="*80)

    except Exception as e:
        logger.exception(f"❌ Erro durante análise: {e}")


if __name__ == "__main__":
    run_all_analyses()
