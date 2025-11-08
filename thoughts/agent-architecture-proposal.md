# Agent Architecture Proposal: Transforming automation-platform

**Date:** 2025-11-08
**Author:** Claude (AI Assistant)
**Based on:** [Everyone should write their own agent](https://fly.io/blog/everyone-write-an-agent/) by Fly.io

---

## Executive Summary

This proposal outlines how to transform the automation-platform from a single-purpose email classifier into a true agent-based automation system following principles from Fly.io's article on agent design. The key insight is that **agents are simple** — they're just context arrays + LLM calls + tools — and building our own gives us architectural control that platforms like Claude Code or Cursor cannot provide.

**Current State:** Rule-based email triage with LLM classification
**Proposed State:** Multi-agent orchestration system with tool-calling, sub-agents, and autonomous decision-making
**Philosophy Shift:** From "automation scripts" to "autonomous agents"

---

## Core Principles from the Fly.io Article

### 1. **Agents are Surprisingly Simple**
The basic agent structure:
- Maintain conversation history (context array)
- Call LLM with context + available tools
- LLM decides next action (respond or call tool)
- Execute tools, append results to context
- Loop until task complete

### 2. **Context Engineering is Real Programming**
Managing context involves legitimate engineering tradeoffs:
- Token budget allocation
- Balancing explicit control vs emergent behavior
- Designing intermediate data representations (JSON, SQL, markdown)
- Context compression through summarization

### 3. **Build Your Own Agents**
Don't rely solely on platforms (Claude Code, Cursor):
- Gain architectural control
- Enable sophisticated customization
- Experiment with novel patterns
- Own the decision-making logic

### 4. **Use Segregated Contexts and Sub-Agents**
- Create separate context arrays for different capabilities
- Structure agent hierarchies that delegate and summarize
- Enable parallel reasoning on different aspects
- Reduce context pollution

### 5. **Many Open Problems Remain**
Individual exploration can resolve:
- Balance between unpredictability and structured behavior
- Connecting agents to ground truth
- Managing multi-stage operations
- Error recovery and self-correction

---

## Current Architecture Analysis

### What We Have Now

**Strengths:**
- ✅ **Two-stage decision making** (deterministic rules + LLM)
- ✅ **Provider-agnostic LLM integration** (OpenAI-compatible API)
- ✅ **Local-first, privacy-focused** architecture
- ✅ **Clear tool abstraction** (Gmail client, LLM client)
- ✅ **Structured configuration** (JSON labels, YAML rules)
- ✅ **Modular, extensible design**

**Limitations:**
- ❌ **Single-purpose** (only email triage)
- ❌ **No true agent behavior** (just classification workflow)
- ❌ **No tool-calling pattern** (LLM only returns labels, not actions)
- ❌ **No context management** (each email processed independently)
- ❌ **No learning or memory** (stateless across runs)
- ❌ **No multi-step reasoning** (one LLM call per email)
- ❌ **No agent hierarchy** (flat workflow, no delegation)

### The Opportunity

We have the **perfect foundation** to build a custom agent framework:
- Working LLM integration with local inference
- Clear understanding of one automation domain (email)
- Strong privacy/local-first requirements that justify custom solution
- Modular codebase ready for extension

---

## Proposed Agent Architecture

### Phase 1: Core Agent Framework

**Goal:** Build the fundamental agent loop and tool-calling infrastructure.

#### 1.1 Agent Base Class

Create `src/core/agent.py`:

```python
from typing import List, Dict, Any, Callable
from dataclasses import dataclass
import json

@dataclass
class Message:
    role: str  # "system", "user", "assistant", "tool"
    content: str
    tool_calls: List[Dict] = None
    tool_call_id: str = None

@dataclass
class Tool:
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON schema
    function: Callable

class Agent:
    """Base agent with context management and tool calling."""

    def __init__(
        self,
        name: str,
        system_prompt: str,
        llm_client,
        tools: List[Tool] = None,
        max_iterations: int = 10
    ):
        self.name = name
        self.context: List[Message] = []
        self.llm_client = llm_client
        self.tools = {tool.name: tool for tool in (tools or [])}
        self.max_iterations = max_iterations

        # Initialize with system prompt
        self.context.append(Message(role="system", content=system_prompt))

    def run(self, user_input: str) -> str:
        """Execute agent loop until completion."""
        self.context.append(Message(role="user", content=user_input))

        for iteration in range(self.max_iterations):
            # Call LLM with context and available tools
            response = self.llm_client.chat(
                messages=self.context,
                tools=[self._tool_schema(t) for t in self.tools.values()]
            )

            # Check if LLM wants to call tools
            if response.tool_calls:
                self.context.append(response)

                # Execute each tool call
                for tool_call in response.tool_calls:
                    result = self._execute_tool(tool_call)
                    self.context.append(Message(
                        role="tool",
                        content=json.dumps(result),
                        tool_call_id=tool_call.id
                    ))
                continue

            # Final response
            self.context.append(response)
            return response.content

        raise Exception(f"Agent {self.name} exceeded max iterations")

    def _execute_tool(self, tool_call) -> Dict[str, Any]:
        """Execute a tool and return results."""
        tool = self.tools.get(tool_call.function.name)
        if not tool:
            return {"error": f"Unknown tool: {tool_call.function.name}"}

        try:
            args = json.loads(tool_call.function.arguments)
            result = tool.function(**args)
            return {"success": True, "result": result}
        except Exception as e:
            return {"error": str(e)}

    def _tool_schema(self, tool: Tool) -> Dict:
        """Convert tool to OpenAI function schema."""
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters
            }
        }

    def get_context_summary(self) -> str:
        """Compress context for passing to parent agents."""
        # Use LLM to summarize conversation
        summary_prompt = "Summarize the key findings and decisions from this conversation in 2-3 sentences."
        # Implementation details...
        pass
```

#### 1.2 Tool Registry

Create `src/core/tools.py`:

```python
from typing import Dict, Any
from .agent import Tool

# Gmail Tools
def get_email_tool() -> Tool:
    return Tool(
        name="get_email",
        description="Retrieve email by ID with full content",
        parameters={
            "type": "object",
            "properties": {
                "email_id": {"type": "string", "description": "Gmail message ID"}
            },
            "required": ["email_id"]
        },
        function=lambda email_id: gmail_client.get_message(email_id)
    )

def search_emails_tool() -> Tool:
    return Tool(
        name="search_emails",
        description="Search Gmail with query string",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Gmail search query"},
                "max_results": {"type": "integer", "description": "Max emails to return"}
            },
            "required": ["query"]
        },
        function=lambda query, max_results=10: gmail_client.search_messages(query, max_results)
    )

def apply_label_tool() -> Tool:
    return Tool(
        name="apply_label",
        description="Apply Gmail label to email",
        parameters={
            "type": "object",
            "properties": {
                "email_id": {"type": "string"},
                "label": {"type": "string"}
            },
            "required": ["email_id", "label"]
        },
        function=lambda email_id, label: gmail_client.add_labels(email_id, [label])
    )

def send_email_tool() -> Tool:
    return Tool(
        name="send_email",
        description="Send email via Gmail",
        parameters={
            "type": "object",
            "properties": {
                "to": {"type": "string"},
                "subject": {"type": "string"},
                "body": {"type": "string"},
                "reply_to": {"type": "string", "description": "Message ID to reply to"}
            },
            "required": ["to", "subject", "body"]
        },
        function=lambda **kwargs: gmail_client.send_message(**kwargs)
    )

# Calendar Tools (future)
def create_calendar_event_tool() -> Tool:
    return Tool(
        name="create_calendar_event",
        description="Create Google Calendar event",
        parameters={
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "start_time": {"type": "string", "format": "date-time"},
                "end_time": {"type": "string", "format": "date-time"},
                "description": {"type": "string"}
            },
            "required": ["title", "start_time", "end_time"]
        },
        function=lambda **kwargs: calendar_client.create_event(**kwargs)
    )

# Research Tools
def web_search_tool() -> Tool:
    return Tool(
        name="web_search",
        description="Search the web for information",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string"}
            },
            "required": ["query"]
        },
        function=lambda query: web_search_client.search(query)
    )

def read_url_tool() -> Tool:
    return Tool(
        name="read_url",
        description="Fetch and parse content from URL",
        parameters={
            "type": "object",
            "properties": {
                "url": {"type": "string"}
            },
            "required": ["url"]
        },
        function=lambda url: web_client.fetch_content(url)
    )
```

#### 1.3 Updated LLM Client with Tool Support

Extend `src/integrations/llm_client.py`:

```python
def chat(
    self,
    messages: List[Message],
    tools: List[Dict] = None,
    temperature: float = 0.0
) -> Message:
    """
    Call LLM with conversation history and available tools.
    Returns either a text response or tool calls.
    """
    payload = {
        "model": self.model_name,
        "messages": [self._message_to_dict(m) for m in messages],
        "temperature": temperature
    }

    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    response = self.client.chat.completions.create(**payload)
    message = response.choices[0].message

    return Message(
        role="assistant",
        content=message.content or "",
        tool_calls=message.tool_calls if hasattr(message, "tool_calls") else None
    )
```

---

### Phase 2: Specialized Agent Implementations

#### 2.1 Email Triage Agent

Transform current workflow into an agent:

```python
class EmailTriageAgent(Agent):
    """Autonomous email classification and labeling agent."""

    def __init__(self, llm_client, gmail_client, config):
        system_prompt = f"""You are an email triage agent. Your job is to:
1. Read incoming emails
2. Classify them using available labels: {config.labels}
3. Apply appropriate Gmail labels
4. Handle edge cases intelligently

Available labels and their meanings:
{self._format_label_descriptions(config.labels)}

You have access to tools to read emails, search for context, and apply labels.
Use deterministic_check first to see if rules have pre-classified the email.
"""

        tools = [
            get_email_tool(),
            search_emails_tool(),
            apply_label_tool(),
            Tool(
                name="deterministic_check",
                description="Check if deterministic rules apply to email",
                parameters={"type": "object", "properties": {
                    "email_data": {"type": "object"}
                }},
                function=lambda email_data: deterministic_rules.evaluate(email_data)
            )
        ]

        super().__init__(
            name="email_triage",
            system_prompt=system_prompt,
            llm_client=llm_client,
            tools=tools
        )
        self.gmail_client = gmail_client

    def process_inbox(self, max_emails: int = 10):
        """Process unlabeled emails in inbox."""
        emails = self.gmail_client.get_unlabeled_messages(max_emails)

        for email in emails:
            result = self.run(f"Triage this email: {email.id}")
            logger.info(f"Triaged {email.id}: {result}")
```

#### 2.2 Email Response Agent

New capability: Autonomous email responses

```python
class EmailResponseAgent(Agent):
    """Agent that can draft and send email responses."""

    def __init__(self, llm_client, gmail_client):
        system_prompt = """You are an email response agent. You can:
1. Read emails that require responses
2. Search for relevant context (past emails, documents)
3. Draft appropriate responses
4. Send responses (with user approval)

Always be professional, concise, and helpful. When drafting responses:
- Match the tone of the original email
- Address all questions/requests
- Include relevant context
- Ask for approval before sending
"""

        tools = [
            get_email_tool(),
            search_emails_tool(),
            send_email_tool(),
            web_search_tool(),
            read_url_tool()
        ]

        super().__init__(
            name="email_response",
            system_prompt=system_prompt,
            llm_client=llm_client,
            tools=tools
        )
```

#### 2.3 Research Agent

For gathering information to inform decisions:

```python
class ResearchAgent(Agent):
    """Agent specialized in gathering and synthesizing information."""

    def __init__(self, llm_client):
        system_prompt = """You are a research agent. Your job is to:
1. Understand the research question
2. Search for relevant information
3. Read and analyze sources
4. Synthesize findings into clear summary

Always cite sources and distinguish facts from inference.
"""

        tools = [
            web_search_tool(),
            read_url_tool(),
            search_emails_tool()  # Search past emails for context
        ]

        super().__init__(
            name="research",
            system_prompt=system_prompt,
            llm_client=llm_client,
            tools=tools
        )
```

---

### Phase 3: Agent Orchestration and Hierarchy

#### 3.1 Orchestrator Agent

Master agent that delegates to specialized sub-agents:

```python
class OrchestratorAgent(Agent):
    """Top-level agent that delegates to specialized agents."""

    def __init__(self, llm_client, sub_agents: Dict[str, Agent]):
        system_prompt = """You are an orchestrator agent. You manage specialized sub-agents:

{agent_list}

When given a task, you should:
1. Analyze what needs to be done
2. Delegate to appropriate sub-agents
3. Gather results from sub-agents
4. Synthesize final response

You can run multiple agents in parallel or sequence as needed.
"""

        self.sub_agents = sub_agents

        # Create delegation tools
        tools = [
            Tool(
                name=f"delegate_to_{name}",
                description=agent.system_prompt.split('\n')[0],  # First line as description
                parameters={
                    "type": "object",
                    "properties": {
                        "task": {"type": "string", "description": "Task for sub-agent"}
                    },
                    "required": ["task"]
                },
                function=lambda task, agent=agent: agent.run(task)
            )
            for name, agent in sub_agents.items()
        ]

        super().__init__(
            name="orchestrator",
            system_prompt=system_prompt.format(
                agent_list="\n".join([f"- {name}: {agent.name}" for name, agent in sub_agents.items()])
            ),
            llm_client=llm_client,
            tools=tools
        )
```

#### 3.2 Usage Example

```python
# Initialize specialized agents
email_triage = EmailTriageAgent(llm_client, gmail_client, config)
email_response = EmailResponseAgent(llm_client, gmail_client)
research = ResearchAgent(llm_client)

# Create orchestrator
orchestrator = OrchestratorAgent(
    llm_client=llm_client,
    sub_agents={
        "email_triage": email_triage,
        "email_response": email_response,
        "research": research
    }
)

# Complex task that requires multiple agents
result = orchestrator.run("""
Process my inbox and for any emails from my boss that require research,
gather the necessary information and draft appropriate responses.
""")
```

---

### Phase 4: Context Management and Memory

#### 4.1 Context Summarization

Implement automatic context compression:

```python
class ContextManager:
    """Manages agent context with automatic summarization."""

    def __init__(self, llm_client, max_tokens: int = 8000):
        self.llm_client = llm_client
        self.max_tokens = max_tokens
        self.compression_threshold = int(max_tokens * 0.8)

    def maybe_compress(self, context: List[Message]) -> List[Message]:
        """Compress context if approaching token limit."""
        current_tokens = self._estimate_tokens(context)

        if current_tokens < self.compression_threshold:
            return context

        # Keep system prompt and recent messages, summarize middle
        system_msg = context[0]
        recent_msgs = context[-10:]  # Keep last 10 messages
        middle_msgs = context[1:-10]

        summary = self._summarize_messages(middle_msgs)

        return [
            system_msg,
            Message(role="system", content=f"Previous conversation summary: {summary}"),
            *recent_msgs
        ]

    def _summarize_messages(self, messages: List[Message]) -> str:
        """Use LLM to summarize message history."""
        summary_prompt = """Summarize the following conversation in 3-5 sentences,
        focusing on key decisions, findings, and context that would be needed
        for future messages:

        {messages}
        """

        response = self.llm_client.chat([
            Message(role="user", content=summary_prompt.format(
                messages="\n\n".join([f"{m.role}: {m.content}" for m in messages])
            ))
        ])

        return response.content
```

#### 4.2 Persistent Memory

Add ability to remember across sessions:

```python
class AgentMemory:
    """Persistent storage for agent learnings."""

    def __init__(self, db_path: str):
        self.db = sqlite3.connect(db_path)
        self._init_schema()

    def remember(self, agent_name: str, key: str, value: str, context: str = None):
        """Store a memory for later retrieval."""
        self.db.execute("""
            INSERT INTO memories (agent_name, key, value, context, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (agent_name, key, value, context, datetime.now()))
        self.db.commit()

    def recall(self, agent_name: str, query: str, limit: int = 5) -> List[Dict]:
        """Retrieve relevant memories using similarity search."""
        # Use vector embeddings for semantic search
        # For now, simple keyword search
        cursor = self.db.execute("""
            SELECT key, value, context, created_at
            FROM memories
            WHERE agent_name = ?
            AND (key LIKE ? OR value LIKE ? OR context LIKE ?)
            ORDER BY created_at DESC
            LIMIT ?
        """, (agent_name, f"%{query}%", f"%{query}%", f"%{query}%", limit))

        return [
            {"key": row[0], "value": row[1], "context": row[2], "created_at": row[3]}
            for row in cursor.fetchall()
        ]
```

---

### Phase 5: Learning and Adaptation

#### 5.1 Feedback Loop

Learn from user corrections:

```python
class FeedbackTracker:
    """Tracks user corrections to agent decisions."""

    def __init__(self, db_path: str):
        self.db = sqlite3.connect(db_path)
        self._init_schema()

    def record_correction(
        self,
        agent_name: str,
        task_context: str,
        agent_decision: str,
        user_correction: str,
        reasoning: str = None
    ):
        """Record when user corrects agent decision."""
        self.db.execute("""
            INSERT INTO corrections
            (agent_name, task_context, agent_decision, user_correction, reasoning, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (agent_name, task_context, agent_decision, user_correction, reasoning, datetime.now()))
        self.db.commit()

    def get_relevant_corrections(self, agent_name: str, context: str) -> List[Dict]:
        """Retrieve similar past corrections."""
        # Find corrections with similar context
        cursor = self.db.execute("""
            SELECT task_context, agent_decision, user_correction, reasoning
            FROM corrections
            WHERE agent_name = ?
            AND task_context LIKE ?
            ORDER BY timestamp DESC
            LIMIT 5
        """, (agent_name, f"%{context}%"))

        return [
            {
                "context": row[0],
                "agent_decision": row[1],
                "user_correction": row[2],
                "reasoning": row[3]
            }
            for row in cursor.fetchall()
        ]

    def augment_system_prompt(self, base_prompt: str, agent_name: str, context: str) -> str:
        """Add relevant learnings to system prompt."""
        corrections = self.get_relevant_corrections(agent_name, context)

        if not corrections:
            return base_prompt

        learnings = "\n\nLearnings from past corrections:\n"
        for i, correction in enumerate(corrections, 1):
            learnings += f"""
{i}. Context: {correction['context']}
   Previous decision: {correction['agent_decision']}
   Correct decision: {correction['user_correction']}
   Reason: {correction['reasoning']}
"""

        return base_prompt + learnings
```

#### 5.2 Integration with Email Triage

```python
# In email triage workflow
feedback_tracker = FeedbackTracker("data/agent_feedback.db")

# When processing email
agent = EmailTriageAgent(llm_client, gmail_client, config)

# Augment system prompt with learnings
email_context = f"From: {email.sender}, Subject: {email.subject}"
agent.system_prompt = feedback_tracker.augment_system_prompt(
    agent.system_prompt,
    "email_triage",
    email_context
)

result = agent.run(f"Triage email: {email.id}")

# Later, if user corrects the label
def handle_label_correction(email_id: str, wrong_label: str, correct_label: str):
    email = gmail_client.get_message(email_id)
    feedback_tracker.record_correction(
        agent_name="email_triage",
        task_context=f"From: {email.sender}, Subject: {email.subject}, Body snippet: {email.snippet}",
        agent_decision=wrong_label,
        user_correction=correct_label,
        reasoning=None  # Could prompt user for reason
    )
```

---

## Implementation Roadmap

### Phase 1: Foundation (2-3 weeks)
- [ ] Implement core Agent base class with tool calling
- [ ] Update LLM client to support function calling
- [ ] Create tool registry for Gmail operations
- [ ] Build basic EmailTriageAgent using new framework
- [ ] Ensure feature parity with current implementation
- [ ] Add comprehensive tests

### Phase 2: Specialization (2-3 weeks)
- [ ] Implement EmailResponseAgent for drafting replies
- [ ] Implement ResearchAgent for information gathering
- [ ] Add web search and URL fetching tools
- [ ] Create agent-specific configuration
- [ ] Build CLI commands for each agent

### Phase 3: Orchestration (2-3 weeks)
- [ ] Implement OrchestratorAgent for delegation
- [ ] Add inter-agent communication
- [ ] Build task routing logic
- [ ] Support parallel agent execution
- [ ] Add visualization/monitoring

### Phase 4: Memory & Context (2-3 weeks)
- [ ] Implement ContextManager with auto-compression
- [ ] Add AgentMemory with SQLite backend
- [ ] Build memory retrieval and injection
- [ ] Add context summarization tools
- [ ] Optimize token usage

### Phase 5: Learning (2-3 weeks)
- [ ] Implement FeedbackTracker
- [ ] Build correction recording UI/CLI
- [ ] Add prompt augmentation with learnings
- [ ] Implement similarity-based retrieval
- [ ] Add analytics dashboard

### Phase 6: Production Hardening (2-3 weeks)
- [ ] Add comprehensive error handling
- [ ] Implement rate limiting and quotas
- [ ] Add monitoring and observability
- [ ] Create deployment automation
- [ ] Write user documentation

---

## Technical Considerations

### 1. Token Budget Management

Each agent needs careful token management:

```python
class TokenBudget:
    """Manages token allocation for agent operations."""

    def __init__(self, max_tokens: int = 8000):
        self.max_tokens = max_tokens
        self.allocations = {
            "system_prompt": 0.15,      # 15% for system prompt
            "conversation": 0.50,        # 50% for conversation history
            "tool_results": 0.25,        # 25% for tool outputs
            "response_buffer": 0.10      # 10% reserved for response
        }

    def get_allocation(self, category: str) -> int:
        return int(self.max_tokens * self.allocations[category])

    def truncate_if_needed(self, content: str, category: str) -> str:
        max_tokens = self.get_allocation(category)
        # Rough estimate: 1 token ≈ 4 characters
        max_chars = max_tokens * 4

        if len(content) <= max_chars:
            return content

        return content[:max_chars] + "...[truncated]"
```

### 2. Provider Compatibility

Ensure all LLM providers support function calling:

| Provider | Function Calling | Notes |
|----------|-----------------|-------|
| OpenAI GPT-4 | ✅ Full support | Reference implementation |
| Anthropic Claude | ✅ Tool use | Different format, need adapter |
| Local MLX | ⚠️ Depends on model | Need function-calling fine-tuned model |
| Ollama | ⚠️ Depends on model | Some models support it |

**Recommendation:** Add provider-specific adapters in `src/integrations/llm_client.py`

### 3. Local LLM Requirements

For true local operation with function calling:

- **Recommended Models:**
  - `mlx-community/Hermes-3-Llama-3.1-8B-4bit` (function calling support)
  - `NousResearch/Hermes-3-Llama-3.1-8B` (via Ollama)

- **Fallback Strategy:**
  - If local model doesn't support function calling, use ReAct prompting pattern
  - Parse tool calls from text responses (less reliable but works)

### 4. Error Handling and Recovery

Agents need robust error handling:

```python
class ResilientAgent(Agent):
    """Agent with automatic error recovery."""

    def run(self, user_input: str) -> str:
        max_retries = 3

        for attempt in range(max_retries):
            try:
                return super().run(user_input)
            except ToolExecutionError as e:
                logger.warning(f"Tool error on attempt {attempt + 1}: {e}")

                # Add error context to conversation
                self.context.append(Message(
                    role="system",
                    content=f"The previous tool call failed with error: {e}. Please try a different approach."
                ))

                if attempt == max_retries - 1:
                    raise
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                raise

        raise Exception("Agent failed after max retries")
```

### 5. Privacy and Security

Maintain local-first privacy guarantees:

- **Data Residency:** All email content processed locally or via controlled servers
- **LLM Privacy:** Prefer local inference; if using cloud LLM, implement content filtering
- **Memory Storage:** Encrypt sensitive data in SQLite databases
- **Audit Logging:** Track all agent actions for transparency

---

## Migration Strategy

### Step 1: Parallel Implementation

- Keep existing `email_triage.py` working
- Build new agent framework alongside
- Create `email_triage_agent.py` using new framework
- Run both, compare results

### Step 2: Feature Flag

Add configuration to switch between old and new:

```python
# In config
USE_AGENT_FRAMEWORK = os.getenv("USE_AGENT_FRAMEWORK", "false").lower() == "true"

if USE_AGENT_FRAMEWORK:
    from src.agents.email_triage_agent import EmailTriageAgent
    agent = EmailTriageAgent(llm_client, gmail_client, config)
    agent.process_inbox(num_messages)
else:
    from src.workflows.email_triage import run_email_triage
    run_email_triage(num_messages)
```

### Step 3: Gradual Rollout

1. **Week 1-2:** Test agent framework with dry-run mode
2. **Week 3-4:** Enable for 10% of emails
3. **Week 5-6:** Enable for 50% of emails
4. **Week 7-8:** Full migration, deprecate old code

---

## Success Metrics

### Quantitative Metrics

- **Accuracy:** Classification accuracy vs current system (target: ≥95%)
- **Autonomy:** % of tasks completed without human intervention (target: >80%)
- **Efficiency:** Average tokens per task (target: <2000)
- **Latency:** Time to complete task (target: <5 seconds for email triage)
- **Reliability:** Success rate for tool calls (target: >99%)

### Qualitative Metrics

- **Flexibility:** Can handle tasks beyond initial design?
- **Explainability:** Can users understand agent reasoning?
- **Control:** Can users effectively guide agent behavior?
- **Trust:** Do users feel comfortable with agent autonomy?

---

## Open Questions and Experiments

Following the Fly.io article's advice that "nobody knows anything yet," here are experiments to run:

### Experiment 1: Tool Calling vs ReAct Prompting

**Question:** Is native function calling better than ReAct-style text parsing?

**Setup:**
- Implement same agent with both approaches
- Compare accuracy, token usage, latency
- Test with local models that don't support function calling

### Experiment 2: Context Summarization Strategies

**Question:** What's the optimal summarization strategy for long conversations?

**Options:**
- Rolling summarization (summarize every N messages)
- Hierarchical summarization (summary of summaries)
- Selective retention (keep important messages, summarize rest)
- Embedding-based retrieval (RAG for conversation history)

### Experiment 3: Agent Hierarchy Depth

**Question:** How many layers of agents are optimal?

**Setup:**
- Test flat structure (no orchestrator)
- Test 2-layer (orchestrator + specialists)
- Test 3-layer (orchestrator + coordinators + specialists)
- Measure complexity, performance, token usage

### Experiment 4: Memory Retrieval Methods

**Question:** How to best retrieve relevant memories?

**Options:**
- Keyword search (simple, fast)
- Embedding similarity (semantic, slower)
- Hybrid (keywords + embeddings)
- Temporal decay (recent memories weighted higher)

### Experiment 5: Learning from Feedback

**Question:** How to effectively incorporate user corrections?

**Approaches:**
- Prompt injection (add examples to system prompt)
- Few-shot learning (add to context as examples)
- Fine-tuning (periodically fine-tune local model)
- Rule synthesis (convert corrections to deterministic rules)

---

## Conclusion

The automation-platform is perfectly positioned to evolve from a single-purpose email classifier into a sophisticated multi-agent system. By following principles from the Fly.io article, we can:

1. **Build our own agent framework** optimized for our needs (privacy, local-first)
2. **Maintain simplicity** through clean abstractions (Agent, Tool, Context)
3. **Enable experimentation** by making architectural decisions explicit
4. **Scale capabilities** through agent specialization and hierarchy
5. **Learn and improve** through feedback loops and memory

The proposed architecture preserves everything good about the current system (modular design, deterministic rules, local LLM integration) while unlocking new capabilities:

- **Autonomous email responses** (not just classification)
- **Multi-step reasoning** (research → draft → review → send)
- **Task delegation** (orchestrator manages specialists)
- **Continuous learning** (improves from feedback)
- **Extensibility** (easy to add new agent types and tools)

Most importantly, building our own agent framework gives us **control and ownership** over the decision-making logic, allowing us to optimize for our specific requirements (privacy, cost, latency, accuracy) in ways that generic platforms cannot.

---

## Next Steps

1. **Review this proposal** with stakeholders
2. **Prioritize experiments** from Open Questions section
3. **Start Phase 1 implementation** with feature flag
4. **Run parallel A/B test** (old system vs new agent framework)
5. **Iterate based on findings**

The journey from automation scripts to autonomous agents is incremental — we can move forward step by step while maintaining a working system at each stage.
