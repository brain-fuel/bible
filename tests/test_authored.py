# tests/test_authored.py
from tools.relations.authored import load_authored, validate_authored_line
import pytest

def test_validate_authored_line_ok():
    d = {"src":"G0026","dst":"G5360","rel":"synonym","directed":False,
         "provenance":{"source":"hand","method":"authored"},"rank":65535,"note":"love→brotherly-love"}
    e = validate_authored_line(d, valid_keys={"G0026","G5360"})
    assert e.method == "authored" and e.rel == "synonym"

def test_validate_authored_line_bad_endpoint():
    d = {"src":"G9999","dst":"G5360","rel":"synonym","directed":False,
         "provenance":{"source":"hand","method":"authored"},"rank":65535,"note":None}
    with pytest.raises(ValueError):
        validate_authored_line(d, valid_keys={"G5360"})
