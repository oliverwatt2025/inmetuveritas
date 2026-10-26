import tempfile,unittest,json
from pathlib import Path
from cryptography.fernet import Fernet
from scripts.publish_archive_health import summary,publish

class ArchiveHealthTests(unittest.TestCase):
 def test_summary_contains_no_spread_values(self):
  rows=[{"date":"2024-01-02","hy_oas":350.0,"ig_oas":99.0},
        {"date":"2024-01-03","hy_oas":355.0},
        {"date":"2024-01-04","ig_oas":100.0}]
  result=summary(rows,"2026-10-26T19:00:00Z")
  self.assertEqual(result["series"]["hy_oas"]["count"],2)
  self.assertEqual(result["series"]["hy_oas"]["earliest"],"2024-01-02")
  self.assertEqual(result["series"]["ig_oas"]["latest"],"2024-01-04")
  self.assertNotIn("350",json.dumps(result))
 def test_encrypted_source_metadata_only(self):
  with tempfile.TemporaryDirectory() as folder:
   archive=Path(folder)/"data.fernet";out=Path(folder)/"health.json";key=Fernet.generate_key()
   rows=[{"date":"2025-01-01","hy_oas":650.0}]
   archive.write_bytes(Fernet(key).encrypt(json.dumps(rows).encode()))
   publish(archive,out,key=key,now="2026-10-26T19:00:00Z")
   content=out.read_text()
   self.assertNotIn("650",content)
   self.assertEqual(json.loads(content)["series"]["hy_oas"]["count"],1)
if __name__=="__main__":unittest.main()
