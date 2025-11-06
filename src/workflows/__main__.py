"""Allow running workflows package directly."""

from src.workflows.email_triage import main

if __name__ == "__main__":
    raise SystemExit(main())
