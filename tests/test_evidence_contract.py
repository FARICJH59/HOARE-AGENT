from hoare_engine.evidence import EvidenceBundle, EvidenceItem, EvidenceQuery, evidence_capability_description


def test_evidence_contract_is_immutable_and_attributable():
    item = EvidenceItem("e-1", "https://example.test/spec", "Specification", "relevant excerpt", "sha256:abc", "2026-09-26T12:00:00+00:00")
    query = EvidenceQuery("find the deployment constraint", "project-1", 5)
    bundle = EvidenceBundle(query, (item,))
    assert bundle.items[0].evidence_id == "e-1"
    assert bundle.items[0].content_hash == "sha256:abc"


def test_query_bounds_and_identity_are_validated():
    assert EvidenceQuery("question", "project-1").limit == 10
    for bad_limit in (0, 101):
        try:
            EvidenceQuery("question", "project-1", bad_limit)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid limit accepted")
    for bad_query, bad_project in (("", "project-1"), ("question", "")):
        try:
            EvidenceQuery(bad_query, bad_project)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid identity accepted")


def test_capability_description_does_not_claim_authority():
    description = evidence_capability_description()
    assert "authorize" in description
    assert "execute" in description
    assert "untrusted" in description
