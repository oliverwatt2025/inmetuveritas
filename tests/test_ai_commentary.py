import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from generate_ai_commentary import evidence_bank,validate_selection,add_commentary

class CommentaryTests(unittest.TestCase):
    def setUp(self):
        self.report={"sourceAsOf":"2026-10-22T12:00:00Z","dataQuality":"CURRENT",
                     "keyFindings":[{"id":"credit_contained","headline":"Credit contained",
                                     "explanation":"Spreads are below provisional warning bands."}],
                     "historicalFindings":[{"indicator":"breadth","explanation":"Breadth is at the 90th percentile over 2022–2026."}],
                     "divergences":["The signals do not fully agree."]}
    def test_only_grounded_ids_accepted(self):
        bank=evidence_bank(self.report)
        with self.assertRaises(ValueError):
            validate_selection({"selected_ids":["invented:prediction"]},bank)
        self.assertEqual(validate_selection({"selected_ids":["finding:credit_contained"]},bank),
                         ["finding:credit_contained"])
    def test_ai_cannot_write_prose_or_numbers(self):
        bank=evidence_bank(self.report)
        with self.assertRaises(ValueError):
            validate_selection({"selected_ids":["finding:credit_contained"],
                                "narrative":"Recession probability 99%"},bank)
    def test_fallback_exact_evidence(self):
        r=add_commentary(self.report.copy())
        c=r["editorialCommentary"]
        self.assertEqual(c["mode"],"RULE_BASED")
        self.assertEqual(c["paragraphs"][0],
                         "Credit contained. Spreads are below provisional warning bands.")
    def test_stale_report_suppresses_commentary(self):
        r=add_commentary({**self.report,"dataQuality":"STALE"})
        self.assertEqual(r["editorialCommentary"]["mode"],"UNAVAILABLE")
        self.assertEqual(r["editorialCommentary"]["paragraphs"],[])
if __name__=="__main__": unittest.main()
