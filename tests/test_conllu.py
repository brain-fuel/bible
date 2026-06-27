# tests/test_conllu.py
from tools.conllu import Token, write_sentence, parse_sentence, format_misc

def test_format_misc_orders_and_joins():
    assert format_misc("G1722", "en", {"en": "in"}, None) == "Strong=G1722|Translit=en|gloss_en=in"

def test_format_misc_empty_is_underscore():
    assert format_misc("", "_", {}, None) == "_"

def test_roundtrip_sentence():
    toks = [Token("1", "ἐν", "ἐν", "ADP", "PREP", "_", misc="Strong=G1722")]
    block = write_sentence("JOH.1.1", toks)
    assert block.startswith("# ref = JOH.1.1\n")
    ref, parsed = parse_sentence(block)
    assert ref == "JOH.1.1"
    assert parsed[0].form == "ἐν"
    assert parsed[0].misc == "Strong=G1722"
