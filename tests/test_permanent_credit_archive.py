import tempfile,unittest
from pathlib import Path
from cryptography.fernet import Fernet
from scripts.archive_credit_permanent import merge_rows,update

class PermanentCreditArchiveTests(unittest.TestCase):
 def test_additions_do_not_overwrite_or_expire(self):
  old=[{"date":"2008-09-15","hy_oas":750.0},{"date":"2025-01-03","hy_oas":300.0}]
  fresh={"hy_oas":[("2025-01-03",4.0),("2026-10-22",3.4)],
         "ig_oas":[("2025-01-03",1.0),("2026-10-22",.89)]}
  rows,n=merge_rows(old,fresh)
  self.assertEqual(n,3)
  self.assertEqual(rows[0]["date"],"2008-09-15")
  self.assertEqual(next(r for r in rows if r["date"]=="2025-01-03")["hy_oas"],300.0)
  self.assertEqual(next(r for r in rows if r["date"]=="2026-10-22")["ig_oas"],89.0)
 def test_bad_key_does_not_destroy_archive(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/"archive.fernet";key=Fernet.generate_key()
   loader=lambda _: [("2026-01-%02d"%d,3.2) for d in range(1,29)]*5
   update(path=path,loader=loader,key=key)
   saved=path.read_bytes()
   with self.assertRaises(RuntimeError):update(path=path,loader=loader,key=Fernet.generate_key())
   self.assertEqual(saved,path.read_bytes())
 def test_all_feeds_fail_without_overwrite(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/"archive.fernet";key=Fernet.generate_key()
   loader=lambda _: [("2026-01-%02d"%d,3.2) for d in range(1,29)]*5
   update(path=path,loader=loader,key=key);original=path.read_bytes()
   def failed(_):raise RuntimeError("offline")
   with self.assertRaises(RuntimeError):update(path=path,loader=failed,key=key)
   self.assertEqual(original,path.read_bytes())
if __name__=="__main__":unittest.main()
