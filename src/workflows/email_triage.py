"""Email triage workflow - classifies and labels Gmail emails using LLM."""
from __future__ import annotations

import argparse
import logging
import sys
from typing import Any, Iterable

from src.core.config import Config
from src.integrations.gmail_client import GmailClient
from src.integrations.llm_client import LLMClient
from src.utils.logging import setup_logging
from src.workflows.deterministic_rules import (
    DeterministicRuleEngine,
    LabelDecisions,
    RuleContext,
)

logger = logging.getLogger(__name__)


class EmailTriageWorkflow:
    """Workflow that fetches unlabeled inbox emails, classifies them, and applies Gmail labels."""

    def __init__(self) -> None:
        """Initialize workflow dependencies."""
        logger.info("Initializing Email Triage Workflow")

        try:
            self.label_config = Config.load_label_config()
            self.valid_labels = {label["name"] for label in self.label_config["labels"]}
            logger.debug("Loaded %s label definitions", len(self.valid_labels))

            self.gmail_client = GmailClient()
            self.llm_client = LLMClient()
            self.email_groups = Config.load_email_groups()
            rules_data = Config.load_deterministic_rules()
            self.rules_engine = DeterministicRuleEngine(
                rules_data,
                self.valid_labels,
                email_groups=self.email_groups,
            )
            self.primary_email = self.gmail_client.get_primary_address()
            self.user_addresses = self.gmail_client.get_user_addresses()
            if not self.user_addresses and self.primary_email:
                self.user_addresses = {self.primary_email.lower()}

            logger.info("Email Triage Workflow initialized successfully")
        except Exception as exc:
            logger.error("Failed to initialize workflow: %s", exc)
            raise

    def run(
        self,
        max_emails: int = 10,
        dry_run: bool = False,
        verbose: bool = False,
        verbosity: int = 0,
    ) -> dict[str, Any]:
        """Run the workflow, returning summary statistics.

        Args:
            max_emails: Maximum number of inbox emails to process.
            dry_run: When True, skip applying labels (classification only).
            verbose: When True, print per-email results to stdout.
            verbosity: Verbosity level for logging additional details.

        Returns:
            Summary statistics for the run.
        """
        effective_verbosity = max(int(bool(verbose)), verbosity or 0)
        is_verbose = effective_verbosity >= 1

        logger.info(
            "Starting email triage (max_emails=%s, dry_run=%s, verbosity=%s)",
            max_emails,
            dry_run,
            effective_verbosity,
        )

        stats: dict[str, Any] = {
            "processed": 0,
            "succeeded": 0,
            "failed": 0,
            "classifications": {label["name"]: 0 for label in self.label_config["labels"]},
        }

        try:
            if max_emails <= 0:
                logger.info("Max emails set to %s; nothing to do.", max_emails)
                return stats

            emails = self.gmail_client.get_inbox_candidates(
                max_results=max_emails,
                exclude_labels=self.valid_labels,
            )
            if not emails:
                logger.info("No unlabeled inbox emails found")
                return stats

            logger.info("Processing %s unlabeled inbox emails", len(emails))

            for email in emails:
                stats["processed"] += 1

                try:
                    final_labels, label_sources = self._process_email(
                        email,
                        dry_run=dry_run,
                        verbosity=effective_verbosity,
                    )
                    success = True
                except Exception as exc:  # Broad catch ensures one bad email does not stop run
                    logger.error("Failed to process email %s: %s", email.get("id"), exc)
                    stats["failed"] += 1
                    if is_verbose:
                        print(
                            f"[ERROR] Email {email.get('id', 'unknown')} failed: {exc}"
                        )
                    continue

                if success:
                    stats["succeeded"] += 1
                    if final_labels:
                        self._update_stats(stats, final_labels)
                        if dry_run:
                            for label in sorted(final_labels):
                                origin = self._format_label_origin(label, label_sources)
                                print(
                                    f"[DRY RUN][{origin}] Email '{email.get('subject', '')}' "
                                    f"(id={email.get('id')}) would be labeled '{label}'"
                                )
                        elif is_verbose:
                            for label in sorted(final_labels):
                                origin = self._format_label_origin(label, label_sources)
                                print(
                                    f"[APPLIED][{origin}] Email '{email.get('subject', '')}' "
                                    f"(id={email.get('id')}) labeled '{label}'"
                                )
                else:
                    stats["failed"] += 1
                    if is_verbose:
                        print(
                            f"[ERROR] Email {email.get('id', 'unknown')} failed to process."
                        )

            logger.info(
                "Email triage complete: %s/%s succeeded, %s failed",
                stats["succeeded"],
                stats["processed"],
                stats["failed"],
            )

            for label_name, count in stats["classifications"].items():
                if count:
                    logger.info("  %s: %s emails", label_name, count)

            return stats
        except Exception as exc:
            logger.error("Email triage workflow failed: %s", exc)
            raise

    def _process_email(
        self,
        email: dict[str, Any],
        dry_run: bool = False,
        verbosity: int = 0,
    ) -> tuple[set[str], dict[str, str]]:
        """Classify and optionally label a single email.

        Returns:
            Tuple of decided labels and their determining sources.
        """
        email_id = email["id"]
        sender = email.get("sender", "")
        subject = email.get("subject", "")

        logger.debug("Processing email %s: %s", email_id, subject[:50])

        decisions = LabelDecisions(
            valid_labels=self.valid_labels,
            label_validator=self.gmail_client.label_exists,
        )
        existing_labels = set(email.get("existing_labels", []))
        context = RuleContext(
            sender=sender,
            sender_display=email.get("sender_display", sender),
            subject=subject,
            content=email.get("content", ""),
            snippet=email.get("snippet", ""),
            to=email.get("to", []),
            cc=email.get("cc", []),
            bcc=email.get("bcc", []),
            existing_labels=existing_labels,
            decisions=decisions,
            my_addresses=self.user_addresses,
            primary_email=self.primary_email or "",
        )

        terminated = self.rules_engine.run(context)

        llm_response: str | None = None
        if not terminated:
            classification = self.llm_client.classify_email(
                sender=sender,
                subject=subject,
                content=email.get("content", ""),
                label_config=self.label_config,
            )

            logger.info("Email %s classified as: %s", email_id, classification)

            get_last_response = getattr(self.llm_client, "get_last_response", None)
            if callable(get_last_response):
                try:
                    llm_response = get_last_response()
                except Exception as exc:
                    logger.debug("Unable to retrieve last LLM response: %s", exc)

            if llm_response is not None:
                email["llm_response"] = llm_response

            if verbosity >= 2 and llm_response:
                print(
                    f"[LLM RESPONSE] Email '{subject}' (id={email_id}) -> {llm_response}"
                )

            if decisions.is_excluded(classification):
                logger.info(
                    "LLM suggested '%s' for email %s but it was excluded by deterministic rules",
                    classification,
                    email_id,
                )
            else:
                decisions.add_label(classification, source="llm")

        final_labels = decisions.final_labels()
        email["applied_labels"] = sorted(final_labels)

        if verbosity >= 2 and final_labels:
            print(
                f"[RULE] Email '{subject}' (id={email_id}) deterministic labels -> {sorted(final_labels)}"
            )

        self._apply_labels(
            email_id=email_id,
            labels=final_labels,
            existing_labels=existing_labels,
            dry_run=dry_run,
        )

        label_sources = decisions.final_label_sources()
        email["label_sources"] = label_sources

        return final_labels, label_sources

    def _apply_labels(
        self,
        email_id: str,
        labels: Iterable[str],
        existing_labels: set[str],
        dry_run: bool,
    ) -> None:
        """Apply decided labels via Gmail unless running in dry-run mode."""
        if dry_run:
            return

        for label in labels:
            if label in existing_labels:
                logger.debug(
                    "Skipping label '%s' for email %s; already applied",
                    label,
                    email_id,
                )
                continue
            self.gmail_client.apply_label(email_id, label)
            logger.debug("Applied label '%s' to email %s", label, email_id)

    @staticmethod
    def _format_label_origin(label: str, label_sources: dict[str, str]) -> str:
        """Return a short descriptor for how a label decision was made."""
        raw_source = label_sources.get(label, "")
        if raw_source == "llm":
            return "LLM"
        if raw_source.startswith("rule:"):
            return f"RULE {raw_source.split(':', 1)[1]}"
        if raw_source:
            return raw_source.upper()
        return "UNKNOWN"

    def _update_stats(self, stats: dict[str, Any], labels: Iterable[str]) -> None:
        """Increment classification stats for each applied label."""
        for label in labels:
            stats["classifications"][label] = stats["classifications"].get(label, 0) + 1


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the workflow."""
    parser = argparse.ArgumentParser(
        description="Classify unlabeled Gmail inbox messages and apply labels."
    )
    parser.add_argument(
        "-n",
        "--num-messages",
        type=int,
        default=10,
        help="Maximum number of inbox emails to process (default: 10).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Classify emails without applying labels; print the labels that would be applied.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase output detail (-v for per-email status, -vv to include raw LLM responses).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point for running the email triage workflow."""
    args = parse_args(argv)
    setup_logging()

    logger.info("=" * 60)
    logger.info("Email Triage Workflow - Starting")
    logger.info("=" * 60)

    try:
        workflow = EmailTriageWorkflow()
        verbosity = args.verbose or 0
        if args.dry_run:
            verbosity = max(verbosity, 1)

        workflow.run(
            max_emails=args.num_messages,
            dry_run=args.dry_run,
            verbose=verbosity >= 1,
            verbosity=verbosity,
        )
        logger.info("Email triage completed successfully")
        return 0
    except KeyboardInterrupt:
        logger.warning("Workflow interrupted by user")
        return 130
    except Exception as exc:
        logger.error("Email triage workflow failed: %s", exc, exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
