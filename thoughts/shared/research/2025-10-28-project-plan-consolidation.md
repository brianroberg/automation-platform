---
date: 2025-10-28T23:17:29+0000
researcher: Claude
git_commit: b6e1c716bb1f5e094aac5dae69216f46e1d52e25
branch: main
repository: https://github.com/brianroberg/automation-platform
topic: "Consolidated Project Plan for Email Classification Automation Platform"
tags: [research, codebase, project-plan, mvp, email-classification]
status: complete
last_updated: 2025-10-28
last_updated_by: Claude
---

# Research: Consolidated Project Plan for Email Classification Automation Platform

**Date**: 2025-10-28T23:17:29+0000
**Researcher**: Claude
**Git Commit**: b6e1c716bb1f5e094aac5dae69216f46e1d52e25
**Branch**: main
**Repository**: https://github.com/brianroberg/automation-platform

## Research Question

Review the project plan documents in the `docs` folder and consolidate them into a form that can be given to a project planner who will generate a detailed implementation plan for the project.

## Executive Summary

The **Automation Platform** is a Mac-local email classification system that uses LLMs to automatically triage Gmail emails by applying appropriate labels. The project follows an MVP-first approach, currently at **Phase 2 completion (LLM Integration)** with **Phase 3 (Gmail Integration)** and **Phase 4 (Email Triage Workflow)** remaining.

**Current Status:**
- ✅ **Phase 1 Complete**: Project foundation (config, logging, project structure)
- ✅ **Phase 2 Complete**: LLM integration (client implemented, tested, production-ready)
- ⏳ **Phase 2 Blocked**: Pending MLX server setup decision
- 🔜 **Phase 3 Next**: Gmail API integration (not started)
- 🔜 **Phase 4 Pending**: Email triage workflow orchestration (not started)
- 🔜 **Phase 5 Pending**: End-to-end testing and documentation (not started)

**Key Technical Decision**: MLX-first strategy
- **Development**: MLX server on Apple Silicon (accessed remotely via secure network)
- **Production**: Same MLX server on macOS laptop (free, private, fast)
- **Interface**: Unified OpenAI-compatible client (provider-agnostic)

## Project Overview

### Vision

Build a modular Python automation framework running locally on Mac with containerized isolation. Prioritizes developer experience, maintainability, and extensibility while keeping everything self-contained.

### Core Goals

1. **Local-First**: Everything runs on your Mac, no remote dependencies (production mode)
2. **Isolated**: Docker containers for clean environment separation (deferred to Phase 3+)
3. **Simple**: Avoid deployment complexity while maintaining modularity
4. **Developer-Friendly**: Full visibility for AI coding assistants (Claude Code)
5. **Extensible**: Easy to add new workflows without modifying existing code (future)

### MVP Scope: Email Classification Workflow

The MVP successfully:
1. Connects to Gmail API with restricted OAuth scopes (`gmail.readonly` + `gmail.labels`)
2. Fetches unread emails from inbox
3. Classifies emails using LLM (via provider-agnostic client, with MLX as the default deployment)
4. Applies appropriate Gmail labels based on classification
5. Handles errors gracefully with comprehensive logging
6. Logs activity for debugging and monitoring

**Security Constraints**:
- Cannot send emails (scopes exclude `gmail.send`)
- Cannot modify email content (readonly access only)
- Cannot delete emails
- Limited to label management and reading

## Current Implementation Status

### Completed Components ✅

#### 1. Configuration Module (`src/core/config.py:1-79`)
- **Status**: Production-ready
- **Features**:
  - Environment variable management via python-dotenv
  - Gmail OAuth scope definitions (`gmail.readonly`, `gmail.labels`)
  - LLM provider configuration (base_url, model, api_key)
  - Label configuration loading from JSON
  - Automatic directory creation for config/ and logs/
