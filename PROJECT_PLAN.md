# PROJECT PLAN

## 1. Introduction
This project builds an integrated personal assistance program with advanced agentic capabilities designed to support a wide spectrum of needs—from managing my personal affairs and developing new agentic functionalities to providing assistance for third parties such as my wife, children, and business mentors. Central to the system is a team of household assistants led by James, acting as the butler and house manager, who coordinates tasks, manages tools, and serves as the primary point of contact. Additional specialized roles include a Personal Coach, responsible for monitoring health, fitness, and overall well-being, and an AI Engineer, who assists in all aspects of code creation and modification. The design emphasizes modularity, scalability, security, and adaptability to both personal and professional applications.

## 2. Agents
This section outlines the multi-agent architecture along with the specific roles and priorities of the primary household assistants.

**Best Practices for Agents:**
- **Separation of Concerns:** Each agent must have a clear, independent role.
- **Loose Coupling:** Agents should communicate through standardized protocols (e.g., JSON messages) while managing independent states.
- **Scalability:** Ensure agents are modular and easily extendable.

### Agent Roles and Priorities

**Priority 1:**
1. **James**
   - **Character/Role:** Butler and Staff Manager
   - **Swarm Role:** Orchestrator
   - **Responsibilities:** Coordinates tasks, manages tools, and serves as the primary point of contact. (First priority for programming)

**Priority 2:**
1. **Rose**
   - **Character/Role:** Personal Assistant and Communications Specialist
   - **Responsibilities:** Handles email, calendar, social media, and general communication tasks.
2. **Dive Master**
   - **Character/Role:** Health and Fitness Coach
   - **Responsibilities:** Tracks health-related metrics, provides daily consultations on personal wellness, and monitors fitness progress.
3. **Fr. Zoph**
   - **Character/Role:** Librarian and Researcher
   - **Responsibilities:** Manages research tasks, handles Retrieval Augmented Generation (RAG) functions, and oversees documentation and data curation.
4. **Support Agents**
   - **Examples:** Security Agent, Memory Agent, etc., which operate in the background to maintain system security and context management.

**Priority 3:**
1. **Accountant Character**
   - **Responsibilities:** Manages budgeting, financial tracking, and administrative accounting tasks.
2. **Tutor/Assistant Character for My Boys**
   - **Responsibilities:** Provides educational support and tutoring for my children.
3. **House Artist Character**
   - **Responsibilities:** Generates creative images and media content on demand.
4. **Web Consultant**
   - **Responsibilities:** Advises on media strategy, leverages popular platforms, and engages with support communities.

## 2.x Standardized Agent Format Example
The following Pydantic model demonstrates a standardized format for representing an agent configuration:

```python
from pydantic import BaseModel, Field
from typing import List, Optional

class Agent(BaseModel):
    name: str = Field(..., description="Name of the agent")
    character_role: str = Field(..., description="The role or character of the agent")
    swarm_role: Optional[str] = Field(None, description="Agent's role within the swarm, if applicable")
    responsibilities: List[str] = Field(..., description="List of responsibilities")
    priority: int = Field(..., description="Priority ranking (lower number means higher priority)")

# Example for James:
james = Agent(
    name="James",
    character_role="Butler and Staff Manager",
    swarm_role="Orchestrator",
    responsibilities=[
        "Coordinates tasks",
        "Manages tools",
        "Serves as primary contact"
    ],
    priority=1
)
```

Use this template to create validated configuration objects for all agents.

## 3. Tools
This section details the assortment of utility tools integrated into the program.

**Best Practices for Tools:**
- **Clear Separation:** Tools should provide specialized functionality independent of agent logic.
- **Reusability:** Design tools as modular, standalone components that can be reused across various tasks.
- **Interface Consistency:** Ensure standardized input/output formats (preferably using Pydantic models) for seamless integration.

### Tool Categories
To prevent overwhelming either the agent or the human user, tools are organized into distinct categories:

