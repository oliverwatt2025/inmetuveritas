import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from generate_intelligence import build_report

NOW = datetime(2026, 10, 22, 14, 0, tzinfo=timezone.utc)
def card(key,value,status="GOOD"):
    return {"id":key,"value":value,"status":status,"updatedAt":"2026-10-22T12:00:00Z"}
class TestIntelligence(unittest.TestCase):
    def test_mixed_evidence(self):
        p={"asOf":"2026-10-22T12:00:00Z","cards":[card("breadth",-2),card("spy_dd_1m",-1),
           card("hy_oas",320),card("ig_oas",90),card("vix",17)]}
        r=build_report(p,NOW)
        self.assertEqual(r["regime"],"MIXED SIGNALS")
        self.assertEqual(r["dataQuality"],"CURRENT")
    def test_staleness_overrides_reading(self):
        p={"asOf":"2026-10-18T12:00:00Z","cards":[card("breadth",2),card("hy_oas",320),card("ig_oas",90)]}
        self.assertEqual(build_report(p,NOW)["regime"],"INSUFFICIENT CURRENT EVIDENCE")
    def test_no_invented_readings(self):
        p={"asOf":"2026-10-22T12:00:00Z","cards":[card("vix",None),card("hy_oas",None)]}
        self.assertEqual(build_report(p,NOW)["keyFindings"],[])
    def test_delayed_raw_card_not_counted(self):
        p={"asOf":"2026-10-22T12:00:00Z","cards":[card("vix",50,"DELAYED"),card("hy_oas",330),card("ig_oas",90)]}
        ids=[x["id"] for x in build_report(p,NOW)["keyFindings"]]
        self.assertNotIn("volatility_elevated",ids)
if __name__=="__main__":
    unittest.main()
