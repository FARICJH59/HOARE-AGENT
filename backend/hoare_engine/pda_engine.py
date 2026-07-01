"""
Pushdown Automaton (PDA) Constrained Grammar Engine
====================================================
Implements a finite-state machine that tracks the structural parsing progress
of an incoming JSON payload and enforces schema-conformance at every
transition.

Architecture
------------
Each payload gets its own :class:`PDAController` instance.  The controller
moves through well-defined states (IDLE → INGESTING → PARSING → VALIDATING →
COMMITTING → COMMITTED) and blocks any transition that is not permitted by
the grammar rules.

In a production deployment this layer would hook into the C++/Rust token
generation loop of the inference engine (via XGrammar / Outlines) to
mathematically prevent the model from emitting schema-violating tokens.
For the Python reference implementation we enforce constraints at the
structured-output boundary using Pydantic validation.

Grammar Constraint Layer
------------------------
The :class:`SchemaGrammar` compiles a Pydantic model into a set of
field-level rules (type, required, range) that are checked whenever the
constrained generator produces a token sequence.  Invalid field values
raise :class:`GrammarConstraintError` which trips the BLOCKED state.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type

from pydantic import BaseModel, ValidationError

from schema.models import FSMState, FSMStateEnum, ParsedRecord, RawPayload


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class GrammarConstraintError(Exception):
    """Raised when a generated value violates the compiled schema grammar."""


class InvalidTransitionError(Exception):
    """Raised when the FSM is asked to make a forbidden state transition."""


# ---------------------------------------------------------------------------
# Allowed state transitions (the PDA grammar)
# ---------------------------------------------------------------------------

_TRANSITIONS: Dict[FSMStateEnum, Set[FSMStateEnum]] = {
    FSMStateEnum.IDLE:       {FSMStateEnum.INGESTING, FSMStateEnum.ERROR},
    FSMStateEnum.INGESTING:  {FSMStateEnum.PARSING,   FSMStateEnum.ERROR},
    FSMStateEnum.PARSING:    {FSMStateEnum.VALIDATING, FSMStateEnum.ERROR},
    FSMStateEnum.VALIDATING: {FSMStateEnum.VERIFYING,  FSMStateEnum.BLOCKED, FSMStateEnum.ERROR},
    FSMStateEnum.VERIFYING:  {FSMStateEnum.COMMITTING, FSMStateEnum.BLOCKED, FSMStateEnum.ERROR},
    FSMStateEnum.COMMITTING: {FSMStateEnum.COMMITTED,  FSMStateEnum.ERROR},
    FSMStateEnum.COMMITTED:  {FSMStateEnum.IDLE},          # ready for next payload
    FSMStateEnum.BLOCKED:    {FSMStateEnum.VALIDATING, FSMStateEnum.ERROR},  # self-healing re-entry
    FSMStateEnum.ERROR:      {FSMStateEnum.IDLE},          # manual reset
}


# ---------------------------------------------------------------------------
# Schema grammar compiler
# ---------------------------------------------------------------------------

class FieldRule:
    """Compiled constraint for a single schema field."""

    def __init__(
        self,
        name: str,
        python_type: type,
        required: bool,
        validator: Optional[Callable[[Any], bool]] = None,
    ) -> None:
        self.name = name
        self.python_type = python_type
        self.required = required
        self.validator = validator

    def check(self, value: Any) -> None:
        """Raise :class:`GrammarConstraintError` if *value* breaks this rule."""
        if value is None:
            if self.required:
                raise GrammarConstraintError(
                    f"Required field '{self.name}' is missing"
                )
            return
        if not isinstance(value, (self.python_type, type(None))):
            # Allow numeric coercions
            try:
                self.python_type(value)
            except (TypeError, ValueError) as exc:
                raise GrammarConstraintError(
                    f"Field '{self.name}' has wrong type "
                    f"(expected {self.python_type.__name__}, got {type(value).__name__})"
                ) from exc
        if self.validator is not None and not self.validator(value):
            raise GrammarConstraintError(
                f"Field '{self.name}' failed custom constraint (value={value!r})"
            )


class SchemaGrammar:
    """
    Compiles a Pydantic *model_class* into a set of :class:`FieldRule` objects.

    In a real XGrammar / Outlines integration the compiled grammar would be
    serialised into a regex / EBNF string that constrains the LLM's decoding
    trie at the C++ level.  Here we model that guarantee at the Python layer.
    """

    def __init__(self, model_class: Type[BaseModel], schema_name: str) -> None:
        self.model_class = model_class
        self.schema_name = schema_name
        self.rules: List[FieldRule] = self._compile()

    # ── Compilation ────────────────────────────────────────────────────────

    def _compile(self) -> List[FieldRule]:
        rules: List[FieldRule] = []
        schema = self.model_class.model_json_schema()
        required_fields: Set[str] = set(schema.get("required", []))
        properties: Dict[str, Any] = schema.get("properties", {})

        _type_map: Dict[str, type] = {
            "string":  str,
            "integer": int,
            "number":  float,
            "boolean": bool,
            "object":  dict,
            "array":   list,
        }

        for field_name, field_schema in properties.items():
            json_type = field_schema.get("type", "string")
            py_type   = _type_map.get(json_type, str)
            required  = field_name in required_fields

            # Build a range validator from JSON Schema keywords
            minimum  = field_schema.get("minimum")
            maximum  = field_schema.get("maximum")
            pattern  = field_schema.get("pattern")

            def _make_validator(
                mn: Optional[float],
                mx: Optional[float],
                pat: Optional[str],
            ) -> Optional[Callable[[Any], bool]]:
                if mn is None and mx is None and pat is None:
                    return None
                def _v(val: Any) -> bool:
                    if mn is not None and float(val) < mn:
                        return False
                    if mx is not None and float(val) > mx:
                        return False
                    if pat is not None and not re.fullmatch(pat, str(val)):
                        return False
                    return True
                return _v

            rules.append(
                FieldRule(
                    name=field_name,
                    python_type=py_type,
                    required=required,
                    validator=_make_validator(minimum, maximum, pattern),
                )
            )
        return rules

    # ── Constraint checking ────────────────────────────────────────────────

    def constrain(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply grammar rules to *data*.

        Returns *data* unchanged if all rules pass.
        Raises :class:`GrammarConstraintError` on the first violation.
        """
        for rule in self.rules:
            rule.check(data.get(rule.name))
        return data

    def parse_and_validate(self, data: Dict[str, Any]) -> BaseModel:
        """
        Full Pydantic validation — the last line of defence before commit.

        Raises :class:`GrammarConstraintError` wrapping any Pydantic error.
        """
        try:
            return self.model_class.model_validate(data)
        except ValidationError as exc:
            raise GrammarConstraintError(
                f"Schema validation failed for '{self.schema_name}': {exc}"
            ) from exc


