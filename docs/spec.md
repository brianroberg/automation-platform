# Automation Platform Specification (Mac-Local)

## Project Overview

### Vision
Build a modular Python automation framework running locally on Mac with containerized isolation. Prioritizes developer experience, maintainability, and extensibility while keeping everything self-contained.

### Goals
- **Local-First**: Everything runs on your Mac, no remote dependencies
- **Isolated**: Docker containers for clean environment separation
- **Simple**: Avoid deployment complexity while maintaining modularity
- **Developer-Friendly**: Full visibility for AI coding assistants (Claude Code)
- **Extensible**: Easy to add new workflows without modifying existing code

## Development Philosophy: MVP-First

**Core Principle**: Build the minimum viable product (email classifier) first, then iterate.

### MVP Scope: Email Classification Workflow
The MVP must successfully:
1. Connect to Gmail API with restricted OAuth scopes
2. Fetch unread emails
3. Classify emails using LLM (via LLM library with MLX)
4. Apply appropriate Gmail labels
5. Handle errors gracefully
6. Log activity for debugging

### MVP Requirements
**Essential (Build First):**
- Gmail API client with OAuth authentication
- LLM library integration with MLX provider
- Email classification logic
- Label application functionality
- Basic error handling and logging
- Command-line execution (python script)
- Unit tests for core functionality

**Deferred (Build After MVP Works):**
- FastAPI web interface
- macOS launchd scheduling
- Multiple LLM provider support (OpenAI, Anthropic, etc.)
- Ollama fallback (if MLX issues arise)
- Docker containerization (can use venv initially)
- Workflow plugin system
- Configuration file management (use .env first)
- Advanced retry logic
- Monitoring and alerting
- macOS notifications
- Menu bar integration
- Additional workflows beyond email triage

**Quality Standards (Always Required):**
- Clean, readable code
- Proper error handling
- Basic logging
- Unit tests for critical paths
- Documentation of key functions
- Git version control

### Sequencing Rationale
This approach ensures:
- **Fast validation**: Prove the concept works before investing in infrastructure
- **Early feedback**: Test with real emails to refine classification logic
- **Risk reduction**: Identify integration issues early
- **Iterative improvement**: Add features based on actual usage needs
- **Maintainability**: Each feature builds on a working foundation

## Architecture

### Deployment Model
- **Runtime**: Local Mac only
- **Isolation**: Docker containers for clean environment separation
- **Scheduling**: macOS launchd or cron for automation triggers
- **Data**: Scoped directory access via Docker volumes
- **AI**: Local LLM access via Simon Willison's LLM library with MLX

