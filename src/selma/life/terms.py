"""URI constants and prefixes for the Selma life ontology (spec §2).

`selma.life` reuses the core ontology (`selma.memory.terms`) and mints two
life-specific properties in a separate namespace.
"""
from __future__ import annotations

import secrets

from pyoxigraph import NamedNode

from selma.memory import terms as core
from selma.memory.terms import PREFIXES as CORE_PREFIXES

NS = "https://selma.example/ns/life#"

# Core classes reused by selma.life.
REMINDER = core.uri("Reminder")
EVENT = core.uri("Event")
TASK = core.uri("Task")
PROJECT = core.uri("Project")

# Core properties reused by selma.life.
VALID_FROM = core.PROPS["validFrom"]
VALID_TO = core.PROPS["validTo"]
LABEL = core.PROPS["label"]
TAG = core.PROPS["tag"]
PART_OF = core.PROPS["partOf"]


def uri(name: str) -> str:
    """Return the full life-namespace URI for a short name."""
    return NS + name


PROPS: dict[str, str] = {
    "remindsAbout": uri("remindsAbout"),
    "firedAt": uri("firedAt"),
}

# Prefixes for SPARQL prologues: core prefixes plus life:.
PREFIXES: dict[str, str] = dict(CORE_PREFIXES)
PREFIXES["life"] = NS


def prologue() -> str:
    """Build a SPARQL PREFIX prologue including core and life: prefixes."""
    return "\n".join(f"PREFIX {k}: <{v}>" for k, v in PREFIXES.items())


def instance(kind: str) -> str:
    """Mint a fresh instance URI: ``life:<kind>/<id>``."""
    return f"{NS}{kind}/{secrets.token_hex(6)}"


def default_stated_by() -> NamedNode:
    """Default provenance agent for life assertions."""
    return NamedNode("https://selma.example/ns/core#self")