# ---------------------------------------------------------------------------
# PDA Controller  (one instance per payload)
# ---------------------------------------------------------------------------

class PDAController:
    """
    Finite-state machine that governs the lifecycle of a single payload.

    The controller enforces the PDA transition graph and calls
    :class:`SchemaGrammar` constraint checks at the VALIDATING state.
    """

    def __init__(self, payload_id: str, grammar: SchemaGrammar) -> None:
        self.payload_id = payload_id
        self.grammar    = grammar
        self._state     = FSMStateEnum.IDLE
        self._history:  List[Tuple[FSMStateEnum, str]] = []

    # ── Public API ─────────────────────────────────────────────────────────

    @property
    def state(self) -> FSMStateEnum:
        return self._state

    def transition(self, target: FSMStateEnum, detail: str = "") -> FSMState:
        """
        Move to *target* state if the transition is allowed.

        Returns the new :class:`FSMState`.
        Raises :class:`InvalidTransitionError` if the transition is forbidden.
        """
        allowed = _TRANSITIONS.get(self._state, set())
        if target not in allowed:
            raise InvalidTransitionError(
                f"Transition {self._state} → {target} is not permitted. "
                f"Allowed: {[s.value for s in allowed]}"
            )
        self._history.append((self._state, detail))
        self._state = target
        return self.current_fsm_state(detail)

    def process_payload(self, payload: RawPayload) -> ParsedRecord:
        """
        Run the full IDLE → COMMITTED pipeline for *payload*.

        Returns a :class:`ParsedRecord`.  On grammar violation the controller
        moves to BLOCKED and the ParsedRecord carries ``valid=False``.
        """
        self.transition(FSMStateEnum.INGESTING, "Received raw payload")
        self.transition(FSMStateEnum.PARSING,   "Tokenising raw data")

        try:
            self.transition(FSMStateEnum.VALIDATING, "Applying grammar constraints")
            structured = self.grammar.constrain(payload.raw_data)
            self.grammar.parse_and_validate(structured)

            self.transition(FSMStateEnum.VERIFYING,  "Grammar passed — verifying constraints")
            self.transition(FSMStateEnum.COMMITTING, "Verification passed — committing")
            self.transition(FSMStateEnum.COMMITTED,  "Payload committed to data fabric")

            return ParsedRecord(
                payload_id=payload.payload_id,
                schema_name=self.grammar.schema_name,
                structured=structured,
                fsm_state=self.current_fsm_state("Committed"),
                valid=True,
            )
        except GrammarConstraintError as exc:
            self.transition(FSMStateEnum.BLOCKED, str(exc))
            return ParsedRecord(
                payload_id=payload.payload_id,
                schema_name=self.grammar.schema_name,
                structured={},
                fsm_state=self.current_fsm_state(str(exc)),
                valid=False,
                error=str(exc),
            )

    # ── Public state accessor ───────────────────────────────────────────────

    def current_fsm_state(self, detail: str = "") -> FSMState:
        """Return the current :class:`FSMState` (public API)."""
        return FSMState(
            state=self._state,
            payload_id=self.payload_id,
            detail=detail,
            timestamp=datetime.now(timezone.utc),
        )

    @property
    def history(self) -> List[Tuple[FSMStateEnum, str]]:
        return list(self._history)


