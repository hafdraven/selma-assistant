from selma.memory import terms


def test_namespace():
    assert terms.NS == "https://selma.example/ns/core#"


def test_uri_helper():
    assert terms.uri("Entity") == "https://selma.example/ns/core#Entity"


def test_classes_present():
    expected = {"Entity", "Agent", "Event", "Task", "Project",
               "Relationship", "Fact", "Belief", "Reminder"}
    assert set(terms.CLASSES) == expected
    for short, full in terms.CLASSES.items():
        assert full == terms.uri(short)


def test_props_present():
    expected = {
        "recordedAt", "validFrom", "validTo",
        "statedBy", "confidence", "source",
        "label", "description", "tag",
        "relates", "relatedBy", "partOf", "dependsOn", "supersedes",
        "hasStatus", "ownedBy", "dueBy", "completedAt",
    }
    assert set(terms.PROPS) == expected


def test_prefixes_include_external_vocabs():
    assert terms.PREFIXES["foaf"].endswith("/")
    assert terms.PREFIXES["schema"].endswith("/")
    assert terms.PREFIXES["xsd"].endswith("#")


def test_xsd_helpers():
    assert terms.XSD["dateTime"] == "http://www.w3.org/2001/XMLSchema#dateTime"
    assert terms.XSD["decimal"] == "http://www.w3.org/2001/XMLSchema#decimal"