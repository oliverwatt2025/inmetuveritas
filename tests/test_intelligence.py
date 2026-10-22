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
    def test_dated_changes_and_thresholds(self):
        p={"asOf":"2026-10-22T12:00:00Z","cards":[card("breadth",2.5),card("spy_dd_1m",-1),
           card("hy_oas",330),card("ig_oas",90),card("vix",19)]}
        history=[{"date":"2026-10-21","breadth":0.5,"hy_oas":305,"ig_oas":88,"vix":18}]
        r=build_report(p,NOW,history)
        self.assertEqual({x["indicator"] for x in r["notableChanges"]},{"breadth","hy_oas"})
        self.assertIn("Notable changes",r["changeSummary"])
    def test_stale_snapshot_suppresses_change_commentary(self):
        p={"asOf":"2026-10-18T12:00:00Z","cards":[card("breadth",5),card("vix",35)]}
        r=build_report(p,NOW,[{"date":"2026-10-17","breadth":-5,"vix":10}])
        self.assertEqual(r["notableChanges"],[])
        self.assertIn("stale",r["changeSummary"])
    def test_missing_prior_values_not_invented(self):
        p={"asOf":"2026-10-22T12:00:00Z","cards":[card("breadth",4),card("vix",19)]}
        r=build_report(p,NOW,[{"date":"2026-10-21","hy_oas":300}])
        self.assertEqual(r["notableChanges"],[])

    def test_historical_percentile_requires_real_sample(self):
        from datetime import timedelta
        p={"asOf":"2026-10-22T12:00:00Z","cards":[card("vix",30),card("breadth",2)]}
        start=datetime(2026,6,1,tzinfo=timezone.utc)
        history=[{"date":(start+timedelta(days=i)).date().isoformat(),"vix":10+i/10}
                 for i in range(120)]
        r=build_report(p,NOW,history)
        entry=next(x for x in r["historicalContext"] if x["indicator"]=="vix")
        self.assertEqual(entry["observationCount"],120)
        self.assertEqual(entry["percentile"],100.0)
        self.assertEqual(entry["fromDate"],"2026-06-01")
        self.assertNotIn("five-year percentile",entry["window"])
        self.assertFalse(any(x["indicator"]=="breadth" for x in r["historicalContext"]))
    def test_no_percentile_for_two_recent_points(self):
        p={"asOf":"2026-10-22T12:00:00Z","cards":[card("breadth",2.0)]}
        r=build_report(p,NOW,[{"date":"2026-10-21","breadth":1.0},
                              {"date":"2026-10-22","breadth":2.0}])
        self.assertEqual(r["historicalContext"],[])

if __name__=="__main__":
    unittest.main()
