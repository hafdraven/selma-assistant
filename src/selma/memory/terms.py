"""URI constants and prefixes for the Selma core ontology (spec §2).

Single source of truth — no other module hardcodes a Selma IRI.
"""

NS = "https://selma.example/ns/core#"


def uri(name: str) -> str:
    """Return the full core-namespace URI for a short name."""
    return NS + name


CLASSES: dict[str, str] = {
    "Entity": uri("Entity"),
    "Agent": uri("Agent"),
    "Event": uri("Event"),
    "Task": uri("Task"),
    "Project": uri("Project"),
    "Relationship": uri("Relationship"),
    "Fact": uri("Fact"),
    "Belief": uri("Belief"),
    "Reminder": uri("Reminder"),
}

PROPS: dict[str, str] = {
    # Temporal
    "recordedAt": uri("recordedAt"),
    "validFrom": uri("validFrom"),
    "validTo": uri("validTo"),
    # Provenance & trust
    "statedBy": uri("statedBy"),
    "confidence": uri("confidence"),
    "source": uri("source"),
    # Metadata
    "label": uri("label"),
    "description": uri("description"),
    "tag": uri("tag"),
    # Structural
    "relates": uri("relates"),
    "relatedBy": uri("relatedBy"),
    "partOf": uri("partOf"),
    "dependsOn": uri("dependsOn"),
    "supersedes": uri("supersedes"),
    # Task lifecycle
    "hasStatus": uri("hasStatus"),
    "ownedBy": uri("ownedBy"),
    "dueBy": uri("dueBy"),
    "completedAt": uri("completedAt"),
}

XSD: dict[str, str] = {
    "dateTime": "http://www.w3.org/2001/XMLSchema#dateTime",
    "decimal": "http://www.w3.org/2001/XMLSchema#decimal",
    "string": "http://www.w3.org/2001/XMLSchema#string",
    "boolean": "http://www.w3.org/2001/XMLSchema#boolean",
}

PREFIXES: dict[str, str] = {
    "selma": NS,
    "foaf": "http://xmlns.com/foaf/0.1/",
    "schema": "https://schema.org/",
    "ical": "http://www.w3.org/2002/12/cal/ical#",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "owl": "http://www.w3.org/2002/07/owl#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
}