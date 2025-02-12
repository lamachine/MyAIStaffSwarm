# To-Do List & Action Items

Below is a categorized and prioritized list of action items. These tasks can be later transferred to Google Tasks.

---

## Priority 1: Critical / Immediate Actions
- [ ] **Build Household Assistant Staff**  
  **Category:** Agents  
  **Details:** Define and implement agent roles using standardized Pydantic models for James (Butler/Orchestrator), Rose (Personal Assistant), Dive Master (Health & Fitness Coach), and Fr. Zoph (Librarian/Researcher).

- [ ] **Test Open WebUI with Webhook**  
  **Category:** Integration / UI  
  **Details:** Verify that Open WebUI successfully calls the FastAPI webhook endpoint (`/webhook`) and processes responses.

- [ ] **Verify RAG Pipeline Output**  
  **Category:** Processing Pipeline  
  **Details:** Programmatically send the top 5 results from the RAG system to the LLM and check output consistency.

---

## Priority 2: Important Enhancements & Integrations
- [ ] **Implement Langgraph and Langchain Integration**  
  **Category:** Tools / LLM Integration  
  **Details:** Evaluate making these available as Python plugins; determine integration feasibility with N8N.

- [ ] **Develop Graph State Management**  
  **Category:** Processing Pipeline / Context Management  
  **Details:** Create graphState, nodes, and edges to manage message stacking and maintain context without overflowing the window.

- [ ] **Set Up Loader for Docs into RAG**  
  **Category:** Processing Pipeline  
  **Details:** Utilize Langchain's directory loader to efficiently pull documentation into the RAG system.

- [ ] **Explore Chroma for Vector Database**  
  **Category:** Data Storage  
  **Details:** Test Chroma as an in-memory vector database alternative.

- [ ] **Retrieve Agent Personalities**  
  **Category:** Agents / Documentation  
  **Details:** Source and integrate personality traits from the tutorial guy to refine agent characterization.

- [ ] **Standardize API Documentation for Tools**  
  **Category:** Tools / Documentation  
  **Details:** Create machine-readable documents (e.g., based on Google Discovery Documents) for building and integrating new API tools.

- [ ] **Add Grafana Loki to the Development Environment**  
  **Category:** Infrastructure  
  **Details:** Integrate Grafana Loki for improved log management in the development environment.

- [ ] **Find Best Tools for Research (Perplexity, Google, etc.)**  
  **Category:** Research / Tools  
  **Details:** Evaluate and select the best available tools for research tasks and integration with the system.

- [ ] **Evaluate MDC Approach**  
  **Category:** Documentation / Strategy  
  **Details:** Investigate what MDC is and determine if following that path is advantageous for the project.

- [ ] **Review Data Storage Plan**  
  **Category:** Data Storage / Documentation  
  **Details:** Thoroughly review and refine the current data storage strategy to ensure it meets project needs.

- [ ] **Scrub Other Packages for Tools and Templates**  
  **Category:** Tools / Maintenance  
  **Details:** Evaluate and clean up existing packages for tools and templates to streamline the system.

- [ ] **Prepare the Action Plan**  
  **Category:** Project Planning  
  **Details:** Develop a detailed action plan outlining next steps, milestones, and responsibilities.

- [ ] **Integrate and Consolidate AgentSwarmModular Plans**  
  **Category:** Agents / Integration  
  **Details:** Merge and harmonize the various AgentSwarmModular planning documents into a unified plan.

- [ ] **Add Database Table for Agent Personalities**  
  **Category:** Data Storage  
  **Details:** Design and implement a database table to store agent personality configurations.

- [ ] **Add Database Table for Tools**  
  **Category:** Data Storage  
  **Details:** Define and create a database table to manage tool configurations and metadata.

---

## Priority 3: Enhancements & Future Features
- [ ] **UI Enhancements for Chat and Dashboard**  
  **Category:** UI  
  **Details:**  
  - Add dropdowns in the chat window for selecting model providers and RAG folder options.  
  - Include checkboxes for model selection.  
  - Implement a cut-and-paste window for session notes (savable to RAG).  
  - Build a dashboard to display funds/costs, hot emails, and human-in-the-loop notifications.

- [ ] **Transition to Enhanced Voice Interfaces**  
  **Category:** UI / Voice Tools  
  **Details:**  
  - Start with Open WebUI basic voice.  
  - Move to using 11 Lab voices for more realistic output.

- [ ] **Extend Support for Multiple Agents**  
  **Category:** Agents / Integration  
  **Details:** Modify the Open WebUI Pipe Function and underlying infrastructure to support multiple simultaneous agents.

- [ ] **Explore Distributed AI via Petals**  
  **Category:** Tools / Infrastructure  
  **Details:** Investigate using Petals to distribute AI requests across machines and leverage GPU resources.

- [ ] **Look into Screen Control Software**  
  **Category:** UI / Tools  
  **Details:** Research and evaluate software solutions for screen control automation.

- [ ] **Add Legal Advisor Agent Barrister Crouch**  
  **Category:** Agents  
  **Details:** Introduce a legal advisor agent (Barrister Crouch from Duck, Crouch, and Hyde, Esquires) to support legal and compliance matters.

- [ ] **Add Review Will and Trust**  
  **Category:** Agents / Legal  
  **Details:** Establish a process for reviewing and managing will and trust documentation.

- [ ] **Create New Ideas List**  
  **Category:** Project Planning / Innovation  
  **Details:** Compile a list of new ideas and potential features to explore in future iterations.

## Unresolved Key Questions
- [ ] Clarify the optimal configuration for agent communication channels (e.g., defaulting to JSON/Pydantic vs. alternative protocols).
- [ ] Research secure communication mechanisms for agents (authentication methods, encryption standards, etc.).
- [ ] Define a robust agent state persistence strategy and synchronization process within Supabase.
- [ ] Develop a reconciliation process for integrating local versus cloud-based LLM providers.
- [ ] Further specify integration points and responsibilities for specialized agents (e.g., Memory Agent, Orchestrator, LLM Interface).

*End of To-Do List & Action Items*

