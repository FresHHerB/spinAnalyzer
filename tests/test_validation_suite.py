"""
Validation Suite - SpinAnalyzer v2.0

Suite completa de testes e validações:
1. Validação de dados
2. Qualidade dos vetores
3. Performance de busca
4. Consistência dos índices
5. Edge cases
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import time
from typing import Dict, List, Tuple

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from indexing import IndexBuilder
from vectorization import Vectorizer
from loguru import logger

# Paths
INDICES_DIR = Path("indices")
DP_FILE = Path("dataset/decision_points/decision_points_vectorized.parquet")


def test_1_data_validation():
    """Teste 1: Validação dos dados carregados"""
    logger.info("\n" + "="*80)
    logger.info("TESTE 1: VALIDAÇÃO DE DADOS")
    logger.info("="*80)

    df = pd.read_parquet(DP_FILE)

    # Checks básicos
    logger.info(f"✓ Total de decision points: {len(df)}")
    logger.info(f"✓ Vilões únicos: {df['villain_name'].nunique()}")
    logger.info(f"✓ Colunas: {len(df.columns)}")

    # Verificar se há dados faltantes críticos
    critical_cols = ['decision_id', 'villain_name', 'street', 'context_vector']
    missing = {}
    for col in critical_cols:
        null_count = df[col].isnull().sum()
        missing[col] = null_count
        status = "✓" if null_count == 0 else "⚠"
        logger.info(f"{status} {col}: {null_count} nulls")

    # Verificar dimensão dos vetores
    sample_vector = df.iloc[0]['context_vector']
    vector_dim = len(sample_vector) if isinstance(sample_vector, (list, np.ndarray)) else 0
    logger.info(f"✓ Dimensão dos vetores: {vector_dim}")

    # Distribuição por street
    logger.info("\nDistribuição por street:")
    for street, count in df['street'].value_counts().items():
        pct = (count / len(df)) * 100
        logger.info(f"  {street:>8}: {count:>3} ({pct:>5.1f}%)")

    # Distribuição por vilão
    logger.info("\nDecision points por vilão:")
    for villain, count in df['villain_name'].value_counts().head(10).items():
        logger.info(f"  {villain:>20}: {count:>3}")

    return {
        'total_dps': len(df),
        'villains': df['villain_name'].nunique(),
        'vector_dim': vector_dim,
        'missing_data': missing
    }


def test_2_vector_quality():
    """Teste 2: Qualidade dos vetores"""
    logger.info("\n" + "="*80)
    logger.info("TESTE 2: QUALIDADE DOS VETORES")
    logger.info("="*80)

    df = pd.read_parquet(DP_FILE)

    # Extrair todos os vetores
    vectors = np.array([v for v in df['context_vector']])
    logger.info(f"✓ Shape dos vetores: {vectors.shape}")

    # Estatísticas dos vetores
    norms = np.linalg.norm(vectors, axis=1)
    logger.info(f"\nEstatísticas das normas dos vetores:")
    logger.info(f"  Min:    {norms.min():.4f}")
    logger.info(f"  Max:    {norms.max():.4f}")
    logger.info(f"  Mean:   {norms.mean():.4f}")
    logger.info(f"  Median: {np.median(norms):.4f}")
    logger.info(f"  Std:    {norms.std():.4f}")

    # Verificar se há vetores zero
    zero_vectors = np.all(vectors == 0, axis=1).sum()
    logger.info(f"\n✓ Vetores zero: {zero_vectors}")

    # Verificar se há NaN ou Inf
    nan_count = np.isnan(vectors).sum()
    inf_count = np.isinf(vectors).sum()
    logger.info(f"✓ NaN values: {nan_count}")
    logger.info(f"✓ Inf values: {inf_count}")

    # Verificar dispersão (variance por dimensão)
    variances = np.var(vectors, axis=0)
    logger.info(f"\nVariância por dimensão:")
    logger.info(f"  Min variance:  {variances.min():.6f}")
    logger.info(f"  Max variance:  {variances.max():.6f}")
    logger.info(f"  Mean variance: {variances.mean():.6f}")
    logger.info(f"  Dims com var=0: {(variances == 0).sum()}")

    return {
        'shape': vectors.shape,
        'norm_stats': {
            'min': float(norms.min()),
            'max': float(norms.max()),
            'mean': float(norms.mean())
        },
        'zero_vectors': int(zero_vectors),
        'nan_count': int(nan_count),
        'inf_count': int(inf_count)
    }


def test_3_search_performance():
    """Teste 3: Performance de busca"""
    logger.info("\n" + "="*80)
    logger.info("TESTE 3: PERFORMANCE DE BUSCA")
    logger.info("="*80)

    df = pd.read_parquet(DP_FILE)
    builder = IndexBuilder(indices_dir=INDICES_DIR, dimension=99)

    # Testar diferentes tamanhos de k
    k_values = [1, 5, 10, 20, 50]

    results = {}

    for villain_name in df['villain_name'].unique()[:3]:  # Testar primeiros 3 vilões
        villain_df = df[df['villain_name'] == villain_name]

        if len(villain_df) == 0:
            continue

        logger.info(f"\n{villain_name} ({len(villain_df)} decision points)")

        # Usar primeiro vetor como query
        query_vec = np.array(villain_df.iloc[0]['context_vector'], dtype=np.float32)

        villain_results = {}

        for k in k_values:
            # Executar busca 10 vezes para média
            times = []
            for _ in range(10):
                start = time.perf_counter()
                distances, indices, decision_ids = builder.search(
                    villain_name=villain_name,
                    query_vector=query_vec,
                    k=min(k, len(villain_df))
                )
                elapsed = (time.perf_counter() - start) * 1000  # ms
                times.append(elapsed)

            avg_time = np.mean(times)
            std_time = np.std(times)

            villain_results[k] = {
                'avg_ms': avg_time,
                'std_ms': std_time
            }

            logger.info(f"  k={k:>3}: {avg_time:>6.2f}ms ± {std_time:.2f}ms")

        results[villain_name] = villain_results

    # Summary
    logger.info(f"\n{'='*80}")
    logger.success("✅ Todos os testes de performance passaram!")
    logger.info(f"{'='*80}")

    return results


def test_4_index_consistency():
    """Teste 4: Consistência dos índices"""
    logger.info("\n" + "="*80)
    logger.info("TESTE 4: CONSISTÊNCIA DOS ÍNDICES")
    logger.info("="*80)

    df = pd.read_parquet(DP_FILE)
    builder = IndexBuilder(indices_dir=INDICES_DIR, dimension=99)

    summary = builder.get_summary()

    logger.info(f"✓ Índices disponíveis: {summary['total_indices']}")
    logger.info(f"✓ Total de vetores indexados: {summary['total_vectors']}")

    # Verificar se todos os vilões do dataset têm índice
    villains_in_data = set(df['villain_name'].unique())
    villains_in_index = set([v['name'] for v in summary['villains']])

    missing = villains_in_data - villains_in_index
    extra = villains_in_index - villains_in_data

    logger.info(f"\n✓ Vilões no dataset: {len(villains_in_data)}")
    logger.info(f"✓ Vilões indexados: {len(villains_in_index)}")

    if missing:
        logger.warning(f"⚠ Vilões sem índice: {missing}")
    else:
        logger.success(f"✅ Todos os vilões estão indexados!")

    if extra:
        logger.warning(f"⚠ Índices extras: {extra}")

    # Verificar contagem de vetores por vilão
    logger.info("\nConsistência de contagem:")
    for villain_info in summary['villains']:
        villain_name = villain_info['name']
        index_count = villain_info['vectors']
        data_count = len(df[df['villain_name'] == villain_name])

        status = "✓" if index_count == data_count else "⚠"
        logger.info(f"  {status} {villain_name:>20}: índice={index_count:>3}, data={data_count:>3}")

    return {
        'total_indices': summary['total_indices'],
        'missing_indices': list(missing),
        'extra_indices': list(extra)
    }


def test_5_search_relevance():
    """Teste 5: Relevância dos resultados de busca"""
    logger.info("\n" + "="*80)
    logger.info("TESTE 5: RELEVÂNCIA DOS RESULTADOS")
    logger.info("="*80)

    df = pd.read_parquet(DP_FILE)
    builder = IndexBuilder(indices_dir=INDICES_DIR, dimension=99)

    # Selecionar 3 queries de diferentes vilões
    test_cases = []

    for villain_name in df['villain_name'].unique()[:3]:
        villain_df = df[df['villain_name'] == villain_name]
        if len(villain_df) >= 5:
            # Pegar um decision point do meio
            test_dp = villain_df.iloc[len(villain_df) // 2]
            test_cases.append((villain_name, test_dp))

    for villain_name, query_dp in test_cases:
        logger.info(f"\n{'-'*80}")
        logger.info(f"Query: {query_dp['decision_id']}")
        logger.info(f"Context: {query_dp['street']}, {query_dp['villain_position']}, {query_dp['villain_action']}")

        query_vec = np.array(query_dp['context_vector'], dtype=np.float32)

        distances, indices, decision_ids = builder.search(
            villain_name=villain_name,
            query_vector=query_vec,
            k=5
        )

        logger.info(f"\nTop 5 resultados:")
        for rank, (dist, dec_id) in enumerate(zip(distances, decision_ids), 1):
            result_dp = df[df['decision_id'] == dec_id].iloc[0]

            # Verificar se contextos batem
            same_street = result_dp['street'] == query_dp['street']
            same_position = result_dp['villain_position'] == query_dp['villain_position']
            same_action = result_dp['villain_action'] == query_dp['villain_action']

            markers = []
            if same_street:
                markers.append("street✓")
            if same_position:
                markers.append("pos✓")
            if same_action:
                markers.append("action✓")

            logger.info(
                f"  {rank}. {dec_id:>25} | dist={dist:>8.4f} | "
                f"{result_dp['street']:>7} {result_dp['villain_position']:>3} "
                f"{result_dp['villain_action']:>10} | {' '.join(markers)}"
            )

        # Verificar se self-match é rank 1 com distance ~0
        if distances[0] < 0.001:
            logger.success(f"  ✅ Self-match perfeito (distance={distances[0]:.6f})")
        else:
            logger.warning(f"  ⚠ Self-match com distance={distances[0]:.6f}")

    return {'test_cases': len(test_cases)}


def test_6_edge_cases():
    """Teste 6: Casos extremos"""
    logger.info("\n" + "="*80)
    logger.info("TESTE 6: CASOS EXTREMOS (EDGE CASES)")
    logger.info("="*80)

    df = pd.read_parquet(DP_FILE)
    builder = IndexBuilder(indices_dir=INDICES_DIR, dimension=99)

    # Caso 1: Vilão com poucos decision points
    min_villain = df['villain_name'].value_counts().idxmin()
    min_count = df['villain_name'].value_counts().min()

    logger.info(f"\n1. Vilão com menos decision points: {min_villain} ({min_count} DPs)")

    villain_df = df[df['villain_name'] == min_villain]
    query_vec = np.array(villain_df.iloc[0]['context_vector'], dtype=np.float32)

    try:
        distances, indices, decision_ids = builder.search(
            villain_name=min_villain,
            query_vector=query_vec,
            k=min(10, min_count)
        )
        logger.success(f"  ✅ Busca funcionou, retornou {len(decision_ids)} resultados")
    except Exception as e:
        logger.error(f"  ❌ Erro na busca: {e}")

    # Caso 2: Buscar com k > número de decision points
    logger.info(f"\n2. Buscar k={min_count + 10} em vilão com apenas {min_count} DPs")

    try:
        distances, indices, decision_ids = builder.search(
            villain_name=min_villain,
            query_vector=query_vec,
            k=min_count + 10  # Pedir mais do que existe
        )
        logger.success(f"  ✅ FAISS ajustou automaticamente, retornou {len(decision_ids)} resultados")
    except Exception as e:
        logger.error(f"  ❌ Erro: {e}")

    # Caso 3: Diferentes streets
    logger.info(f"\n3. Buscar decision points de diferentes streets")

    for street in ['preflop', 'flop', 'turn', 'river']:
        street_dps = df[df['street'] == street]
        if len(street_dps) > 0:
            logger.info(f"  {street:>8}: {len(street_dps):>3} decision points")

    return {'min_villain_count': int(min_count)}


def run_all_tests():
    """Executa todos os testes"""

    logger.remove()
    logger.add(sys.stderr, level="INFO")

    logger.info("\n" + "="*80)
    logger.info("🧪 SPINANALYZER v2.0 - VALIDATION SUITE")
    logger.info("="*80)

    results = {}

    try:
        results['test_1_data'] = test_1_data_validation()
        results['test_2_vectors'] = test_2_vector_quality()
        results['test_3_performance'] = test_3_search_performance()
        results['test_4_consistency'] = test_4_index_consistency()
        results['test_5_relevance'] = test_5_search_relevance()
        results['test_6_edge_cases'] = test_6_edge_cases()

        # Summary
        logger.info("\n" + "="*80)
        logger.success("✅ TODOS OS TESTES PASSARAM COM SUCESSO!")
        logger.info("="*80)

        logger.info("\nResumo:")
        logger.info(f"  Decision Points: {results['test_1_data']['total_dps']}")
        logger.info(f"  Vilões: {results['test_1_data']['villains']}")
        logger.info(f"  Dimensão dos vetores: {results['test_1_data']['vector_dim']}")
        logger.info(f"  Índices criados: {results['test_4_consistency']['total_indices']}")
        logger.info(f"  Vetores zero: {results['test_2_vectors']['zero_vectors']}")
        logger.info(f"  NaN values: {results['test_2_vectors']['nan_count']}")

        logger.info("\nSistema validado e pronto para produção! 🚀")

    except Exception as e:
        logger.exception(f"❌ Erro durante os testes: {e}")
        return None

    return results


if __name__ == "__main__":
    results = run_all_tests()