- **Code References**:
  - Gmail scopes: `config.py:28-31`
  - LLM defaults: `config.py:36` (default model: `mlx-community/Llama-3.2-3B-Instruct-4bit`)
  - Label config loader: `config.py:46-67`

#### 2. LLM Client (`src/integrations/llm_client.py:1-221`)
- **Status**: Production-ready
- **Features**:
  - Supports MLX (primary) and other OpenAI-compatible APIs
  - Server verification on initialization
  - Email classification with structured prompts
  - Label validation with fallback to default
  - Content truncation (1000 chars max)
  - Deterministic classification (temperature=0.0)
  - Comprehensive error handling
- **Key Methods**:
  - `classify_email(sender, subject, content, label_config)` at lines 124-180
  - `_build_classification_prompt()` at lines 182-220
  - `_verify_server_available()` at lines 95-122
- **Configuration**:
  - Environment: `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY`
  - Supports provider detection from URL (lines 75-84)
- **Testing**: 7 comprehensive unit tests passing
  - Server verification, classification, error handling, truncation, validation

#### 3. Logging Utilities (`src/utils/logging.py`)
- **Status**: Production-ready
- **Features**:
  - Configurable log levels via environment variable
  - File and console logging
  - Automatic log directory creation
  - Structured log format with timestamps

#### 4. Label Configuration (`config/labels.json`)
- **Status**: Example configuration provided
- **Labels Defined**:
  - `response-required`: Emails requiring direct response
  - `fyi`: Informational emails (default)
  - `transactional`: Automated notifications and receipts

#### 5. Dependencies (`requirements.txt`)
- All required libraries installed:
  - Google API: `google-auth`, `google-api-python-client`, etc. (lines 4-8)
  - OpenAI: `openai>=1.0.0` (line 11)
  - Configuration: `python-dotenv==1.1.1` (line 2)

### Not Yet Implemented ⏭️

#### 1. Gmail Client (`src/integrations/gmail_client.py`)
- **Phase**: 3 (Next)
- **Planned Methods**:
  - `_authenticate()` - OAuth 2.0 flow with restricted scopes
  - `get_unread_emails(max_results)` - Fetch unread emails from inbox
  - `_get_email_details(msg_id)` - Extract email metadata and content
  - `_extract_body(payload)` - Parse plain text body from MIME structure
  - `apply_label(msg_id, label_name)` - Apply label to email
  - `_get_or_create_label(label_name)` - Ensure label exists
- **Dependencies Ready**: Google API libraries already in requirements.txt
- **Configuration Ready**: OAuth scopes and file paths defined in Config

#### 2. Email Triage Workflow (`src/workflows/email_triage.py`)
- **Phase**: 4
- **Planned Structure**:
  - `EmailTriageWorkflow` class to orchestrate Gmail + LLM clients
  - `__init__()` - Initialize Gmail client, LLM client, load label config
  - `run(max_emails, dry_run)` - Main workflow execution
  - `_process_email(email)` - Classify and label individual email
  - `main()` - CLI entry point
- **Data Flow**:
  ```
  GmailClient.get_unread_emails() → emails
  For each email:
    LLMClient.classify_email() → label
    GmailClient.apply_label(label)
  Return statistics
  ```

#### 3. End-to-End Tests
- **Phase**: 5
- **Coverage Needed**:
  - Full workflow integration test
  - Gmail API mocking for CI/CD
  - Error handling scenarios
  - Dry-run mode validation

#### 4. Infrastructure (Deferred Post-MVP)
- Docker containerization
- macOS launchd scheduling
- FastAPI web interface
- Workflow plugin system
- Additional workflow types

## Remaining Work Breakdown

### Phase 3: Gmail Integration (Next Phase)

**Objective**: Implement Gmail API client with OAuth authentication and email operations.

**Tasks**:
1. **OAuth Setup**
   - Create Gmail API project in Google Cloud Console
   - Configure OAuth consent screen
   - Download credentials JSON
   - Implement OAuth flow using `InstalledAppFlow`
   - Token persistence and refresh logic

