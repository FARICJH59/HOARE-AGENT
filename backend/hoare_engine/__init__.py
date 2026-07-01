"""hoare_engine package — core Hoare-Agent intelligence layer."""

from hoare_engine.verifier  import HoareVerifier, verify_triple, verifier
from hoare_engine.pda_engine import (
    GrammarRegistry,
    PDAController,
    SchemaGrammar,
    GrammarConstraintError,
    InvalidTransitionError,
    registry,
)
from hoare_engine.agent import HoareAgent, AgentObserver, LoggingObserver

__all__ = [
    "HoareVerifier",
    "verify_triple",
    "verifier",
    "GrammarRegistry",
    "PDAController",
    "SchemaGrammar",
    "GrammarConstraintError",
    "InvalidTransitionError",
    "registry",
    "HoareAgent",
    "AgentObserver",
    "LoggingObserver",
]
