"""
Master Pipeline Script - SpinAnalyzer v2.0

Executa pipeline completo:
1. Parse (XML/TXT/ZIP → PHH)
2. Context Extraction (PHH → Decision Points)
3. Vectorization (Decision Points → Vectors)
4. FAISS Indexing (Vectors → Indices)

Usage:
    python run_pipeline.py [--input-dir DIR] [--output-dir DIR]
"""

import sys
import argparse
from pathlib import Path
from loguru import logger
import time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from parsers import UnifiedParser
from context import ContextExtractor
from vectorization import Vectorizer
from indexing import IndexBuilder


def setup_logging(log_file: Path):
    """Configura logging"""
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    logger.add(log_file, level="DEBUG", rotation="10 MB")


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="SpinAnalyzer v2.0 - Pattern Matching Engine Pipeline"
    )

    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("dataset/original_hands/final"),
        help="Diretório com arquivos de entrada (XML, TXT, ZIP)"
    )

    parser.add_argument(
        "--phh-dir",
        type=Path,
        default=Path("dataset/phh_hands"),
        help="Diretório para salvar arquivos PHH"
    )

    parser.add_argument(
        "--dp-file",
        type=Path,
        default=Path("dataset/decision_points/decision_points.parquet"),
        help="Arquivo para salvar decision points"
    )

    parser.add_argument(
        "--indices-dir",
        type=Path,
        default=Path("indices"),
        help="Diretório para salvar índices FAISS"
    )

    parser.add_argument(
        "--dimension",
        type=int,
        default=99,
        help="Dimensão dos vetores"
    )

    parser.add_argument(
        "--skip-parse",
        action="store_true",
        help="Pular etapa de parsing (usar PHH existentes)"
    )

    parser.add_argument(
        "--skip-extract",
        action="store_true",
        help="Pular etapa de extração (usar decision points existentes)"
    )

    parser.add_argument(
        "--skip-vectorize",
        action="store_true",
        help="Pular etapa de vetorização"
    )

    parser.add_argument(
        "--index-type",
        choices=["HNSW", "Flat", "IVF"],
        default="HNSW",
        help="Tipo de índice FAISS"
    )

    return parser.parse_args()


def run_pipeline(args):
    """Executa pipeline completo"""

    start_time = time.time()

    logger.info("="*80)
    logger.info("SPINANALYZER v2.0 - PATTERN MATCHING ENGINE")
    logger.info("="*80)
    logger.info(f"Input: {args.input_dir}")
    logger.info(f"Output indices: {args.indices_dir}")
    logger.info("="*80)

    # ============================================
    # ETAPA 1: PARSING
    # ============================================

    if not args.skip_parse:
        logger.info("\n" + "="*80)
        logger.info("ETAPA 1: PARSING (XML/TXT/ZIP → PHH)")
        logger.info("="*80)

        parser = UnifiedParser(output_dir=args.phh_dir)

        phh_files = parser.parse_directory(
            input_dir=args.input_dir,
            filters={'heads_up_only': True}
        )

        logger.success(f"✅ Parsing concluído: {len(phh_files)} arquivos PHH gerados")
    else:
        logger.info("\n⏭ Pulando etapa de parsing (usando PHH existentes)")

    # ============================================
    # ETAPA 2: CONTEXT EXTRACTION
    # ============================================

    if not args.skip_extract:
        logger.info("\n" + "="*80)
        logger.info("ETAPA 2: CONTEXT EXTRACTION (PHH → Decision Points)")
        logger.info("="*80)

        extractor = ContextExtractor()

        df_decision_points = extractor.extract_from_directory(args.phh_dir)

        # Salvar
        args.dp_file.parent.mkdir(parents=True, exist_ok=True)
        df_decision_points.to_parquet(args.dp_file, index=False)

        logger.success(f"✅ Extração concluída: {len(df_decision_points)} decision points")
        logger.success(f"📁 Salvo em: {args.dp_file}")
    else:
        logger.info("\n⏭ Pulando etapa de extração (usando decision points existentes)")

        import pandas as pd
        df_decision_points = pd.read_parquet(args.dp_file)
        logger.info(f"Carregados {len(df_decision_points)} decision points de {args.dp_file}")

    # ============================================
    # ETAPA 3: VECTORIZATION
    # ============================================

    if not args.skip_vectorize:
        logger.info("\n" + "="*80)
        logger.info("ETAPA 3: VECTORIZATION (Decision Points → Vectors)")
        logger.info("="*80)

        vectorizer = Vectorizer()

        # Fit
        vectorizer.fit(df_decision_points)

        # Vetorizar
        vectors = vectorizer.vectorize_batch(df_decision_points)

        # Adicionar ao DataFrame
        df_decision_points['context_vector'] = list(vectors)

        # Salvar versão vetorizada
        vectorized_file = args.dp_file.parent / "decision_points_vectorized.parquet"
        df_decision_points.to_parquet(vectorized_file, index=False)

        logger.success(f"✅ Vetorização concluída: {vectors.shape}")
        logger.success(f"📁 Salvo em: {vectorized_file}")
    else:
        logger.info("\n⏭ Pulando etapa de vetorização")

        import pandas as pd
        vectorized_file = args.dp_file.parent / "decision_points_vectorized.parquet"
        df_decision_points = pd.read_parquet(vectorized_file)
        logger.info(f"Carregados {len(df_decision_points)} decision points vetorizados")

    # ============================================
    # ETAPA 4: FAISS INDEXING
    # ============================================

    logger.info("\n" + "="*80)
    logger.info("ETAPA 4: FAISS INDEXING (Vectors → Indices)")
    logger.info("="*80)

    builder = IndexBuilder(indices_dir=args.indices_dir, dimension=args.dimension)

    builder.build_indices_from_df(
        df_decision_points,
        index_type=args.index_type,
        hnsw_m=32
    )

    # ============================================
    # SUMÁRIO FINAL
    # ============================================

    elapsed_time = time.time() - start_time

    logger.info("\n" + "="*80)
    logger.info("PIPELINE CONCLUÍDO COM SUCESSO!")
    logger.info("="*80)

    summary = builder.get_summary()

    logger.info(f"Tempo total: {elapsed_time:.2f}s ({elapsed_time/60:.2f} min)")
    logger.info(f"\nÍndices criados: {summary['total_indices']}")
    logger.info(f"Total de vetores: {summary['total_vectors']}")
    logger.info(f"\nVilões indexados:")

    for villain_info in summary['villains']:
        logger.info(f"  • {villain_info['name']}: {villain_info['vectors']} decision points")

    logger.info(f"\n📁 Localização dos índices: {args.indices_dir}")
    logger.info(f"📁 Decision points: {args.dp_file}")

    logger.info("\n" + "="*80)
    logger.success("🎯 Sistema pronto para buscas!")
    logger.info("="*80)

    logger.info("\nPróximos passos:")
    logger.info("  1. Iniciar API: uvicorn src.api.main:app --reload")
    logger.info("  2. Testar busca: python test_search.py")
    logger.info("  3. Dashboard: cd frontend && npm run dev")

    return summary


if __name__ == "__main__":
    # Parse arguments
    args = parse_args()

    # Setup logging
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"pipeline_{time.strftime('%Y%m%d_%H%M%S')}.log"

    setup_logging(log_file)

    try:
        # Run pipeline
        summary = run_pipeline(args)

        sys.exit(0)

    except Exception as e:
        logger.exception(f"Erro fatal no pipeline: {e}")
        sys.exit(1)
