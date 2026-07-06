from selma.memory import terms
from selma.memory.ontology import build_ontology, CLASS_HIERARCHY


def test_every_superclass_exists():
    ont = build_ontology()
    class_uris = {c.uri for c in ont.classes}
    for cls in ont.classes:
        for sup in cls.superclasses:
            assert sup in class_uris, f"{cls.uri} references unknown superclass {sup}"


def test_every_property_domain_range_exists_or_xsd():
    ont = build_ontology()
    class_uris = {c.uri for c in ont.classes}
    for prop in ont.properties:
        for endpoint in (prop.domain, prop.range):
            if endpoint is None:
                continue
            assert endpoint in class_uris or endpoint.startswith(
                "http://www.w3.org/2001/XMLSchema#"), (
                f"{prop.uri} references unknown {endpoint}")


def test_class_hierarchy_matches_ontology():
    ont = build_ontology()
    by_uri = {c.uri: c for c in ont.classes}
    for short, sups in CLASS_HIERARCHY.items():
        cls = by_uri[terms.uri(short)]
        assert [terms.uri(s) for s in sups] == cls.superclasses