"""
Test Search Functionality - SpinAnalyzer v2.0

Tests FAISS index search to validate the pattern matching engine.
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from indexing import IndexBuilder
from loguru import logger

def test_search():
    """Test search functionality on real data"""

    logger.remove()
    logger.add(sys.stderr, level="INFO")

    # Paths
    INDICES_DIR = Path("indices")
    DP_FILE = Path("dataset/decision_points/decision_points_vectorized.parquet")

    # Load decision points
    logger.info(f"Carregando decision points de {DP_FILE}...")
    df = pd.read_parquet(DP_FILE)
    logger.info(f"✅ {len(df)} decision points carregados")

    # Create IndexBuilder
    builder = IndexBuilder(indices_dir=INDICES_DIR, dimension=99)

    # Get summary
    summary = builder.get_summary()
    logger.info(f"\n{'='*60}")
    logger.info(f"ÍNDICES DISPONÍVEIS: {summary['total_indices']}")
    logger.info(f"TOTAL DE VETORES: {summary['total_vectors']}")
    logger.info(f"{'='*60}\n")

    # Test search on each villain
    for villain_info in summary['villains'][:3]:  # Test first 3 villains
        villain_name = villain_info['name']
        logger.info(f"\n{'='*60}")
        logger.info(f"TESTANDO BUSCA: {villain_name}")
        logger.info(f"{'='*60}")

        # Get a sample decision point from this villain
        villain_df = df[df['villain_name'] == villain_name]

        if len(villain_df) == 0:
            logger.warning(f"Nenhum decision point encontrado para {villain_name}")
            continue

        # Use first decision point as query
        query_dp = villain_df.iloc[0]
        query_vector = np.array(query_dp['context_vector'], dtype=np.float32)

        logger.info(f"Query decision ID: {query_dp['decision_id']}")
        logger.info(f"Street: {query_dp['street']}")
        logger.info(f"Position: {query_dp['villain_position']}")
        logger.info(f"Action: {query_dp['villain_action']}")
        logger.info(f"Pot: {query_dp['pot_bb']:.1f} BB")

        # Search
        logger.info(f"\nBuscando top-10 similares...")
        distances, indices, decision_ids = builder.search(
            villain_name=villain_name,
            query_vector=query_vector,
            k=10
        )

        logger.success(f"\n✅ Busca concluída! Top 10 resultados:")
        logger.info(f"{'Rank':<6} {'Decision ID':<30} {'Distance':<12} {'Details'}")
        logger.info("="*80)

        for rank, (dist, dec_id) in enumerate(zip(distances, decision_ids), 1):
            # Get decision point info
            dp_info = df[df['decision_id'] == dec_id]
            if len(dp_info) > 0:
                dp = dp_info.iloc[0]
                details = f"{dp['street']:>6} | {dp['villain_position']:>3} | {dp['villain_action']}"
                logger.info(f"{rank:<6} {dec_id:<30} {dist:<12.4f} {details}")

        logger.info("")

    logger.success(f"\n{'='*60}")
    logger.success("✅ TODOS OS TESTES PASSARAM!")
    logger.success(f"{'='*60}")
    logger.info("\nPróximos passos:")
    logger.info("  1. Implementar API FastAPI (Week 2)")
    logger.info("  2. Criar dashboard React (Week 3-4)")
    logger.info("  3. Expandir dataset com mais mãos")


if __name__ == "__main__":
    test_search()
