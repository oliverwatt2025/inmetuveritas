import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch
from scripts import backfill_credit_20y as mod

class CreditArchiveTests(unittest.TestCase):
    def test_dated_conversion_and_missing_days(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"credit.ndjson"
            def loader(sid):
                return [(f"{year}-{month:02d}-{day:02d}", 3.0 if sid=="BAMLH0A0HYM2" else 1.0)
                        for year in range(2007,2027) for month in range(1,13) for day in (5,12,19)]
            mod.build(today=date(2026,10,26),loader=loader,output=p)
            rows=[json.loads(line) for line in p.read_text().splitlines()]
            self.assertTrue(rows)
            self.assertEqual(rows[0]["date"],"2007-01-05")
            self.assertEqual(rows[0]["hy_oas"],300.0)
            self.assertEqual(rows[0]["ig_oas"],100.0)
            self.assertEqual(len({r["date"] for r in rows}),len(rows))

    def test_failed_feeds_leave_existing_file_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"credit.ndjson"
            original='{"date":"2025-01-02","hy_oas":330.0}\n'
            p.write_text(original)
            def broken(_):raise RuntimeError("offline")
            with self.assertRaises(RuntimeError):
                mod.build(today=date(2026,10,26),loader=broken,output=p)
            self.assertEqual(p.read_text(),original)

if __name__=="__main__":
    unittest.main()
