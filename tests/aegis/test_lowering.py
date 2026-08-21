from hoare_engine.aegis_lowering import lower_aegis
from hoare_engine.aegis_parser import parse_aegis


def test_aegis_lowers_to_verification_ir():
    source = """\
agent transform(data)
    let n = length(data)
    fact n >= 0
    return data
end
"""

    ast = parse_aegis(source)
    ir = lower_aegis(ast)

    assert ir.source_language == "aegis"

    assert len(ir.assignments) == 1
    assert ir.assignments[0].target == "n"
    assert ir.assignments[0].expression == "len(data)"

    assert ir.facts == ["n >= 0"]

    assert len(ir.returns) == 1
    assert ir.returns[0].expression == "data"


def test_boolean_normalization():
    source = """\
agent policy(x)
    fact TRUE and not FALSE
    return x
end
"""

    ast = parse_aegis(source)
    ir = lower_aegis(ast)

    assert ir.facts == ["True and not False"]