2. **Gmail Client Implementation**
   - `_authenticate()` method with token caching
   - `get_unread_emails()` to query `is:unread in:inbox`
   - `_get_email_details()` to extract sender, subject, content
   - `_extract_body()` to parse plain text from MIME structure
   - `apply_label()` to modify email labels
   - `_get_or_create_label()` for label management

3. **Unit Testing**
   - Mock Google API responses
   - Test OAuth flow
   - Test email fetching and parsing
   - Test label application
   - Test error handling

4. **Documentation**
   - OAuth setup guide
   - API quota management
   - Error scenarios

**Acceptance Criteria**:
- Successfully authenticate with Gmail API using OAuth
- Fetch unread emails programmatically
- Parse email sender, subject, and content correctly
- Apply labels to emails
- All unit tests passing
- OAuth token refreshes automatically

**Estimated Effort**: 2-3 days

### Phase 4: Email Triage Workflow (After Phase 3)

**Objective**: Orchestrate Gmail and LLM clients into end-to-end workflow.

**Tasks**:
1. **Workflow Class Implementation**
   - `EmailTriageWorkflow.__init__()` to initialize clients
   - `run()` method with max_emails and dry_run parameters
   - `_process_email()` for individual email classification
   - Statistics tracking (processed, classified, failed)

2. **CLI Entry Point**
   - `main()` function with argument parsing
   - Logging setup
   - Exit code handling (0=success, 1=error, 130=interrupt)

3. **Error Handling**
   - Individual email failures don't stop workflow
   - Comprehensive error logging
   - Graceful degradation

4. **Integration Testing**
   - End-to-end workflow test with mocked APIs
   - Dry-run mode validation
   - Statistics verification

**Acceptance Criteria**:
- Can run `python -m src.workflows.email_triage` successfully
- Classifies and labels emails end-to-end
- Handles errors gracefully without crashing
- Logs all activity appropriately
- Dry-run mode works correctly
- Returns accurate statistics

**Estimated Effort**: 1-2 days

### Phase 5: Testing & Documentation (After Phase 4)

**Objective**: Comprehensive testing and user documentation.

**Tasks**:
1. **End-to-End Testing**
   - Full workflow integration test
   - Validate MLX connectivity from development and production environments
   - Error scenario testing
   - Performance testing

2. **Documentation**
   - Setup guide (OAuth, LLM provider, environment config)
   - Usage guide (running manually, understanding logs)
   - Troubleshooting guide
   - Label customization guide

3. **Quality Assurance**
   - Test with real Gmail account
   - Verify classification accuracy
   - Monitor API quota usage
   - Performance benchmarking

**Acceptance Criteria**:
- All tests passing (unit + integration)
- Documentation complete and accurate
- Successfully tested with real emails
- Performance meets expectations (<500ms per email)

**Estimated Effort**: 1-2 days

## Technical Architecture

### Deployment Model

- **Runtime**: Local Mac for production, Linux for development
- **Isolation**: Docker containers (deferred to post-MVP)
- **Scheduling**: macOS launchd or cron (deferred to post-MVP)
- **Data**: Scoped directory access (~/automation-platform/)
- **AI**: MLX-first inference accessible via secure network (see below)

### LLM Integration Strategy

**MLX-First Approach**:

#### Development Environment
- **Access Method**: Remote connection to MLX server (e.g. via Tailscale)
- **Configuration**:
  ```bash
  LLM_BASE_URL=http://<tailscale-host>:8080/v1
  LLM_MODEL=mlx-community/Llama-3.2-3B-Instruct-4bit
  LLM_API_KEY=not-needed
  ```
- **Benefits**:
  - Same infrastructure as production
  - No third-party data sharing
  - Consistent behavior across environments
  - Debuggable from remote environments with network visibility