- **Google Suite Tools:** Tools for email, calendar, document editing, and related cloud productivity tasks. Examples include dedicated API clients for Gmail, Calendar, Docs, Sheets, Slides, and Drive.
- **LLM Tools:** Interfaces for integrating with various language model providers, covering both local (e.g., Ollama) and cloud-based APIs (e.g., OpenAI, Anthropic).
- **Browser Control Tools:** Automation utilities for controlling and automating web browser tasks such as navigation, content extraction, and interaction.
- **Local Program Control Tools:** Tools to manage and automate local application workflows and system processes.
- **Voice Tools:** Components for speech-to-text, text-to-speech, and voice command processing.
- **File Tools:** Utilities for file management, conversion, editing, and formatting.

## 3.x Standardized Tool Format Example
The following Pydantic model demonstrates a standardized format for representing a tool configuration:

```python
from pydantic import BaseModel, Field
from typing import List

class Tool(BaseModel):
    name: str = Field(..., description="Tool name")
    category: str = Field(..., description="Tool category (e.g., 'Google Suite Tools')")
    description: str = Field(..., description="Brief description of the tool functionality")
    interfaces: List[str] = Field(..., description="Supported interfaces (e.g., API, CLI)")
    version: str = Field(default="1.0", description="Tool version")

# Example for a Gmail API tool:
gmail_client = Tool(
    name="Gmail API Client",
    category="Google Suite Tools",
    description="Handles email functions via Gmail API",
    interfaces=["REST", "Pydantic"],
    version="1.0"
)
```

Use this template to define validated configuration objects for all integrated tools.

## 4. UI
This section covers the user interface components of the system.

**Best Practices for UI:**
- **User-Centric Design:** Create interfaces (web UI, CLI, etc.) that are intuitive, accessible, and tailored to the needs of end users.
- **Clear Separation:** Isolate UI logic from core processing and agent functionalities to simplify maintenance and future redesigns.
- **Responsiveness:** Ensure that the interfaces accommodate different platforms with consistent interaction patterns.

## 5. Programming Objectives
This section outlines the overarching programming objectives to guide the design and development of the system:

- **Modular Architecture:** Build a well-separated system by partitioning functionalities into distinct layers for crawling, processing, storage, API management, and agent swarm operations.
- **Flexible Integration:** Support multiple LLM providers (with a default focus on Ollama using LLama 3.1 and nomic-embed-text) and allow for easy swapping of databases and other integrations.
- **Dual UIs:** Develop both a custom web UI and a command-line interface (CLI) to facilitate testing, development, and end-user interaction.
- **Robust Processing:** Implement source-specific crawlers combined with a common processing pipeline that handles text chunking, summarization, and embedding generation, ensuring efficient data handling and storage.
- **Agent Swarm:** Orchestrate a diverse set of specialized agents (e.g., Jarvis as the orchestrator, Research, Memory, etc.) using standardized communication protocols and independent responsibilities.

**Optional Advanced Integration:**  
- **Model Context Protocol (MCP):**  
  Design the system in a modular fashion so that MCP functionality can be layered in as an optional connector module. Begin with the current JSON/Pydantic communication schema; later, if needed, MCP can be added without impacting core development.

  Example MCP connector using Pydantic:

  ```python
  from pydantic import BaseModel, Field
  from datetime import datetime

  class MCPMessage(BaseModel):
      id: str = Field(..., description="Unique message ID")
      timestamp: datetime = Field(default_factory=datetime.utcnow, description="Message sent time")
      sender: str = Field(..., description="Identifier of the sender (agent or system)")
      receiver: str = Field(..., description="Identifier of the receiver (agent or system)")
      payload: dict = Field(default_factory=dict, description="Structured payload per MCP specifications")

  # Example usage:
  example_msg = MCPMessage(
      id="msg-001",
      sender="agent_orchestrator",
      receiver="data_connector",
      payload={"action": "fetch_data", "params": {"collection": "sales_data"}}
  )
  print(example_msg.json(indent=2))
  ```

  **Rationale:** This approach lets you maintain a clear separation between core functionality and advanced, optional protocols while keeping the development process lean. MCP integration can be added later as the project matures.

## 6. Environment Setup
- **Python & Venv:** All development is done in Python inside a dedicated virtual environment.
- **Git:** Version control is mandatory with semantic versioning and regular backups.
- **Containers:** Docker is used for core services:
  - Local Supabase (with Postgres, RLS, and storage)
  - Local hosted Ollama image
  - Monitoring stack (Grafana, Prometheus)
- **Cloud & Tunnels:** Cloudflared is configured to expose services via free tunnels.

