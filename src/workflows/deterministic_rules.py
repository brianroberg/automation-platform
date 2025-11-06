"""Deterministic rule engine for email triage."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import logging
from typing import Any, Callable, Iterable

logger = logging.getLogger(__name__)


class LabelDecision(Enum):
    """Represents the state of a label decision."""

    NONE = "none"
    ADD = "add"
    EXCLUDE = "exclude"


@dataclass
class LabelDecisions:
    """Tracks per-label decisions made during processing."""

    valid_labels: set[str] | None = None
    label_validator: Callable[[str], bool] | None = None
    decisions: dict[str, LabelDecision] = field(default_factory=dict)

    def add_label(self, label: str, source: str) -> None:
        """Mark a label to be applied."""
        self._update_label(label, LabelDecision.ADD, source)

    def exclude_label(self, label: str, source: str) -> None:
        """Mark a label to be excluded."""
        self._update_label(label, LabelDecision.EXCLUDE, source)

    def _update_label(self, label: str, new_state: LabelDecision, source: str) -> None:
        self._validate_label(label)
        previous = self.decisions.get(label, LabelDecision.NONE)
        if previous == new_state:
            logger.debug(
                "Label '%s' already set to %s (source=%s)",
                label,
                new_state.value,
                source,
            )
            return

        if previous != LabelDecision.NONE:
            logger.info(
                "Label '%s' decision overridden from %s to %s by %s",
                label,
                previous.value,
                new_state.value,
                source,
            )
        else:
            logger.debug("Label '%s' set to %s by %s", label, new_state.value, source)

        self.decisions[label] = new_state

    def _validate_label(self, label: str) -> None:
        if self.valid_labels and label in self.valid_labels:
            return
        if self.label_validator and self.label_validator(label):
            return
        raise ValueError(
            f"Deterministic rule referenced unknown label '{label}'. "
            "Ensure this label exists in Gmail before referencing it."
        )

    def pending_additions(self) -> list[str]:
        return [label for label, state in self.decisions.items() if state == LabelDecision.ADD]

    def excluded_labels(self) -> set[str]:
        return {label for label, state in self.decisions.items() if state == LabelDecision.EXCLUDE}

    def is_excluded(self, label: str) -> bool:
        return self.decisions.get(label) == LabelDecision.EXCLUDE

    def final_labels(self) -> list[str]:
        return self.pending_additions()


@dataclass
class RuleContext:
    """Context data available to deterministic rules."""

    sender: str
    sender_display: str
    subject: str
    content: str
    snippet: str
    to: list[str]
    cc: list[str]
    bcc: list[str]
    existing_labels: set[str]
    decisions: LabelDecisions
    my_addresses: set[str]
    primary_email: str

    def __post_init__(self) -> None:
        self.subject_lower = self.subject.lower()
        self.content_lower = self.content.lower()
        self.snippet_lower = self.snippet.lower()
        self.sender_lower = self.sender.lower()
        self.all_recipients = [*self.to, *self.cc, *self.bcc]
        self.primary_domain = self._extract_domain(self.primary_email)

    @staticmethod
    def _extract_domain(email: str) -> str:
        return email.split("@", 1)[-1] if "@" in email else ""


@dataclass
class DeterministicRule:
    """Rule definition parsed from YAML configuration."""

    name: str
    description: str | None
    conditions: dict[str, Any] | None
    add_labels: list[str]
    exclude_labels: list[str]
    terminate: bool = False


class DeterministicRuleEngine:
    """Evaluates deterministic rules before deferring to the LLM."""

    def __init__(
        self,
        rules_data: Iterable[dict[str, Any]],
        valid_labels: set[str],
    ) -> None:
        self.valid_labels = valid_labels
        self.rules = [self._parse_rule(entry) for entry in rules_data]

    def _parse_rule(self, data: dict[str, Any]) -> DeterministicRule:
        name = data.get("name")
        if not name:
            raise ValueError("Deterministic rule is missing required field 'name'.")
        description = data.get("description")
        when = data.get("when")
        actions = data.get("actions", {})
        add = actions.get("add", []) or []
        exclude = actions.get("exclude", []) or []
        terminate = bool(data.get("terminate"))

        return DeterministicRule(
            name=name,
            description=description,
            conditions=when,
            add_labels=list(add),
            exclude_labels=list(exclude),
            terminate=terminate,
        )

    def run(self, context: RuleContext) -> bool:
        """Evaluate rules for the provided context.

        Returns:
            True if processing should terminate, otherwise False.
        """
        for rule in self.rules:
            if self._rule_matches(rule, context):
                self._apply_actions(rule, context)
                if rule.terminate:
                    logger.info("Rule '%s' requested termination for email %s", rule.name, context.subject)
                    return True
        return False

    def _rule_matches(self, rule: DeterministicRule, context: RuleContext) -> bool:
        if not rule.conditions:
            logger.debug("Rule '%s' has no conditions; treating as match", rule.name)
            return True
        result = self._evaluate_condition(rule.conditions, context)
        logger.debug("Rule '%s' conditions evaluated to %s", rule.name, result)
        return result

    def _apply_actions(self, rule: DeterministicRule, context: RuleContext) -> None:
        for label in rule.add_labels:
            context.decisions.add_label(label, source=f"rule:{rule.name}")
        for label in rule.exclude_labels:
            context.decisions.exclude_label(label, source=f"rule:{rule.name}")

    def _evaluate_condition(self, condition: Any, context: RuleContext) -> bool:
        if not condition:
            return True

        if isinstance(condition, dict):
            if "all" in condition:
                return all(self._evaluate_condition(sub, context) for sub in condition["all"])
            if "any" in condition:
                return any(self._evaluate_condition(sub, context) for sub in condition["any"])
            if "not" in condition:
                return not self._evaluate_condition(condition["not"], context)

            if "sender" in condition:
                return self._match_sender(condition["sender"], context)
            if "subject" in condition:
                return self._match_text(condition["subject"], context.subject_lower)
            if "body" in condition or "content" in condition:
                spec = condition.get("body") or condition.get("content")
                return self._match_text(spec, context.content_lower)
            if "snippet" in condition:
                return self._match_text(condition["snippet"], context.snippet_lower)
            if "recipients" in condition:
                return self._match_recipients(condition["recipients"], context)
            if "existing_labels" in condition:
                return self._match_label_sets(condition["existing_labels"], context.existing_labels)
            if "decided_labels" in condition:
                decided = set(context.decisions.pending_additions())
                return self._match_label_sets(condition["decided_labels"], decided)
            if "excluded_labels" in condition:
                excluded = context.decisions.excluded_labels()
                return self._match_label_sets(condition["excluded_labels"], excluded)

        # Unsupported condition format defaults to False
        logger.debug("Unsupported condition encountered: %s", condition)
        return False

    def _match_sender(self, spec: dict[str, Any], context: RuleContext) -> bool:
        value = context.sender_lower
        domain = context.sender_lower.split("@", 1)[-1] if "@" in context.sender_lower else ""

        allowed = spec.get("in")
        if allowed and value not in {entry.lower() for entry in allowed}:
            return False

        blocked = spec.get("not_in")
        if blocked and value in {entry.lower() for entry in blocked}:
            return False

        domain_in = spec.get("domains")
        if domain_in and domain not in {entry.lower() for entry in domain_in}:
            return False

        domain_not = spec.get("domains_not")
        if domain_not and domain in {entry.lower() for entry in domain_not}:
            return False

        contains = spec.get("contains")
        if contains and not self._match_text(contains, value):
            return False

        return True

    def _match_text(self, spec: Any, text_value: str) -> bool:
        if not spec:
            return True
        if isinstance(spec, str):
            return spec.lower() in text_value
        if not isinstance(spec, dict):
            return False

        def normalize(values: Any) -> list[str]:
            if isinstance(values, str):
                return [values]
            return list(values or [])

        def contains_all(values: Iterable[str]) -> bool:
            normalized = [value.lower() for value in values]
            return all(value in text_value for value in normalized)

        def contains_any(values: Iterable[str]) -> bool:
            normalized = [value.lower() for value in values]
            return any(value in text_value for value in normalized)

        def starts_with_any(values: Iterable[str]) -> bool:
            normalized = [value.lower() for value in values]
            return any(text_value.startswith(value) for value in normalized)

        def ends_with_any(values: Iterable[str]) -> bool:
            normalized = [value.lower() for value in values]
            return any(text_value.endswith(value) for value in normalized)

        if "contains_all" in spec and not contains_all(normalize(spec["contains_all"])):
            return False
        if "contains_any" in spec and not contains_any(normalize(spec["contains_any"])):
            return False
        if "not_contains" in spec and contains_any(normalize(spec["not_contains"])):
            return False
        if "starts_with" in spec and not starts_with_any(normalize(spec["starts_with"])):
            return False
        if "ends_with" in spec and not ends_with_any(normalize(spec["ends_with"])):
            return False
        if "equals_any" in spec:
            equals_values = {val.lower() for val in normalize(spec["equals_any"])}
            if text_value not in equals_values:
                return False
        return True

    def _match_recipients(self, spec: dict[str, Any], context: RuleContext) -> bool:
        recipients = context.all_recipients
        total = len(recipients)
        my_addresses = context.my_addresses
        domains = [self._extract_domain(addr) for addr in recipients]

        def any_in(addresses: Iterable[str], pool: Iterable[str]) -> bool:
            items = {item.lower() for item in pool}
            return any(addr.lower() in items for addr in addresses)

        if spec.get("only_me"):
            if not recipients or any(addr not in my_addresses for addr in recipients):
                return False

        if spec.get("not_on_to"):
            if any(addr in my_addresses for addr in context.to):
                return False

        if spec.get("cc_me") and not any(addr in my_addresses for addr in context.cc):
            return False

        if spec.get("to_me") and not any(addr in my_addresses for addr in context.to):
            return False

        if "total_more_than" in spec and not (total > int(spec["total_more_than"])):
            return False

        if "total_less_than" in spec and not (total < int(spec["total_less_than"])):
            return False

        includes_any = spec.get("includes_any") or []
        if includes_any and not any_in(includes_any, recipients):
            return False

        includes_domains = spec.get("includes_domains") or []
        if includes_domains and not any(
            domain in [d.lower() for d in includes_domains] for domain in domains
        ):
            return False

        if spec.get("contains_mailing_list") and not any(
            self._looks_like_mailing_list(addr, spec.get("mailing_list_patterns"))
            for addr in recipients
        ):
            return False

        primary_domain = context.primary_domain
        if spec.get("all_internal"):
            if not primary_domain:
                return False
            if not recipients:
                return False
            if any(domain != primary_domain for domain in domains if domain):
                return False

        if spec.get("any_external"):
            if not primary_domain:
                return False
            if not any(domain and domain != primary_domain for domain in domains):
                return False

        if spec.get("sender_in_recipients"):
            if context.sender_lower not in recipients:
                return False

        return True

    def _match_label_sets(self, spec: dict[str, Any], labels: set[str]) -> bool:
        if not spec:
            return True
        if "has_any" in spec:
            if not any(label in labels for label in spec["has_any"]):
                return False
        if "has_all" in spec:
            if not all(label in labels for label in spec["has_all"]):
                return False
        if "missing_all" in spec:
            if any(label in labels for label in spec["missing_all"]):
                return False
        return True

    @staticmethod
    def _extract_domain(email: str) -> str:
        return email.split("@", 1)[-1] if "@" in email else ""

    def _looks_like_mailing_list(self, address: str, patterns: Any = None) -> bool:
        """Heuristic for spotting mailing list recipients."""
        address = address.lower()
        candidate_patterns = patterns or []
        default_patterns = ["-list@", "@googlegroups.com", "@lists.", "+list@", "newsletter@"]
        for pattern in [*candidate_patterns, *default_patterns]:
            if pattern and pattern.lower() in address:
                return True
        return False