#### Production Environment
- **Provider**: MLX server on macOS laptop
- **Configuration**:
  ```bash
  LLM_BASE_URL=http://localhost:8080/v1
  LLM_MODEL=mlx-community/Llama-3.2-3B-Instruct-4bit
  LLM_API_KEY=not-needed
  ```
- **Benefits**:
  - Free operation (no API costs)
  - Complete privacy (data stays on laptop)
  - Fast inference (~50-200ms latency)
  - Offline capable (after model download)
  - Apple Silicon optimized

#### Alternative Providers
- **OpenAI**: For highest quality, more expensive (~$18/year vs $4/year)
- **Ollama**: Local alternative to MLX, works on Linux but slower on Mac

**Provider Switching**: No code changes needed, just update `.env` file.

### System Architecture

```
automation-platform/
├── src/
│   ├── core/
│   │   └── config.py              [✅ IMPLEMENTED]
│   ├── integrations/
│   │   ├── gmail_client.py        [⏭️ PHASE 3]
│   │   └── llm_client.py          [✅ IMPLEMENTED]
│   ├── workflows/
│   │   └── email_triage.py        [⏭️ PHASE 4]
│   └── utils/
│       └── logging.py             [✅ IMPLEMENTED]
├── config/
│   ├── .env                       [✅ CONFIGURED]
│   ├── labels.json                [✅ CONFIGURED]
│   ├── gmail_credentials.json     [⏭️ PHASE 3 - user provides]
│   └── gmail_token.json           [⏭️ PHASE 3 - auto-generated]
├── data/
│   └── logs/                      [✅ AUTO-CREATED]
├── tests/
│   └── test_llm_client.py         [✅ IMPLEMENTED]
├── docs/
│   ├── spec.md                    [✅ COMPLETE]
│   ├── llm_configuration.md       [✅ COMPLETE]
│   ├── mlx_server_setup.md        [✅ COMPLETE]
│   └── development_environment.md [✅ COMPLETE]
├── requirements.txt               [✅ COMPLETE]
└── .env.example                   [✅ COMPLETE]
```

### Data Flow (Planned)

```
1. Config.load_label_config()
   → Load label definitions from config/labels.json

2. EmailTriageWorkflow.__init__()
   → Initialize GmailClient (OAuth authentication)
   → Initialize LLMClient (connect to provider)

3. EmailTriageWorkflow.run()
   → GmailClient.get_unread_emails()
   → Returns list of email dicts

4. For each email:
   → LLMClient.classify_email(email, label_config)
   → Returns classification label

   → GmailClient.apply_label(email_id, label)
   → Applies label in Gmail

5. Return statistics
   → Total processed, successful, failed
   → Classification breakdown by label
```

### Security Model

**OAuth Scopes** (Minimal Permissions):
- `https://www.googleapis.com/auth/gmail.readonly` - Read emails only
- `https://www.googleapis.com/auth/gmail.labels` - Manage labels only

**Explicitly Excluded**:
- ❌ `gmail.send` - Cannot send emails
- ❌ `gmail.compose` - Cannot create drafts
- ❌ `gmail.modify` - Cannot delete or modify email content

**Credential Storage**:
- Gmail credentials: `config/gmail_credentials.json` (user-provided, not committed)
- Gmail token: `config/gmail_token.json` (auto-generated, not committed)
- LLM API keys: `.env` file (not committed)
- `.gitignore` configured to exclude all secrets

**Data Privacy**:
- Development and production share the same MLX server, so email content remains on hardware you control.

## Dependencies and Blockers

### Current Blocker (Phase 2)

**MLX Server Accessibility** (documented in `thoughts/shared/handoffs/general/2025-10-09_02-04-50_phase2-llm-integration.md:19-40`):

- **Issue**: MLX runs only on macOS with Apple Silicon
- **Impact**: Development environments (Codespaces/Linux) must reach MLX remotely
- **Solution Implemented**: Provide network access (e.g. Tailscale) from development to the MLX host