## 7. Architecture Overview

### 7.1. Core Modules
- **FastAPI Server:**  
  - Central API gateway handling dependency injection, error handling, and state management.
  - Serves as the entry-point for both the UI and sub-tool interfaces.
- **Crawler Modules:**  
  - Separate crawlers for documentation (`src/crawler/docs`), repositories (`src/crawler/repos`), and media.
- **Processing Pipeline:**  
  - Raw content processing (HTML to markdown conversion, link extraction).
  - Common operations: text chunking, title/summary extraction, embedding generation.
- **Storage Management:**  
  - Supabase is used for persistent storage. See [DataStorage.md](./DataStorage.md) for detailed data modeling and caching strategies.

### 7.2. Agent Swarm Architecture
- **Overview:**  
  - Multiple agents with specialized roles (Orchestrator, Research, Memory, etc.) collaborate to distribute workload and maintain system state.
- **Documentation & Specs:**  
  - Use the following subfiles in `AgentSwarmModularPlanning/` for detailed agent configuration and communication guidelines:  
      - [AgentPlan.txt](./AgentSwarmModularPlanning/AgentPlan.txt)  
      - [AgentSwarmPlanJarvis1.txt](./AgentSwarmModularPlanning/AgentSwarmPlanJarvis1.txt)  
      - [AgentSwarm_comms.txt](./AgentSwarmModularPlanning/AgentSwarm_comms.txt)
- **Communication Protocols:**  
  - Standard JSON message schema with required fields (id, timestamp, sender, receiver, type, payload, control).
  - Support for synchronous (API) and asynchronous (message queues/event buses) interactions.

## 8. Processing Pipeline
- **Steps:**
  1. **Content Retrieval:** Crawlers fetch source-specific raw content.
  2. **Preprocessing:** HTML cleaning, link discovery, and conversion to `RawContent`.
  3. **Text Processing:** Chunking, title and summary extraction, and embedding generation.
  4. **Persistence:** Batching and upsert operations into Supabase with efficient indexing.
- **Diagram:**  
  ```
  [Source Crawlers] -> RawContent -> [Chunking] -> [LLM Processing] -> [Storage]
  ```
- Detailed pipeline specs and enhancements are described in [Project Status.md](./Project%20Status.md).

## 9. Data Storage & Management
- **Database:**  
  - Primary storage via Supabase with secure, real-time subscriptions.
  - Row Level Security (RLS) policies and environment-based configurations.
- **Caching:**  
  - Employ Redis (or in-memory caching) to optimize I/O and reduce latency.
- **Documentation:**  
  - See [DataStorage.md](./DataStorage.md) for comprehensive data schema, indexing strategies, and backup procedures.

## 10. Testing, Documentation & Security
- **Testing Guidelines:**  
  - Unit tests for utility functions/hooks.
  - Integration tests for API and component interactions.
  - End-to-end tests for critical flows.
  - Detailed instructions and test cases are captured in the [testanddocsrules.mdc](./testanddocsrules.mdc).
- **Security Measures:**  
  - Environment variable management for secrets.
  - Rate limiting, input sanitization, and strict authentication/authorization (using Supabase Auth and JWT).
- **Documentation:**  
  - Maintain living documentation (Swagger UI, JupyterBook) and use Notion for project tracking.

## 11. Versioning, Deployment & Logging
- **Version Control:**  
  - Always use Git with commits tracking major changes (remember to tag releases).
- **Deployment:**  
  - Docker Compose is used to orchestrate containerized services.
  - Separate containers for primary services (Ollama, Supabase, FastAPI, etc.) to enable scaling and isolation.
- **Logging & Monitoring:**  
  - Structured logging (e.g., Logfire) is integrated.
  - Monitoring via Prometheus/Grafana.
- **Change Management:**  
  - Use of CHANGELOG.md to track version changes and backward compatibility issues.

## 12. Next Steps & Roadmap
- **Short Term:**  
  - Finalize connection and communication between crawlers, processing pipeline, and FastAPI server.
  - Implement and test Agent Swarm communications and task lifecycle management (refer to [AgentSwarm_TaskLifecycle.txt](./AgentSwarmModularPlanning/AgentSwarm_TaskLifecycle.txt)).
  - Set up CI/CD pipelines for automated testing and deployment.
