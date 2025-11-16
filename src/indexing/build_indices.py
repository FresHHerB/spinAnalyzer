"""
Index Builder - Constrói e gerencia índices FAISS

Cria índices particionados por vilão para busca eficiente
"""

import faiss
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import json
from loguru import logger
import pickle


@dataclass
class IndexMetadata:
    """Metadata de um índice FAISS"""
    villain_name: str
    total_vectors: int
    dimension: int
    index_type: str  # "HNSW", "Flat", "IVF", etc
    created_at: str
    decision_point_ids: List[str]  # Mapeamento de IDs
    stats: Dict

    def to_dict(self) -> Dict:
        return asdict(self)

    def save(self, path: Path):
        """Salva metadata em JSON"""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: Path):
        """Carrega metadata de JSON"""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls(**data)


class IndexBuilder:
    """
    Constrói e gerencia índices FAISS particionados por vilão
    """

    def __init__(self, indices_dir: Path, dimension: int = 104):
        """
        Args:
            indices_dir: Diretório para salvar índices
            dimension: Dimensão dos vetores
        """
        self.indices_dir = Path(indices_dir)
        self.indices_dir.mkdir(parents=True, exist_ok=True)

        self.dimension = dimension
        self.indices = {}  # {villain_name: faiss.Index}
        self.metadata = {}  # {villain_name: IndexMetadata}

        logger.info(f"IndexBuilder inicializado")
        logger.info(f"Diretório de índices: {self.indices_dir}")
        logger.info(f"Dimensão dos vetores: {self.dimension}")

    def build_indices_from_df(
        self,
        df: pd.DataFrame,
        index_type: str = "HNSW",
        hnsw_m: int = 32
    ):
        """
        Constrói índices FAISS a partir de DataFrame com decision points

        Args:
            df: DataFrame com colunas:
                - villain_name
                - context_vector (array de floats)
                - decision_id
            index_type: Tipo de índice ("HNSW", "Flat", "IVF")
            hnsw_m: Parâmetro M para HNSW (conexões por nó)
        """
        logger.info(f"\nConstruindo índices FAISS ({index_type})...")
        logger.info(f"Total de decision points: {len(df)}")

        # Agrupar por vilão
        villains = df['villain_name'].unique()
        logger.info(f"Vilões encontrados: {len(villains)}")

        for villain in villains:
            logger.info(f"\n{'='*60}")
            logger.info(f"Processando vilão: {villain}")
            logger.info(f"{'='*60}")

            # Filtrar decision points deste vilão
            villain_df = df[df['villain_name'] == villain].copy()

            logger.info(f"Decision points: {len(villain_df)}")

            # Extrair vetores
            vectors = self._extract_vectors_from_df(villain_df)

            if len(vectors) == 0:
                logger.warning(f"Nenhum vetor válido para {villain}, pulando...")
                continue

            # Extrair decision IDs
            decision_ids = villain_df['decision_id'].tolist()

            # Construir índice
            index = self._create_faiss_index(
                vectors,
                index_type=index_type,
                hnsw_m=hnsw_m
            )

            # Salvar índice
            self._save_index(villain, index, decision_ids, vectors)

            logger.success(f"✅ Índice criado para {villain}")

        logger.info(f"\n{'='*60}")
        logger.success(f"✅ Todos os índices criados!")
        logger.info(f"{'='*60}")
        logger.info(f"Total de índices: {len(self.indices)}")
        logger.info(f"Localização: {self.indices_dir}")

    def _extract_vectors_from_df(self, df: pd.DataFrame) -> np.ndarray:
        """
        Extrai vetores do DataFrame

        Args:
            df: DataFrame com coluna 'context_vector'

        Returns:
            Array numpy de shape [n_samples, dimension]
        """
        vectors = []

        for idx, row in df.iterrows():
            vec = row.get('context_vector')

            # Converter para numpy array se necessário
            if isinstance(vec, list):
                vec = np.array(vec, dtype=np.float32)
            elif isinstance(vec, str):
                # Pode estar serializado como string
                try:
                    vec = np.array(json.loads(vec), dtype=np.float32)
                except:
                    logger.warning(f"Não foi possível parsear vetor do índice {idx}")
                    continue

            if vec is not None and len(vec) == self.dimension:
                vectors.append(vec)

        if len(vectors) == 0:
            return np.array([], dtype=np.float32).reshape(0, self.dimension)

        return np.array(vectors, dtype=np.float32)

    def _create_faiss_index(
        self,
        vectors: np.ndarray,
        index_type: str = "HNSW",
        hnsw_m: int = 32
    ) -> faiss.Index:
        """
        Cria índice FAISS

        Args:
            vectors: Array de vetores [n_samples, dimension]
            index_type: Tipo de índice
            hnsw_m: Parâmetro M para HNSW

        Returns:
            faiss.Index
        """
        n_vectors, dim = vectors.shape

        logger.info(f"Criando índice {index_type}...")
        logger.info(f"  Vetores: {n_vectors}")
        logger.info(f"  Dimensão: {dim}")

        if index_type == "HNSW":
            # HNSW (Hierarchical Navigable Small World)
            # Ótimo para busca aproximada rápida
            index = faiss.IndexHNSWFlat(dim, hnsw_m)

            # Configurações
            index.hnsw.efConstruction = 200  # Qualidade da construção
            index.hnsw.efSearch = 64         # Qualidade da busca

            logger.info(f"  HNSW M: {hnsw_m}")
            logger.info(f"  efConstruction: 200")
            logger.info(f"  efSearch: 64")

        elif index_type == "Flat":
            # Flat (busca exata, mais lento mas preciso)
            index = faiss.IndexFlatL2(dim)

            logger.info(f"  Tipo: Flat (busca exata)")

        elif index_type == "IVF":
            # IVF (Inverted File Index)
            # Bom para datasets grandes
            n_centroids = min(int(np.sqrt(n_vectors)), 256)
            quantizer = faiss.IndexFlatL2(dim)
            index = faiss.IndexIVFFlat(quantizer, dim, n_centroids)

            # Treinar
            logger.info(f"  Treinando IVF com {n_centroids} centroids...")
            index.train(vectors)

            logger.info(f"  Tipo: IVF")
            logger.info(f"  Centroids: {n_centroids}")

        else:
            raise ValueError(f"Tipo de índice desconhecido: {index_type}")

        # Adicionar vetores ao índice
        logger.info(f"Adicionando {n_vectors} vetores ao índice...")
        index.add(vectors)

        logger.success(f"✅ Índice criado com sucesso!")
        logger.info(f"  Total no índice: {index.ntotal}")

        return index

    def _save_index(
        self,
        villain_name: str,
        index: faiss.Index,
        decision_ids: List[str],
        vectors: np.ndarray
    ):
        """
        Salva índice e metadata

        Args:
            villain_name: Nome do vilão
            index: Índice FAISS
            decision_ids: Lista de decision IDs
            vectors: Vetores (para calcular stats)
        """
        # Paths
        index_path = self.indices_dir / f"{villain_name}.faiss"
        metadata_path = self.indices_dir / f"{villain_name}_metadata.json"
        ids_path = self.indices_dir / f"{villain_name}_ids.pkl"

        # Salvar índice FAISS
        faiss.write_index(index, str(index_path))
        logger.info(f"  Índice salvo: {index_path.name}")

        # Salvar decision IDs (mapeamento)
        with open(ids_path, 'wb') as f:
            pickle.dump(decision_ids, f)
        logger.info(f"  IDs salvos: {ids_path.name}")

        # Calcular stats
        stats = {
            "min_norm": float(np.min(np.linalg.norm(vectors, axis=1))),
            "max_norm": float(np.max(np.linalg.norm(vectors, axis=1))),
            "mean_norm": float(np.mean(np.linalg.norm(vectors, axis=1))),
            "std_norm": float(np.std(np.linalg.norm(vectors, axis=1)))
        }

        # Criar metadata
        from datetime import datetime

        metadata = IndexMetadata(
            villain_name=villain_name,
            total_vectors=len(decision_ids),
            dimension=self.dimension,
            index_type=type(index).__name__,
            created_at=datetime.now().isoformat(),
            decision_point_ids=decision_ids[:100],  # Primeiros 100 para referência
            stats=stats
        )

        # Salvar metadata
        metadata.save(metadata_path)
        logger.info(f"  Metadata salvo: {metadata_path.name}")

        # Armazenar em memória
        self.indices[villain_name] = index
        self.metadata[villain_name] = metadata

    def load_index(self, villain_name: str) -> Tuple[faiss.Index, IndexMetadata, List[str]]:
        """
        Carrega índice de um vilão

        Args:
            villain_name: Nome do vilão

        Returns:
            (index, metadata, decision_ids)
        """
        index_path = self.indices_dir / f"{villain_name}.faiss"
        metadata_path = self.indices_dir / f"{villain_name}_metadata.json"
        ids_path = self.indices_dir / f"{villain_name}_ids.pkl"

        if not index_path.exists():
            raise FileNotFoundError(f"Índice não encontrado para {villain_name}")

        # Carregar índice
        index = faiss.read_index(str(index_path))

        # Carregar metadata
        metadata = IndexMetadata.load(metadata_path)

        # Carregar IDs
        with open(ids_path, 'rb') as f:
            decision_ids = pickle.load(f)

        logger.info(f"Índice carregado: {villain_name}")
        logger.info(f"  Vetores: {index.ntotal}")
        logger.info(f"  Dimensão: {metadata.dimension}")

        return index, metadata, decision_ids

    def search(
        self,
        villain_name: str,
        query_vector: np.ndarray,
        k: int = 50
    ) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """
        Busca k-nearest neighbors

        Args:
            villain_name: Nome do vilão
            query_vector: Vetor de query [dimension]
            k: Número de vizinhos a retornar

        Returns:
            (distances, indices, decision_ids)
        """
        # Carregar índice se não estiver em memória
        if villain_name not in self.indices:
            index, metadata, decision_ids = self.load_index(villain_name)
            self.indices[villain_name] = index
            self.metadata[villain_name] = metadata
        else:
            index = self.indices[villain_name]
            # Carregar IDs
            ids_path = self.indices_dir / f"{villain_name}_ids.pkl"
            with open(ids_path, 'rb') as f:
                decision_ids = pickle.load(f)

        # Reshape query vector
        query_vector = query_vector.reshape(1, -1).astype(np.float32)

        # Buscar
        distances, indices = index.search(query_vector, k)

        # Mapear índices para decision IDs
        result_ids = [decision_ids[idx] for idx in indices[0] if idx < len(decision_ids)]

        return distances[0], indices[0], result_ids

    def list_available_villains(self) -> List[str]:
        """
        Lista todos os vilões com índices disponíveis

        Returns:
            Lista de nomes de vilões
        """
        villains = []

        for file in self.indices_dir.glob("*.faiss"):
            villain_name = file.stem
            villains.append(villain_name)

        return sorted(villains)

    def get_summary(self) -> Dict:
        """
        Retorna sumário de todos os índices

        Returns:
            Dicionário com informações de todos os índices
        """
        summary = {
            "total_indices": 0,
            "total_vectors": 0,
            "villains": []
        }

        for villain in self.list_available_villains():
            metadata_path = self.indices_dir / f"{villain}_metadata.json"

            if metadata_path.exists():
                metadata = IndexMetadata.load(metadata_path)

                summary["total_indices"] += 1
                summary["total_vectors"] += metadata.total_vectors

                summary["villains"].append({
                    "name": villain,
                    "vectors": metadata.total_vectors,
                    "created_at": metadata.created_at
                })

        return summary


