"""Tests for src/parsers/unified_parser.py — XML iPoker parser completion."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import tomli

from src.parsers.pokerkit_adapter import load_phh, replay_to_list
from src.parsers.unified_parser import UnifiedParser

REPO_ROOT = Path(__file__).parents[3]
RAW_XML_DIR = REPO_ROOT / "dataset" / "original_hands" / "final"


@pytest.fixture
def parser(tmp_path: Path) -> UnifiedParser:
    return UnifiedParser(output_dir=tmp_path)


@pytest.fixture
def sample_xml_file() -> Path:
    f = RAW_XML_DIR / "8384733544.xml"
    if not f.exists():
        pytest.skip(f"{f} not found")
    return f


class TestXMLGameToPHH:
    def test_extracts_metadata_and_players(self, parser: UnifiedParser,
                                            sample_xml_file: Path) -> None:
        tree = ET.parse(sample_xml_file)
        root = tree.getroot()
        nick = root.find('./general/nickname')
        hero = nick.text if nick is not None else ''

        # Find the first 2-player game (HU)
        for g in root.findall('.//game'):
            if len(g.findall('.//player')) == 2:
                phh = parser._xml_game_to_phh(g, hero_name=hero)
                assert phh is not None
                assert phh['metadata']['game'] == 'NLHE'
                assert phh['metadata']['room'] == 'iPoker'
                assert phh['metadata']['hero']
                assert phh['metadata']['hand_id']
                assert len(phh['players']) == 2
                # Exactly one BTN
                assert sum(p['is_btn'] for p in phh['players']) == 1
                return
        pytest.skip("no HU games in fixture")

    def test_extracts_actions_with_streets(self, parser: UnifiedParser,
                                            sample_xml_file: Path) -> None:
        tree = ET.parse(sample_xml_file)
        root = tree.getroot()
        hero = root.find('./general/nickname').text

        for g in root.findall('.//game'):
            if len(g.findall('.//player')) == 2:
                phh = parser._xml_game_to_phh(g, hero_name=hero)
                if phh is None:
                    continue
                actions = phh['actions']
                assert actions, "no actions extracted"
                # At least one action per street tag must be valid
                streets = {a['street'] for a in actions if a.get('event') == 'action'}
                assert 'preflop' in streets
                # Action types are PHH verbs
                verbs = {a['action'] for a in actions if a.get('event') == 'action'}
                assert verbs.issubset({
                    'fold', 'call', 'check', 'bet', 'raise', 'all_in',
                    'ante', 'posts_sb', 'posts_bb',
                })
                return

    def test_extracts_board_cards_when_present(self, parser: UnifiedParser,
                                                sample_xml_file: Path) -> None:
        tree = ET.parse(sample_xml_file)
        root = tree.getroot()
        hero = root.find('./general/nickname').text

        # Find a game that reached at least the flop
        for g in root.findall('.//game'):
            if len(g.findall('.//player')) != 2:
                continue
            phh = parser._xml_game_to_phh(g, hero_name=hero)
            if phh is None:
                continue
            board_events = [a for a in phh['actions']
                            if a.get('event') == 'cards' and 'player' not in a]
            if board_events:
                # First board event should be flop with 3 cards
                first = board_events[0]
                assert first['street'] == 'flop'
                assert len(first['cards']) == 3
                return

    def test_round_trip_xml_to_phh_to_pokerkit(
        self, parser: UnifiedParser, sample_xml_file: Path, tmp_path: Path,
    ) -> None:
        """Parse XML → write PHH → load PHH → replay through PokerKit."""
        out = parser.parse_file(sample_xml_file, filters={'heads_up_only': True})
        assert len(out) > 0, "no PHHs generated from sample XML"

        replayed = 0
        for phh_path in out[:5]:  # sample first 5
            try:
                hand = load_phh(phh_path)
                snaps = replay_to_list(hand)
                replayed += 1
                # At least the blinds-then-action sequence
                assert snaps or hand.bb > 0
            except Exception as e:
                pytest.fail(f"PokerKit replay failed for {phh_path.name}: {e}")
        assert replayed > 0


class TestParseFileEndToEnd:
    def test_parse_xml_file_writes_phh_files(
        self, parser: UnifiedParser, sample_xml_file: Path
    ) -> None:
        out = parser.parse_file(sample_xml_file, filters={'heads_up_only': True})
        assert all(p.suffix == '.phh' for p in out)
        assert all(p.exists() for p in out)
        # At least 1 HU hand in this 17-game session file
        assert len(out) > 0

    def test_phh_files_are_valid_toml(
        self, parser: UnifiedParser, sample_xml_file: Path
    ) -> None:
        out = parser.parse_file(sample_xml_file, filters={'heads_up_only': True})
        for phh_path in out[:3]:
            with open(phh_path, 'rb') as f:
                data = tomli.load(f)
            assert 'metadata' in data
            assert 'players' in data
            assert 'actions' in data
