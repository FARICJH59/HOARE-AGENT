from hoare_engine.aegis_parser import AegisSyntaxError, parse_aegis


def test_parse_basic_agent():
    source = """\
agent transform(data)
    let n = length(data)
    fact n >= 0
    return data
end
"""

    program = parse_aegis(source)

    assert program.name == "transform"
    assert program.parameters == ["data"]
    assert len(program.assignments) == 1
    assert program.assignments[0].target == "n"
    assert program.assignments[0].expression == "length(data)"
    assert len(program.facts) == 1
    assert program.facts[0].expression == "n >= 0"
    assert len(program.returns) == 1


def test_parse_boolean_expression():
    source = """\
agent policy(x)
    fact x >= 0 and x < 100
    return x
end
"""

    program = parse_aegis(source)

    assert program.facts[0].expression == "x >= 0 and x < 100"


def test_reject_missing_end():
    source = """\
agent broken(x)
    let y = x + 1
"""

    try:
        parse_aegis(source)
    except AegisSyntaxError:
        return

    raise AssertionError("Expected AegisSyntaxError")
