"""
Service wrapper for IndexBuilder
Simplifies index building after file uploads
"""

from pathlib import Path
from typing import Dict
from loguru import logger

from src.indexing.build_indices import IndexBuilder as CoreIndexBuilder
from src.vectorization.vectorizer import Vectorizer


class IndexBuilder:
    """
    Simplified IndexBuilder service for file uploads

    Rebuilds all FAISS indices after new PHH files are added
    """

    def __init__(self, phh_dir: Path, indices_dir: Path):
        """
        Args:
            phh_dir: Directory containing PHH files
            indices_dir: Directory to store FAISS indices
        """
        self.phh_dir = Path(phh_dir)
        self.indices_dir = Path(indices_dir)

        # Ensure directories exist
        self.phh_dir.mkdir(parents=True, exist_ok=True)
        self.indices_dir.mkdir(parents=True, exist_ok=True)

    def build_all_indices(self) -> Dict:
        """
        Rebuild all FAISS indices from PHH files

        Pipeline completo:
        1. Context Extraction: PHH → Decision Points
        2. Vectorization: Decision Points → Vectors
        3. FAISS Indexing: Vectors → Indices

        Returns:
            Statistics about index building
        """
        try:
            logger.info("Starting full index rebuild pipeline...")

            # Import required modules
            from src.context.context_extractor import ContextExtractor
            from src.vectorization.vectorizer import Vectorizer
            import pandas as pd

            # ============================================
            # ETAPA 1: CONTEXT EXTRACTION
            # ============================================
            logger.info("STEP 1/3: Extracting decision points from PHH files...")

            extractor = ContextExtractor()
            df_decision_points = extractor.extract_from_directory(self.phh_dir)

            if len(df_decision_points) == 0:
                logger.warning("No decision points extracted. No indices will be built.")
                return {
                    "status": "success",
                    "message": "No decision points found",
                    "phh_dir": str(self.phh_dir),
                    "decision_points": 0
                }

            logger.info(f"✓ Extracted {len(df_decision_points)} decision points")

            # ============================================
            # ETAPA 2: VECTORIZATION
            # ============================================
            logger.info("STEP 2/3: Vectorizing decision points...")

            vectorizer = Vectorizer()
            vectorizer.fit(df_decision_points)

            vectors = vectorizer.vectorize_batch(df_decision_points)
            df_decision_points['context_vector'] = list(vectors)

            logger.info(f"✓ Vectorized {len(vectors)} decision points (dimension: {vectors.shape[1]})")

            # ============================================
            # SALVAR DECISION POINTS VETORIZADOS
            # ============================================
            logger.info("Saving vectorized decision points to parquet...")

            decision_points_file = Path("dataset/decision_points/decision_points_vectorized.parquet")
            decision_points_file.parent.mkdir(parents=True, exist_ok=True)
            df_decision_points.to_parquet(decision_points_file, index=False)

            logger.success(f"✓ Saved {len(df_decision_points)} decision points to {decision_points_file}")

            # ============================================
            # ETAPA 3: FAISS INDEXING
            # ============================================
            logger.info("STEP 3/3: Building FAISS indices...")

            builder = CoreIndexBuilder(
                indices_dir=self.indices_dir,
                dimension=99
            )

            builder.build_indices_from_df(
                df_decision_points,
                index_type="HNSW",
                hnsw_m=32
            )

            # Get summary
            summary = builder.get_summary()

            logger.success("✅ Index rebuild completed!")
            logger.info(f"  Villains: {summary['total_indices']}")
            logger.info(f"  Vectors: {summary['total_vectors']}")

            return {
                "status": "success",
                "total_indices": summary['total_indices'],
                "total_vectors": summary['total_vectors'],
                "villains": summary['villains'],
                "phh_dir": str(self.phh_dir),
                "indices_dir": str(self.indices_dir)
            }

        except Exception as e:
            logger.error(f"Error building indices: {e}")
            logger.exception("Full traceback:")
            return {
                "status": "error",
                "error": str(e)
            }
