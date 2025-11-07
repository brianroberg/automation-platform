"""Tests for deterministic rule engine helpers."""
import pytest

from src.workflows.deterministic_rules import (
    DeterministicRuleEngine,
    LabelDecisions,
    RuleContext,
)


def _make_context(sender: str = "vip@example.com") -> RuleContext:
    decisions = LabelDecisions(
        valid_labels={"VIP"},
        label_validator=lambda _: True,
    )
    return RuleContext(
        sender=sender,
        sender_display=sender,
        subject="Quarterly check-in",
        content="Let's connect soon.",
        snippet="Let's connect",
        to=[],
        cc=[],
        bcc=[],
        existing_labels=set(),
        decisions=decisions,
        my_addresses=set(),
        primary_email="triager@example.com",
    )


def test_sender_group_adds_label() -> None:
    """Group-based sender matching should add labels without exposing addresses in rules."""
    engine = DeterministicRuleEngine(
        rules_data=[
            {
                "name": "vip-group",
                "when": {"sender": {"groups_any": ["vip"]}},
                "actions": {"add": ["VIP"], "exclude": []},
            }
        ],
        valid_labels={"VIP"},
        email_groups={"vip": {"vip@example.com", "vip2@example.com"}},
    )

    context = _make_context()
    terminated = engine.run(context)

    assert terminated is False
    assert context.decisions.pending_additions() == ["VIP"]


def test_sender_group_not_blocks_label() -> None:
    """groups_not_any should prevent rule matches."""
    engine = DeterministicRuleEngine(
        rules_data=[
            {
                "name": "skip-vip",
                "when": {"sender": {"groups_not_any": ["vip"]}},
                "actions": {"add": ["VIP"], "exclude": []},
            }
        ],
        valid_labels={"VIP"},
        email_groups={"vip": {"vip@example.com"}},
    )

    context = _make_context()
    terminated = engine.run(context)

    assert terminated is False
    assert context.decisions.pending_additions() == []


def test_unknown_group_raises_error() -> None:
    """Referencing an undefined group should surface a helpful error."""
    engine = DeterministicRuleEngine(
        rules_data=[
            {
                "name": "bad-group",
                "when": {"sender": {"groups_any": ["vip"]}},
                "actions": {"add": ["VIP"], "exclude": []},
            }
        ],
        valid_labels={"VIP"},
        email_groups={},
    )

    with pytest.raises(ValueError, match="unknown email group"):
        engine.run(_make_context())
