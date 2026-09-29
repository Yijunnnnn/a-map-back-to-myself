"""Offline retrieval regressions. Run: python -m unittest discover -s tests -v."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

from app.retriever import retrieve_candidate_evidence
from app.schemas import EvidenceCard


def card(evidence_id: str, event: str, **overrides: Any) -> EvidenceCard:
    values = dict(evidence_id=evidence_id, profile_id="demo_user",
                  source_type="manual_input", source_id=evidence_id, date="",
                  event=event, skills=[], emotions=[], supports=[], contradicts=[],
                  citation="", privacy_level="private")
    values.update(overrides)
    return EvidenceCard(**values)


class RetrievalTests(unittest.TestCase):
    def search(self, cards: list[EvidenceCard], query: str, **kwargs: Any) -> list[str]:
        with patch("app.retriever.load_evidence_cards_raw", return_value=cards):
            results = retrieve_candidate_evidence(
                query, None, kwargs.pop("profile_id", "demo_user"),
                kwargs.pop("mode", "demo"), **kwargs)
        return [item.evidence_id for item in results]

    def test_unrelated_evidence_is_absent(self) -> None:
        self.assertEqual(self.search([card("weather", "Sunny weather yesterday")],
                                     "Quantum mechanics"), [])

    def test_shared_pronouns_are_not_evidence(self) -> None:
        self.assertEqual(self.search([card("plants", "I watered my plants")],
                                     "I cannot explain my presentation"), [])

    def test_positive_unrelated_evidence_does_not_outrank_relevant(self) -> None:
        cards = [card("unrelated", "gardening growth", contradicts=["I cannot cook"]),
                 card("relevant", "presentation client feedback")]
        self.assertEqual(self.search(cards, "I fail at presentation"), ["relevant"])

    def test_negative_relevant_evidence_is_retained(self) -> None:
        cards = [card("negative", "presentation confused the audience"),
                 card("positive", "presentation impressed the audience")]
        self.assertEqual(self.search(cards, "presentation"), ["negative", "positive"])

    def test_empty_and_nonpositive_limit(self) -> None:
        self.assertEqual(self.search([], "presentation"), [])
        for query in ("", "I am", "Ich bin"):
            self.assertEqual(self.search([card("a", "presentation")], query), [])
        for limit in (0, -1):
            self.assertEqual(self.search([card("a", "presentation")],
                                         "presentation", top_k=limit), [])

    def test_privacy_and_profile_filters(self) -> None:
        cards = [card("hidden", "presentation", privacy_level="hidden"),
                 card("sensitive", "presentation", privacy_level="sensitive"),
                 card("disabled", "presentation", send_to_gemini_allowed=False),
                 card("other", "presentation", profile_id="other"),
                 card("ok", "presentation")]
        self.assertEqual(self.search(cards, "presentation"), ["ok"])
        self.assertEqual(self.search(cards, "presentation", allow_sensitive=True),
                         ["sensitive", "ok"])
        self.assertEqual(self.search(cards, "presentation", mode="user", profile_id="other"),
                         ["other"])

    def test_word_boundaries_case_and_punctuation(self) -> None:
        cards = [card("wrong", "party"), card("right", "ART!")]
        self.assertEqual(self.search(cards, "Art?"), ["right"])

    def test_german_and_chinese(self) -> None:
        self.assertEqual(self.search([card("plants", "Ich gieße meine Pflanzen"),
                                      card("talk", "Meine Präsentation war verständlich")],
                                     "Ich kann meine Präsentation nicht erklären"), ["talk"])
        self.assertEqual(self.search([card("plants", "今天浇花"),
                                      card("talk", "演讲得到好评")],
                                     "我的演讲总是失败"), ["talk"])

    def test_more_topic_matches_rank_first(self) -> None:
        self.assertEqual(self.search([card("one", "presentation"),
                                      card("two", "client presentation")],
                                     "client presentation", top_k=1), ["two"])

    def test_real_file_loader_and_removal_countercheck(self) -> None:
        previous = os.getcwd()
        with tempfile.TemporaryDirectory() as directory:
            try:
                os.chdir(directory)
                Path("derived").mkdir()
                path = Path("derived/evidence_cards.json")
                relevant = card("talk", "presentation was clear")
                irrelevant = card("plants", "I watered my plants")
                path.write_text(json.dumps([relevant.model_dump(), irrelevant.model_dump()]))
                result = retrieve_candidate_evidence("my presentation", None, "demo_user", "demo")
                self.assertEqual([item.evidence_id for item in result], ["talk"])
                path.write_text(json.dumps([irrelevant.model_dump()]))
                self.assertEqual(retrieve_candidate_evidence(
                    "my presentation", None, "demo_user", "demo"), [])
            finally:
                os.chdir(previous)


if __name__ == "__main__":
    unittest.main()
