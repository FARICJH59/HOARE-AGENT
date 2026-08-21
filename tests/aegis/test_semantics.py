from hoare_engine.aegis_lowering import lower_aegis
from hoare_engine.aegis_parser import parse_aegis


def lower(source):
    return lower_aegis(parse_aegis(source))


def test_arithmetic_semantics():
    source = """\
agent increment(x)
    let y = x + 1
    return y
end
"""

    ir = lower(source)

    assert ir.assignments[0].expression == "x + 1"


def test_length_has_non_negative_fact():
    source = """\
agent size(data)
    let n = length(data)
    return n
end
"""

    ir = lower(source)

    assert ir.assignments[0].expression == "len(data)"
    assert "n >= 0" in ir.facts


def test_logical_semantics():
    source = """\
agent policy(x)
    fact x >= 0 and x < 10
    return x
end
"""

    ir = lower(source)

    assert ir.facts == ["x >= 0 and x < 10"]
