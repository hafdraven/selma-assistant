"""Ontology self-description and entailment metadata (spec §2, §4)."""
from __future__ import annotations

from dataclasses import dataclass, field

from .terms import NS, PREFIXES, XSD, uri

# Class hierarchy: short name -> list of direct superclass short names.
CLASS_HIERARCHY: dict[str, list[str]] = {
    "Entity": [],
    "Agent": ["Entity"],
    "Event": ["Entity"],
    "Task": ["Entity"],
    "Project": ["Entity"],
    "Relationship": ["Entity"],
    "Fact": ["Entity"],
    "Belief": ["Entity"],
    "Reminder": ["Event"],
}

# owl:inverseOf pairs (short names).
INVERSE_PROPS: set[tuple[str, str]] = {
    ("relates", "relatedBy"),
}

# owl:TransitiveProperty short names.
TRANSITIVE_PROPS: set[str] = {"partOf", "dependsOn"}


@dataclass
class OntologyClass:
    uri: str
    label: str
    description: str
    superclasses: list[str]
    properties: list[str]


@dataclass
class OntologyProperty:
    uri: str
    label: str
    description: str
    domain: str | None
    range: str | None


@dataclass
class OntologyDescription:
    context: dict[str, str]
    classes: list[OntologyClass]
    properties: list[OntologyProperty]
    entailment_rules: list[str]
    example_queries: list[str]

    def to_dict(self) -> dict:
        return {
            "context": self.context,
            "classes": [c.__dict__ for c in self.classes],
            "properties": [p.__dict__ for p in self.properties],
            "entailment_rules": self.entailment_rules,
            "example_queries": self.example_queries,
        }


_CLASS_DESCRIPTIONS = {
    "Entity": "Top class for anything named and referenceable.",
    "Agent": "An Entity that can act on Tasks or assert Facts.",
    "Event": "Something that happened or will happen, anchored in time.",
    "Task": "A unit of work with status, owner, optional deadline.",
    "Project": "A container of Tasks and resources tracking goals and outcomes.",
    "Relationship": "A reified relationship between two Entities with type and time window.",
    "Fact": "A statement the assistant believes is true, with provenance and confidence.",
    "Belief": "A statement an Agent holds that may be uncertain or evolving.",
    "Reminder": "An Event that fires at a time and produces a notification.",
}

# Properties that apply to each class (short names), for /describe output.
_CLASS_PROPS = {
    "Entity": ["label", "description", "tag"],
    "Agent": ["label", "description"],
    "Event": ["validFrom", "validTo", "statedBy"],
    "Task": ["hasStatus", "ownedBy", "dueBy", "completedAt", "partOf"],
    "Project": ["label", "description", "partOf"],
    "Relationship": ["validFrom", "validTo", "statedBy", "confidence"],
    "Fact": ["recordedAt", "validFrom", "validTo", "statedBy", "confidence", "source", "supersedes"],
    "Belief": ["recordedAt", "validFrom", "validTo", "statedBy", "confidence", "source"],
    "Reminder": ["validFrom", "validTo", "statedBy"],
}

_PROP_DESCRIPTIONS = {
    "recordedAt": "When this statement was stored.",
    "validFrom": "Start of the time window in which the statement holds.",
    "validTo": "End of the time window in which the statement holds.",
    "statedBy": "The Agent or source that asserted this statement (required).",
    "confidence": "Decimal in [0, 1] expressing trust in this statement.",
    "source": "URI or literal identifying the channel that produced this statement.",
    "label": "Human-readable label for /describe rendering.",
    "description": "Natural-language description for /describe rendering.",
    "tag": "Free-text tag.",
    "relates": "Subject relates to object (inverse of relatedBy).",
    "relatedBy": "Object is related by subject (inverse of relates).",
    "partOf": "Subject is a part of object (transitive).",
    "dependsOn": "Subject depends on object (transitive).",
    "supersedes": "Subject Fact supersedes the object Fact.",
    "hasStatus": "Task status: open, in_progress, done, or blocked.",
    "ownedBy": "The Agent that owns a Task.",
    "dueBy": "When a Task is due (xsd:dateTime).",
    "completedAt": "When a Task was completed (xsd:dateTime).",
}

_PROP_DOMAIN_RANGE = {
    "recordedAt": (uri("Fact"), XSD["dateTime"]),
    "validFrom": (uri("Entity"), XSD["dateTime"]),
    "validTo": (uri("Entity"), XSD["dateTime"]),
    "statedBy": (uri("Entity"), uri("Agent")),
    "confidence": (uri("Entity"), XSD["decimal"]),
    "source": (uri("Fact"), XSD["string"]),
    "label": (uri("Entity"), XSD["string"]),
    "description": (uri("Entity"), XSD["string"]),
    "tag": (uri("Entity"), XSD["string"]),
    "relates": (uri("Relationship"), uri("Entity")),
    "relatedBy": (uri("Entity"), uri("Relationship")),
    "partOf": (uri("Entity"), uri("Entity")),
    "dependsOn": (uri("Entity"), uri("Entity")),
    "supersedes": (uri("Fact"), uri("Fact")),
    "hasStatus": (uri("Task"), XSD["string"]),
    "ownedBy": (uri("Task"), uri("Agent")),
    "dueBy": (uri("Task"), XSD["dateTime"]),
    "completedAt": (uri("Task"), XSD["dateTime"]),
}


_EXAMPLE_QUERIES = [
    "SELECT ?e WHERE { ?e a selma:Entity . } LIMIT 10",
    "SELECT ?s ?o WHERE { ?s selma:partOf+ ?o }",
    "SELECT ?fact ?val WHERE { ?fact a selma:Fact ; selma:statedBy <selma:agent:self> . ?fact selma:confidence ?val . FILTER(?val > 0.5) }",
]


def build_ontology() -> OntologyDescription:
    classes = [
        OntologyClass(
            uri=uri(short),
            label=short,
            description=_CLASS_DESCRIPTIONS[short],
            superclasses=[uri(s) for s in CLASS_HIERARCHY[short]],
            properties=[uri(p) for p in _CLASS_PROPS[short]],
        )
        for short in CLASS_HIERARCHY
    ]
    from .terms import PROPS
    properties = [
        OntologyProperty(
            uri=PROPS[short],
            label=short,
            description=_PROP_DESCRIPTIONS[short],
            domain=_PROP_DOMAIN_RANGE[short][0],
            range=_PROP_DOMAIN_RANGE[short][1],
        )
        for short in PROPS
    ]
    return OntologyDescription(
        context=dict(PREFIXES),
        classes=classes,
        properties=properties,
        entailment_rules=["rdfs:subClassOf", "owl:inverseOf", "owl:TransitiveProperty"],
        example_queries=list(_EXAMPLE_QUERIES),
    )


def describe() -> OntologyDescription:
    """Return the ontology self-description (spec §4 /describe payload)."""
    return build_ontology()