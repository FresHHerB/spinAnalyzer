"""End-to-end: parse raw iPoker XMLs → PHH → DPs → vectors.

Measures dataset-growth yield from the XML parser completion (Phase 1.4)
and confirms the v2 pipeline scales beyond the 134-PHH zip.
"""

from __future__ import annotations

import time
from collections import Counter
from pathlib import Path

import pytest

from src.context.extractor_v2 import extract_decision_points
from src.parsers.pokerkit_adapter import load_phh
from src.parsers.unified_parser import UnifiedParser

REPO_ROOT = Path(__file__).parents[2]
RAW_XML_DIR = REPO_ROOT / "dataset" / "original_hands" / "final"


@pytest.mark.integration
def test_xml_regrow_pipeline(tmp_path: Path) -> None:
    if not RAW_XML_DIR.exists():
        pytest.skip(f"{RAW_XML_DIR} not found")

    # Sample 200 XMLs to keep the test fast (full set is 3,540)
    xml_files = sorted(RAW_XML_DIR.glob("*.xml"))[:200]
    if not xml_files:
        pytest.skip("no XML files in fixture dir")

    parser = UnifiedParser(output_dir=tmp_path / "phh_out")
    start = time.perf_counter()

    phh_paths: list[Path] = []
    for xml in xml_files:
        phh_paths.extend(parser.parse_file(xml, filters={"heads_up_only": True}))
    parse_elapsed = time.perf_counter() - start
    print(
        f"\n[REGROW] parsed {len(xml_files)} XMLs → {len(phh_paths)} HU PHHs "
        f"in {parse_elapsed:.2f}s"
    )
    assert len(phh_paths) > 0, "no HU PHHs produced from sample XMLs"

    # Run full v2 pipeline on the new PHHs
    start = time.perf_counter()
    all_dps = []
    parse_errors = 0
    for f in phh_paths:
        try:
            all_dps.extend(extract_decision_points(load_phh(f)))
        except Exception:
            parse_errors += 1
    pipeline_elapsed = time.perf_counter() - start
    print(
        f"[REGROW] extracted {len(all_dps)} DPs from {len(phh_paths)} PHHs "
        f"in {pipeline_elapsed:.2f}s ({parse_errors} errors)"
    )

    # Coverage assertions
    streets = Counter(dp.street for dp in all_dps)
    print(f"[REGROW] DPs by street: {dict(streets)}")
    assert (streets["flop"] + streets["turn"] + streets["river"]) > 0

    revealed = [dp for dp in all_dps if dp.villain_hand is not None]
    print(f"[REGROW] DPs with villain holdings revealed: {len(revealed)}")

    villains = {dp.villain_name for dp in all_dps}
    print(f"[REGROW] distinct villains: {len(villains)}")
    assert len(villains) >= 1
