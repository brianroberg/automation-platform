"""Email triage workflow - classifies and labels Gmail emails using LLM."""
from __future__ import annotations

import argparse
import logging
import sys
from typing import Any

from src.core.config import Config
from src.integrations.gmail_client import GmailClient
from src.integrations.llm_client import LLMClient
from src.utils.logging import setup_logging

logger = logging.getLogger(__name__)


class EmailTriageWorkflow:
    """Workflow that fetches unread emails, classifies them, and applies Gmail labels."""

    def __init__(self) -> None:
        """Initialize workflow dependencies."""
        logger.info("Initializing Email Triage Workflow")

        try:
            self.label_config = Config.load_label_config()
            logger.debug("Loaded %s label definitions", len(self.label_config["labels"]))

            self.gmail_client = GmailClient()
            self.llm_client = LLMClient()

            logger.info("Email Triage Workflow initialized successfully")
        except Exception as exc:
            logger.error("Failed to initialize workflow: %s", exc)
            raise

    def run(self, max_emails: int = 10, dry_run: bool = False, verbose: bool = False) -> dict[str, Any]:
        """Run the workflow, returning summary statistics.

        Args:
            max_emails: Maximum number of unread emails to process.
            dry_run: When True, skip applying labels (classification only).
            verbose: When True, print per-email results to stdout.

        Returns:
            Summary statistics for the run.
        """
        logger.info(
            "Starting email triage (max_emails=%s, dry_run=%s, verbose=%s)",
            max_emails,
            dry_run,
            verbose,
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

            emails = self.gmail_client.get_unread_emails(max_results=max_emails)
            if not emails:
                logger.info("No unread emails found")
                return stats

            logger.info("Processing %s unread emails", len(emails))

            for email in emails:
                stats["processed"] += 1

                try:
                    success = self._process_email(email, dry_run=dry_run)
                except Exception as exc:  # Broad catch ensures one bad email does not stop run
                    logger.error("Failed to process email %s: %s", email.get("id"), exc)
                    stats["failed"] += 1
                    if verbose:
                        print(
                            f"[ERROR] Email {email.get('id', 'unknown')} failed: {exc}"
                        )
                    continue

                if success:
                    stats["succeeded"] += 1
                    classification = email.get("classification")
                    if classification:
                        stats["classifications"][classification] = (
                            stats["classifications"].get(classification, 0) + 1
                        )
                        if dry_run:
                            print(
                                f"[DRY RUN] Email '{email.get('subject', '')}' "
                                f"(id={email.get('id')}) would be labeled '{classification}'"
                            )
                        elif verbose:
                            print(
                                f"[APPLIED] Email '{email.get('subject', '')}' "
                                f"(id={email.get('id')}) labeled '{classification}'"
                            )
                else:
                    stats["failed"] += 1
                    if verbose:
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

    def _process_email(self, email: dict[str, Any], dry_run: bool = False) -> bool:
        """Classify and optionally label a single email."""
        email_id = email["id"]
        sender = email["sender"]
        subject = email["subject"]

        logger.debug("Processing email %s: %s", email_id, subject[:50])

        classification = self.llm_client.classify_email(
            sender=sender,
            subject=subject,
            content=email["content"],
            label_config=self.label_config,
        )

        email["classification"] = classification
        logger.info("Email %s classified as: %s", email_id, classification)

        if dry_run:
            logger.debug("Dry run: would apply label '%s' to email %s", classification, email_id)
            return True

        self.gmail_client.apply_label(email_id, classification)
        logger.debug("Applied label '%s' to email %s", classification, email_id)
        return True


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the workflow."""
    parser = argparse.ArgumentParser(
        description="Classify unread Gmail messages and apply labels."
    )
    parser.add_argument(
        "-n",
        "--num-messages",
        type=int,
        default=10,
        help="Maximum number of unread emails to process (default: 10).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Classify emails without applying labels; print the labels that would be applied.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print the result of processing each email.",
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
        workflow.run(
            max_emails=args.num_messages,
            dry_run=args.dry_run,
            verbose=args.verbose or args.dry_run,
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
