"""Deterministic plumbing tests; stub scores do NOT evaluate the real model."""
import os
import unittest
from unittest.mock import patch
from test_retrieval_relevance import card
from app.retriever import retrieve_candidate_evidence


class SemanticRetrievalTests(unittest.TestCase):
    def test_synonym_without_shared_words(self) -> None:
        with patch.dict(os.environ, {"SELFMAP_RETRIEVAL_MODE": "hybrid"}), \
             patch("app.retriever.load_evidence_cards_raw", return_value=[
                 card("talk", "Vortrag verständlich"), card("plants", "Blumen gegossen")]), \
             patch("app.retriever.semantic_scores", return_value=[0.8, 0.1]):
            found = retrieve_candidate_evidence("Präsentation erklären", None, "demo_user", "demo")
        self.assertEqual([c.evidence_id for c in found], ["talk"])

    def test_filters_run_before_embedding(self) -> None:
        with patch.dict(os.environ, {"SELFMAP_RETRIEVAL_MODE": "hybrid"}), \
             patch("app.retriever.load_evidence_cards_raw", return_value=[
                 card("hidden", "secret", privacy_level="hidden"),
                 card("other", "other secret", profile_id="other"),
                 card("sensitive", "sensitive secret", privacy_level="sensitive"),
                 card("disabled", "disabled secret", send_to_gemini_allowed=False),
                 card("ok", "presentation")]), \
             patch("app.retriever.semantic_scores", return_value=[0.9]) as encoder:
            retrieve_candidate_evidence("presentation", None, "demo_user", "demo")
        self.assertEqual(encoder.call_args.args[1], ["presentation"])

    def test_low_similarity_abstains_even_with_word_overlap(self) -> None:
        with patch.dict(os.environ, {"SELFMAP_RETRIEVAL_MODE": "hybrid"}), \
             patch("app.retriever.load_evidence_cards_raw", return_value=[card("a", "presentation")]), \
             patch("app.retriever.semantic_scores", return_value=[0.1]):
            self.assertEqual(retrieve_candidate_evidence(
                "presentation", None, "demo_user", "demo"), [])

    def test_unavailable_model_falls_back_without_logging_private_text(self) -> None:
        with patch.dict(os.environ, {"SELFMAP_RETRIEVAL_MODE": "hybrid"}), \
             patch("app.retriever.load_evidence_cards_raw", return_value=[
                 card("ok", "presentation"), card("bad", "gardening")]), \
             patch("app.retriever.semantic_scores", side_effect=RuntimeError("PRIVATE TEXT")), \
             self.assertLogs("app.retriever", level="WARNING") as logs:
            found = retrieve_candidate_evidence("presentation", None, "demo_user", "demo")
        self.assertEqual([c.evidence_id for c in found], ["ok"])
        self.assertNotIn("PRIVATE TEXT", " ".join(logs.output))

    def test_invalid_configuration_falls_back(self) -> None:
        for threshold in ["nan", "-1", "2", "invalid"]:
            with self.subTest(threshold=threshold), \
                 patch.dict(os.environ, {"SELFMAP_RETRIEVAL_MODE": "hybrid",
                                         "SELFMAP_SEMANTIC_THRESHOLD": threshold}), \
                 patch("app.retriever.load_evidence_cards_raw", return_value=[card("ok", "presentation")]), \
                 patch("app.retriever.semantic_scores") as encoder, \
                 self.assertLogs("app.retriever", level="WARNING"):
                result = retrieve_candidate_evidence("presentation", None, "demo_user", "demo")
                self.assertEqual([c.evidence_id for c in result], ["ok"])
                encoder.assert_not_called()

    def test_invalid_scores_fall_back(self) -> None:
        for scores in [[], [float("nan")], [2.0]]:
            with self.subTest(scores=scores), \
                 patch.dict(os.environ, {"SELFMAP_RETRIEVAL_MODE": "hybrid"}), \
                 patch("app.retriever.load_evidence_cards_raw", return_value=[card("ok", "presentation")]), \
                 patch("app.retriever.semantic_scores", return_value=scores), \
                 self.assertLogs("app.retriever", level="WARNING"):
                result = retrieve_candidate_evidence("presentation", None, "demo_user", "demo")
                self.assertEqual([c.evidence_id for c in result], ["ok"])