# ============================================
# SCRIPT DE TESTE
# ============================================

if __name__ == "__main__":
    import sys

    # Configurar logging
    logger.remove()
    logger.add(sys.stderr, level="INFO")

    # Paths
    VECTORIZED_FILE = Path(r"D:\code\python\spinAnalyzer\dataset\decision_points\decision_points_vectorized.parquet")
    INDICES_DIR = Path(r"D:\code\python\spinAnalyzer\indices")

    if not VECTORIZED_FILE.exists():
        logger.error(f"Arquivo não encontrado: {VECTORIZED_FILE}")
        logger.info("Execute vectorizer.py primeiro!")
        sys.exit(1)

    # Carregar decision points vetorizados
    logger.info(f"Carregando decision points de {VECTORIZED_FILE}...")
    df = pd.read_parquet(VECTORIZED_FILE)

    logger.info(f"Decision points carregados: {len(df)}")
    logger.info(f"Vilões únicos: {df['villain_name'].nunique()}")

    # Criar IndexBuilder
    builder = IndexBuilder(indices_dir=INDICES_DIR, dimension=104)

    # Construir índices
    builder.build_indices_from_df(df, index_type="HNSW", hnsw_m=32)

    # Sumário
    logger.info(f"\n{'='*60}")
    logger.info("SUMÁRIO DOS ÍNDICES")
    logger.info(f"{'='*60}")

    summary = builder.get_summary()

    logger.info(f"Total de índices: {summary['total_indices']}")
    logger.info(f"Total de vetores: {summary['total_vectors']}")
    logger.info(f"\nVilões indexados:")

    for villain_info in summary['villains']:
        logger.info(f"  • {villain_info['name']}: {villain_info['vectors']} decision points")

    # Teste de busca
    if len(summary['villains']) > 0:
        logger.info(f"\n{'='*60}")
        logger.info("TESTE DE BUSCA")
        logger.info(f"{'='*60}")

        # Pegar primeiro vilão
        test_villain = summary['villains'][0]['name']
        test_df = df[df['villain_name'] == test_villain]

        if len(test_df) > 0:
            # Usar primeiro vetor como query
            query_vec = test_df.iloc[0]['context_vector']

            if isinstance(query_vec, list):
                query_vec = np.array(query_vec, dtype=np.float32)

            logger.info(f"Testando busca para vilão: {test_villain}")
            logger.info(f"Query vector shape: {query_vec.shape}")

            # Buscar
            distances, indices, decision_ids = builder.search(
                villain_name=test_villain,
                query_vector=query_vec,
                k=10
            )

            logger.success(f"\n✅ Busca bem-sucedida!")
            logger.info(f"Top 10 resultados:")

            for i, (dist, dec_id) in enumerate(zip(distances[:10], decision_ids[:10])):
                logger.info(f"  {i+1}. Decision ID: {dec_id} | Distance: {dist:.4f}")

    logger.success(f"\n✅ Todos os índices foram criados e testados!")
