from tools.validate_morph import reconcile_form


def test_reconcile_form_present():
    assert reconcile_form("ἀρχῇ", "ἐν ἀρχῇ ἦν") is True


def test_reconcile_form_absent():
    assert reconcile_form("xyz", "ἐν ἀρχῇ ἦν") is False