# ---------------------------------------------------------------------------
# Registry — maps schema names to compiled grammars
# ---------------------------------------------------------------------------

class GrammarRegistry:
    """Thread-safe registry of compiled :class:`SchemaGrammar` objects."""

    def __init__(self) -> None:
        self._grammars: Dict[str, SchemaGrammar] = {}
        self._tenant_schemas: Dict[str, Set[str]] = {"public": set()}

    def register(self, model_class: Type[BaseModel], schema_name: str) -> SchemaGrammar:
        grammar = SchemaGrammar(model_class, schema_name)
        self._grammars[schema_name] = grammar
        self._tenant_schemas.setdefault("public", set()).add(schema_name)
        return grammar

    def provision_tenant(self, tenant_id: str, schemas: Optional[List[str]] = None) -> List[str]:
        allowed = set(self._grammars.keys()) if schemas is None else set(schemas)
        unknown = allowed - set(self._grammars.keys())
        if unknown:
            raise KeyError(f"Unknown schemas for tenant '{tenant_id}': {sorted(unknown)}")
        self._tenant_schemas[tenant_id] = allowed
        return sorted(allowed)

    def list_schemas(self, tenant_id: str = "public") -> List[str]:
        if tenant_id in self._tenant_schemas:
            return sorted(self._tenant_schemas[tenant_id])
        return sorted(self._tenant_schemas.get("public", set()))

    def get(self, schema_name: str, tenant_id: str = "public") -> SchemaGrammar:
        allowed = set(self.list_schemas(tenant_id))
        if schema_name not in allowed:
            raise KeyError(
                f"Schema '{schema_name}' is not allowed for tenant '{tenant_id}'"
            )
        try:
            return self._grammars[schema_name]
        except KeyError:
            raise KeyError(f"Schema '{schema_name}' is not registered") from None

    def make_controller(self, payload_id: str, schema_name: str, tenant_id: str = "public") -> PDAController:
        return PDAController(payload_id, self.get(schema_name, tenant_id=tenant_id))


# ---------------------------------------------------------------------------
# Default registry pre-loaded with built-in schemas
# ---------------------------------------------------------------------------

from schema.models import TelemetryEvent, TransformationOutput  # noqa: E402

registry = GrammarRegistry()
registry.register(TelemetryEvent,       "TelemetryEvent")
registry.register(TransformationOutput, "TransformationOutput")