### LLM Integration Strategy
Use [Simon Willison's LLM library](https://llm.datasette.io/en/stable/) as the interface layer for all AI/LLM interactions:

**Primary Provider: MLX** via [llm-mlx](https://github.com/simonw/llm-mlx) plugin
- Optimized for Apple Silicon performance
- Native Mac hardware acceleration
- Fast inference for email classification

**Fallback Provider: Ollama** via [llm-ollama](https://github.com/taketwo/llm-ollama) plugin
- Alternative if MLX has compatibility issues
- Wider model selection
- Only use if MLX proves insufficient

**Future Providers (Deferred):**
- OpenAI
- Anthropic Claude
- Other commercial APIs

**Benefits:**
- **Model Flexibility**: Easy switching between local and commercial models
- **Unified Interface**: Single API for all model providers
- **Performance**: MLX optimized for Mac hardware
- **Future-Proof**: Add providers without code changes

### System Architecture
automation-platform/
├── src/
│   ├── core/
│   │   ├── workflow_engine.py      # [DEFERRED] Core execution
│   │   ├── scheduler.py            # [DEFERRED] Task scheduling
│   │   └── config.py              # [MVP] Simple configuration
│   ├── integrations/
│   │   ├── gmail_client.py        # [MVP] Gmail API (restricted scopes)
│   │   ├── llm_client.py          # [MVP] LLM library wrapper (MLX)
│   │   └── base_client.py         # [DEFERRED] Base integration class
│   ├── workflows/
│   │   ├── email_triage.py        # [MVP] Primary workflow
│   │   └── workflow_base.py       # [DEFERRED] Base workflow class
│   ├── api/
│   │   └── server.py              # [DEFERRED] Optional FastAPI interface
│   └── utils/
│       ├── logging.py             # [MVP] Basic logging
│       └── helpers.py             # [MVP] Essential utilities only
├── config/
│   ├── .env                       # [MVP] Simple environment config
│   ├── workflows.yaml             # [DEFERRED] Complex workflow definitions
│   ├── integrations.yaml          # [DEFERRED] Service configurations
│   └── launchd/                   # [DEFERRED] macOS scheduling configs
├── data/                          # [DEFERRED initially - use temp/logs only]
│   ├── logs/                      # [MVP] Basic log files
│   ├── cache/                     # [DEFERRED]
│   └── state/                     # [DEFERRED]
├── requirements.txt               # [MVP]
├── docker-compose.yml             # [DEFERRED]
├── .env.example                   # [MVP]
├── README.md                      # [MVP] Basic setup instructions
└── tests/                         # [MVP] Critical path tests only
└── test_email_triage.py
## Technical Requirements

### Mac-Specific Considerations
- **Scheduling**: macOS launchd for reliable background execution [DEFERRED]
- **Permissions**: Keychain integration for secure credential storage [MVP - basic .env first]
- **Disk Access**: Scoped to specific directories only:
  - `~/automation-platform/` - app data [MVP]
  - Gmail attachments directory (if specified by user) [DEFERRED]
  - **NO system-wide or full disk access**
- **Performance**: MLX optimized for Apple Silicon

### LLM Integration
- **Primary Interface**: Simon Willison's LLM library [MVP]
- **Primary Provider**: MLX-optimized models via llm-mlx plugin [MVP]
- **Fallback Provider**: Ollama via llm-ollama plugin [DEFERRED - only if MLX issues]
- **Commercial Models**: OpenAI, Anthropic [DEFERRED - add after MVP]
- **Configuration**: Model selection via environment variables [MVP]

### Gmail API Integration
**OAuth Scopes (MVP):**
- `openid` - Basic profile identity [MVP]
- `https://www.googleapis.com/auth/userinfo.email` - Access to account email address [MVP]
- `https://www.googleapis.com/auth/gmail.modify` - Read and modify Gmail messages and labels [MVP]

**Explicitly Excluded:**
- `gmail.send` - Sending email (NOT GRANTED)
- `gmail.compose` - Creating/sending drafts (NOT GRANTED)

**Security Note**: 
- Application can read, label, archive, and mark messages as read/unread
- Cannot send messages or create drafts
- No direct access to compose/send scopes; only metadata modifications needed for triage

### Development Environment
- **Primary**: Python venv initially [MVP], Docker Desktop later [DEFERRED]
- **AI**: LLM library with MLX provider [MVP]
- **Storage**: Local directory structure [MVP]
- **Monitoring**: Basic print/log statements [MVP], Console.app integration [DEFERRED]

## Implementation Strategy

### Phase 1: MVP - Email Classification (Week 1)
**Goal**: Get email classification working end-to-end

**Day 1-2: Foundation**
- Set up Python project structure (minimal)
- Install LLM library and llm-mlx plugin
- Configure MLX model
- Create .env file for configuration
- Basic logging setup

**Day 3-4: Gmail Integration**
- Implement Gmail OAuth flow (readonly + labels scopes)
- Create simple gmail_client.py to fetch unread emails
- Test authentication and email retrieval

**Day 5-6: Classification Logic**
- Implement llm_client.py wrapper around LLM library (MLX)
- Build email classification function
- Test with sample emails

**Day 7: Integration & Testing**
- Connect all components in email_triage.py
- Apply labels based on classification
- Write basic tests
- Document usage in README

**Success Criteria**: Can run `python email_triage.py` and it successfully classifies and labels unread emails using MLX

### Phase 2: Refinement (Week 2)
**Only if MVP works:**
1. Improve error handling
2. Add retry logic for API failures
3. Enhance logging
4. Expand test coverage
5. Refine classification prompts based on results

### Phase 3: Infrastructure (Week 3+)
**Only after Phase 2 complete:**
1. Add Docker containerization
2. Implement scheduling (launchd or cron)
3. Create configuration file system (YAML)
4. Build plugin architecture for new workflows

### Phase 4: Platform Features (Week 4+)
**Only after Phase 3 complete:**
1. FastAPI web interface
2. Multiple LLM provider support (Ollama, OpenAI, Anthropic)
3. Workflow engine abstraction
4. Additional integrations
5. macOS-specific features (notifications, menu bar)

### Sequencing Decision Framework
For each feature, ask:
1. **Is it needed for MVP?** If no → defer
2. **Does it block testing core functionality?** If no → defer
3. **Can we validate the concept without it?** If yes → defer
4. **Is it complex/risky?** If yes → defer until proven value

## Success Criteria

### MVP Success (Phase 1)
- [ ] Successfully authenticate with Gmail API (readonly + labels scopes)
- [ ] Fetch unread emails programmatically
- [ ] Classify email using LLM library with MLX
- [ ] Apply correct Gmail label based on classification
- [ ] Handle API errors without crashing
- [ ] Log activity for debugging
- [ ] Pass basic unit tests
- [ ] Can run manually via command line

### Post-MVP Success (Phases 2-4)
- Automated scheduling works reliably
- Multiple LLM providers supported (Ollama, commercial APIs)
- New workflows easy to add
- System runs for weeks without intervention
- Comprehensive test coverage

### Security Requirements (All Phases)
- **No full disk access** - only scoped directories
- **No email sending capability** - OAuth scopes prevent this
- **Credential isolation** - environment variables initially, Keychain later
- **Container isolation** - deferred to Phase 3

## Project Plan Summary

**Week 1**: Build and validate email classification MVP with MLX
**Week 2**: Refine based on actual usage
**Week 3+**: Add infrastructure only after core works
**Week 4+**: Expand platform capabilities

This specification provides clear sequencing from MVP to full platform, ensuring we validate the core concept before investing in elaborate infrastructure.
