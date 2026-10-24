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
    def test_cloudflare_model_selection_is_strictly_validated(self):
        from unittest.mock import patch
        import io
        from generate_ai_commentary import choose_with_ai
        class Response(io.BytesIO):
            def __enter__(self): return self
            def __exit__(self,*args): self.close()
        bank=evidence_bank(self.report)
        good=b'{"success":true,"result":{"response":"{\\\"selected_ids\\\":[\\\"historical:breadth\\\"]}"}}'
        with patch("generate_ai_commentary.urllib.request.urlopen",return_value=Response(good)) as mocked:
            ids=choose_with_ai(self.report,bank,"test-token","test-account")
            self.assertEqual(ids,["historical:breadth"])
            request=mocked.call_args.args[0]
            self.assertIn("api.cloudflare.com",request.full_url)
            self.assertIn("@cf/meta/llama-3.1-8b-instruct",request.full_url)
        bad=b'{"success":true,"result":{"response":"{\\\"selected_ids\\\":[\\\"invented\\\"]}"}}'
        with patch("generate_ai_commentary.urllib.request.urlopen",return_value=Response(bad)):
            with self.assertRaises(ValueError):
                choose_with_ai(self.report,bank,"test-token","test-account")
if __name__=="__main__": unittest.main()
