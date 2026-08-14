import os
import sys
import json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_request import *
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
cases_file = os.environ.get("CASES_FILE")

with open(cases_file, "r", encoding="utf-8") as f:
    cases_data = json.load(f)

@pytest.mark.parametrize(
    "case",
    cases_data,
    ids=[c['CaseID'] for c in cases_data]
)
def test_api(case):
    run_main(case)
