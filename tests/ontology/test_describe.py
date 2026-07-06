from selma.memory.ontology import build_ontology


def test_describe_has_context():
    ont = build_ontology()
    assert "selma" in ont.context
    assert "foaf" in ont.context


def test_every_class_has_description():
    ont = build_ontology()
    for c in ont.classes:
        assert c.description, f"{c.uri} missing description"
        assert c.label, f"{c.uri} missing label"


def test_every_property_has_description():
    ont = build_ontology()
    for p in ont.properties:
        assert p.description, f"{p.uri} missing description"
        assert p.label, f"{p.uri} missing label"


def test_entailment_rules_present():
    ont = build_ontology()
    assert "rdfs:subClassOf" in ont.entailment_rules
    assert "owl:inverseOf" in ont.entailment_rules
    assert "owl:TransitiveProperty" in ont.entailment_rules


def test_to_dict_roundtrips_to_json():
    import json
    ont = build_ontology()
    s = json.dumps(ont.to_dict(), sort_keys=True)
    assert "selma:Entity" in s