**Action Required**:
1. Ensure Tailscale (or equivalent) is configured between development environment and Mac
2. Keep `mlx_lm.server` running on the Mac for both development and production testing

### Dependencies for Phase 3

**External Requirements**:
1. **Google Cloud Console Access**
   - Create Gmail API project
   - Configure OAuth consent screen
   - Download credentials JSON

2. **Gmail Account**
   - Test account with representative emails
   - Permission to enable API access

3. **API Quota Awareness**
   - Gmail API has free tier quotas
   - Should be sufficient for personal use
   - Monitor usage to avoid limits

### Dependencies for Phase 4

**Internal Requirements**:
- Phase 3 complete (Gmail client implemented and tested)
- Label configuration finalized (can customize in `config/labels.json`)

### Dependencies for Phase 5

**Internal Requirements**:
- Phase 4 complete (workflow implemented)
- Real Gmail account for end-to-end testing
- LLM provider configured (MLX base URL reachable)

**Optional for Production**:
- MLX server running on macOS laptop
- macOS launchd configuration (for scheduled execution)

## Success Criteria

### MVP Success (Phase 1-4 Complete)

- [x] **Phase 1**: Project foundation complete
- [x] **Phase 2**: LLM integration complete
- [ ] **Phase 3**: Gmail API integration complete
  - [ ] Successfully authenticate with Gmail API (readonly + labels scopes)
  - [ ] Fetch unread emails programmatically
  - [ ] Apply Gmail labels programmatically
  - [ ] OAuth token refreshes automatically
- [ ] **Phase 4**: Email triage workflow complete
  - [ ] Classify email using LLM client with configured provider
  - [ ] Apply correct Gmail label based on classification
  - [ ] Handle API errors without crashing
  - [ ] Log activity for debugging
  - [ ] Can run manually via command line
  - [ ] Dry-run mode works correctly
- [ ] **Phase 5**: Testing and documentation complete
  - [ ] All unit tests passing
  - [ ] Integration tests passing
  - [ ] End-to-end test with real emails successful
  - [ ] Documentation complete

### Post-MVP Goals (Deferred)

- Automated scheduling via macOS launchd
- Docker containerization
- FastAPI web interface
- Multiple workflow types
- Menu bar integration
- macOS notifications
- Advanced retry logic and monitoring

### Quality Standards (Always Required)

- ✅ Clean, readable code
- ✅ Proper error handling
- ✅ Comprehensive logging
- ✅ Unit tests for critical paths
- ✅ Documentation of key functions
- ✅ Git version control with meaningful commits

## Implementation Recommendations

### Immediate Next Steps

1. **Ensure MLX Access**:
   - Configure secure network access (e.g. Tailscale) between development environment and Mac
   - Start `mlx_lm.server` on the Apple Silicon laptop
   - Set `LLM_BASE_URL`, `LLM_MODEL`, and `LLM_API_KEY` (if required) in `.env`
   - Test the LLM client with a sample email classification

2. **Begin Phase 3** (Gmail Integration):
   - Set up Gmail API project in Google Cloud Console
   - Download OAuth credentials
   - Implement `GmailClient` class following specification
   - Write unit tests with mocked API responses
   - Test OAuth flow manually

3. **Complete Phase 4** (Email Triage Workflow):
   - Implement `EmailTriageWorkflow` class
   - Create CLI entry point
   - Test with dry-run mode
   - Validate end-to-end flow

4. **Finalize Phase 5** (Testing & Documentation):
   - Run integration tests
   - Test with real Gmail account
   - Measure performance and accuracy
   - Create user-facing setup guide

### Best Practices

1. **Testing Strategy**:
   - Mock external APIs (Gmail, LLM) in unit tests
   - Use real APIs only in integration tests
   - Implement dry-run mode for safe testing
   - Start with small email batches (max_emails=5)

2. **Configuration Management**:
   - Keep secrets in `.env` (never commit)
   - Use `.env.example` as template
   - Document all environment variables
   - Validate configuration on startup