- **Medium Term:**  
  - Expand agent features including personality, context handling, and dynamic task allocation.
  - Optimize storage efficiency and caching for scalable throughput.
- **Long Term:**  
  - Integrate multi-modal interfaces (voice, web UI, CLI).
  - Incorporate additional LLM providers and expand API integrations.
  - Scale horizontally based on demand with auto-scaling of containers.

## 13. References & Detailed Documentation
- **Project Status:** [Project Status.md](./Project%20Status.md)
- **Agent Swarm Details:** See the entire folder `AgentSwarmModularPlanning/` for comprehensive design, communications, task lifecycle, and integration guides.
- **Data Storage:** [DataStorage.md](./DataStorage.md)
- **Testing & Documentation Guidelines:** [testanddocsrules.mdc](./testanddocsrules.mdc)
- **General Project & Environment Rules:** [CursorProjectRules.md](./CursorProjectRules.md) and [CursorRulesForAI.md](./CursorRulesForAI.md)

## 12. To-Do List & Action Items

Below is a categorized and prioritized list of action items. Each item includes a check box for status tracking.

### Priority 1: Critical / Immediate Actions
- [ ] **Build Household Assistant Staff**
  - **Category:** Agents
  - **Details:** Define and implement agent roles using standardized Pydantic models for James (Butler/Orchestrator), Rose (Personal Assistant), Dive Master (Health & Fitness Coach), and Fr. Zoph (Librarian/Researcher).
- [ ] **Test Open WebUI with Webhook**
  - **Category:** Integration / UI
  - **Details:** Verify that Open WebUI successfully calls the FastAPI webhook endpoint (/webhook) and processes responses.
- [ ] **Verify RAG Pipeline Output**
  - **Category:** Processing Pipeline
  - **Details:** Programmatically send the top 5 results from the RAG system to the LLM and check output consistency.
  
### Priority 2: Important Enhancements & Integrations
- [ ] **Implement Langgraph and Langchain Integration**
  - **Category:** Tools / LLM Integration
  - **Details:** Evaluate making these available as Python plugins; determine integration feasibility with N8N.
- [ ] **Develop Graph State Management**
  - **Category:** Processing Pipeline / Context Management
  - **Details:** Create graphState, nodes, and edges to manage message stacking and maintain context without overflowing the window.
- [ ] **Set Up Loader for Docs into RAG**
  - **Category:** Processing Pipeline
  - **Details:** Utilize Langchain's directory loader to efficiently pull documentation into the RAG system.
- [ ] **Explore Chroma for Vector Database**
  - **Category:** Data Storage
  - **Details:** Test Chroma as an in-memory vector database alternative.
- [ ] **Retrieve Agent Personalities**
  - **Category:** Agents / Documentation
  - **Details:** Source and integrate personality traits from the tutorial guy to refine agent characterization.
- [ ] **Standardize API Documentation for Tools**
  - **Category:** Tools / Documentation
  - **Details:** Create machine-readable documents (e.g., based on Google Discovery Documents) for building and integrating new API tools.

### Priority 3: Enhancements & Future Features
- [ ] **UI Enhancements for Chat and Dashboard**
  - **Category:** UI
  - **Details:** 
    - Add dropdowns in the chat window for selecting model providers and RAG folder options.
    - Include checkboxes for model selection.
    - Implement a cut-and-paste window for session notes (savable to RAG).
    - Build a dashboard to display funds/costs, hot emails, and human-in-the-loop notifications.
- [ ] **Transition to Enhanced Voice Interfaces**
  - **Category:** UI / Voice Tools
  - **Details:** 
    - Start with Open WebUI basic voice.
    - Move to using 11 Lab voices for more realistic output.
- [ ] **Extend Support for Multiple Agents**
  - **Category:** Agents / Integration
  - **Details:** Modify the Open WebUI Pipe Function and underlying infrastructure to support multiple simultaneous agents.
- [ ] **Explore Distributed AI via Petals**
  - **Category:** Tools / Infrastructure
  - **Details:** Investigate using Petals to distribute AI requests across machines and leverage GPU resources.

---

This document provides a high-level roadmap. Each section outlines core components and interfaces; detailed implementation steps and auxiliary documents reside in their respective sub-files. Updates should be version-controlled and meticulously documented.

*End of Project Plan*
