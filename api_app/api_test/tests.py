import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_request import *
import pytest

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(BASE_DIR, "cases.json"), "r", encoding="utf-8") as f:
    cases_data = json.load(f)

@pytest.mark.parametrize(
    "case",
    cases_data,
    ids=[c['CaseID'] for c in cases_data]
)
def test_api(case):
    run_and_assert(case)