3. **Error Handling**:
   - Individual email failures should not stop workflow
   - Log all errors with context (email ID, error message)
   - Return statistics including failure counts
   - Graceful degradation when possible

4. **Logging Strategy**:
   - `logger.info()` for workflow lifecycle events
   - `logger.debug()` for detailed processing info
   - `logger.error()` for failures
   - Include timestamps and email IDs in logs

5. **Performance Monitoring**:
   - Track classification latency
   - Monitor API quota usage (Gmail API)
   - Log statistics per run
   - Benchmark different LLM providers

## Code References

### Implemented Components

- **Config Module**: `src/core/config.py:1-79`
  - Gmail scopes: `config.py:28-31`
  - LLM defaults: `config.py:36`
  - Label config loader: `config.py:46-67`

- **LLM Client**: `src/integrations/llm_client.py:1-221`
  - Classification method: `llm_client.py:124-180`
  - Prompt builder: `llm_client.py:182-220`
  - Server verification: `llm_client.py:95-122`

- **Logging Utilities**: `src/utils/logging.py`

- **Tests**: `tests/test_llm_client.py`
  - 7 test cases covering initialization, classification, errors, validation

### Documentation

- **Main Specification**: `docs/spec.md:1-268`
  - MVP scope: `spec.md:19-51`
  - Architecture: `spec.md:68-135`
  - Implementation phases: `spec.md:176-235`

- **LLM Configuration Guide**: `docs/llm_configuration.md:1-295`
  - Dual-environment strategy: `llm_configuration.md:8-22`
  - Provider options: `llm_configuration.md:25-186`
  - Troubleshooting: `llm_configuration.md:206-235`

- **MLX Server Setup**: `docs/mlx_server_setup.md:1-272`
  - Installation guide: `mlx_server_setup.md:13-75`
  - Tailscale setup: `mlx_server_setup.md:38-58` (optional)
  - Production service: `mlx_server_setup.md:142-182`

- **Development Environment**: `docs/development_environment.md:1-467`
  - Quick start: `development_environment.md:59-138`
  - Workflow scenarios: `development_environment.md:172-237`
  - Troubleshooting: `development_environment.md:238-315`

### Historical Context

- **Phase 2 Handoff**: `thoughts/shared/handoffs/general/2025-10-09_02-04-50_phase2-llm-integration.md`
  - Completion status: Lines 19-40
  - MLX platform decision: Lines 42-70
  - Implementation patterns: Lines 72-115
  - Next steps: Lines 117-141

- **MVP Implementation Plan**: `thoughts/shared/plans/2025-10-08-email-classification-mvp.md`
  - Phase definitions: Throughout document
  - Gmail client specification: Lines 333-590
  - Workflow specification: Lines 1740-1931

## Related Research

- None yet (this is the first research document for this project)

## Open Questions

1. **LLM Provider Selection**:
   - Is secure connectivity to the MLX server configured for all development environments?
   - Is `mlx_lm.server` running on the Apple Silicon laptop?
   - Are fallback providers needed for contingency testing?

2. **Gmail API Setup**:
   - Has Google Cloud Console project been created?
   - Are OAuth credentials available?
   - Is test Gmail account configured?

3. **Label Configuration**:
   - Are the current labels (response-required, fyi, transactional) sufficient?
   - Should additional labels be added before Phase 3?
   - How should default label behavior work?

4. **Scheduling Strategy**:
   - How frequently should email triage run? (e.g., every 5 minutes, hourly)
   - Should scheduling be implemented in MVP or deferred?
   - macOS launchd vs. cron for scheduling?

5. **Performance Requirements**:
   - What is acceptable latency per email classification?
   - How many emails should be processed per run?
   - Are there Gmail API quota concerns?

6. **Post-MVP Roadmap**:
   - Which deferred features are highest priority?
   - Should additional workflow types be added?
   - Is web interface needed or is CLI sufficient?
