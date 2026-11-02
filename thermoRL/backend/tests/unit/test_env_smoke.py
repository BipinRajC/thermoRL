import importlib


def test_raps_and_fmpy_importable():
    assert importlib.import_module("raps.engine").Engine
    assert importlib.import_module("fmpy").__version__


def test_thermorl2_importable():
    import thermorl2

    assert thermorl2.__name__ == "thermorl2"
