"""URI constants and prefixes for the Selma agents ontology (spec §2).

`selma.agents` reuses the core ontology (`selma.memory.terms`) and mints two
agents-specific properties in a separate namespace.
"""
from __future__ import annotations

import secrets

from pyoxigraph import NamedNode

from selma.memory import terms as core
from selma.memory.terms import PREFIXES as CORE_PREFIXES

NS = "https://selma.example/ns/agents#"

# Core classes reused by selma.agents.
TASK = core.uri("Task")
PROJECT = core.uri("Project")
AGENT = core.uri("Agent")

# Core properties reused by selma.agents.
LABEL = core.PROPS["label"]
DESCRIPTION = core.PROPS["description"]
HAS_STATUS = core.PROPS["hasStatus"]
OWNED_BY = core.PROPS["ownedBy"]
DUE_BY = core.PROPS["dueBy"]
COMPLETED_AT = core.PROPS["completedAt"]
PART_OF = core.PROPS["partOf"]
DEPENDS_ON = core.PROPS["dependsOn"]

# A stable self agent URI used as the default task owner / runner agent.
AGENT_SELF = "https://selma.example/ns/core#self"


def uri(name: str) -> str:
    """Return the full agents-namespace URI for a short name."""
    return NS + name


PROPS: dict[str, str] = {
    "executionResult": uri("executionResult"),
    "blockReason": uri("blockReason"),
}

# Prefixes for SPARQL prologues: core prefixes plus agents:.
PREFIXES: dict[str, str] = dict(CORE_PREFIXES)
PREFIXES["agents"] = NS


def prologue() -> str:
    """Build a SPARQL PREFIX prologue including core and agents: prefixes."""
    return "\n".join(f"PREFIX {k}: <{v}>" for k, v in PREFIXES.items())


def instance(kind: str) -> str:
    """Mint a fresh instance URI: ``agents:<kind>/<id>``."""
    return f"{NS}{kind}/{secrets.token_hex(6)}"


def default_stated_by() -> NamedNode:
    """Default provenance agent for agents assertions."""
    return NamedNode("https://selma.example/ns/core#self")