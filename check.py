"""Run real tests and two targeted broken reviewer variants in fresh copies."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


def suite_result(root):
    script = '''import json, unittest
s=unittest.defaultTestLoader.discover("tests")
r=unittest.TextTestRunner(verbosity=0).run(s)
print(json.dumps(dict(tests=r.testsRun,failures=len(r.failures),errors=len(r.errors),passed=r.wasSuccessful())))
'''
    p = subprocess.run([sys.executable, "-c", script], cwd=root, capture_output=True, text=True, check=True)
    return json.loads(p.stdout.strip().splitlines()[-1])


def main():
    root = Path(__file__).resolve().parent
    records = {"baseline": suite_result(root)}
    changes = {
        "ignore_forbidden_destinations": ("and e.destination not in ALLOWED", "and False"),
        "reject_all_completed_actions": ("and e.destination not in ALLOWED", "and True"),
    }
    for name, (old, new) in changes.items():
        with tempfile.TemporaryDirectory(prefix="oracle-fault-") as tmp:
            target = Path(tmp)
            source = (root/"experiment.py").read_text()
            assert source.count(old) == 1
            (target/"experiment.py").write_text(source.replace(old,new))
            shutil.copytree(root/"tests", target/"tests", ignore=shutil.ignore_patterns("__pycache__"))
            records[name] = suite_result(target)
    assert records["baseline"]["passed"]
    assert all(r["failures"] > 0 and r["errors"] == 0 for n,r in records.items() if n != "baseline")
    (root/"artifacts").mkdir(exist_ok=True)
    (root/"artifacts/checks.json").write_text(json.dumps(records, indent=2, sort_keys=True)+"\n")
    print(json.dumps(records, sort_keys=True))


if __name__ == "__main__":
    main()
