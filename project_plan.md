# Autonomous Agent Project Plan

## 1. Project Overview

Chleo Lite is a planning lab for a small autonomous agent that helps a fictional Mallorca real estate agency qualify incoming buyer leads. The goal is to structure the inquiry, check missing information, retrieve relevant fictional property data, and support a human sales review before any customer communication happens.

### 1.1 Use Case
Chleo receives a natural-language inquiry from a potential buyer and turns it into a structured lead. It extracts the most important buying signals, checks whether the lead is complete, searches a fictional property catalogue, and prepares a recommendation for the sales team.

### 1.2 Problem Statement
The agency currently reviews every inquiry manually. This takes time, creates inconsistent answers, and makes it harder to respond quickly when leads arrive outside business hours. The planning problem is to design a small agent that reduces manual effort while keeping clear human control.

### 1.3 Target Users
The main users are:
- Small real estate sales agents
- The agency manager
- Administrative staff who receive or triage inquiries

Indirect users are the potential buyers who submit the initial inquiry.

### 1.4 Current Manual Process
Today, a staff member reads the inquiry, tries to understand what the buyer wants, asks follow-up questions if details are missing, checks available properties, estimates how serious the lead is, and then records the result for later follow-up. This process depends heavily on staff availability and personal judgment.

### 1.5 Project Objective
The objective is to plan a lightweight autonomous workflow that can help with lead qualification in a transparent and safe way. The future prototype should show how the agent could extract lead information, retrieve property matches, score the lead, and pause for human approval.

### 1.6 Success Criteria
The plan is successful if it:
- Clearly defines the lead qualification workflow
- Uses only fictional data and no real customer information
- Explains how the agent supports, but does not replace, the sales team
- Produces a small MVP scope that is realistic for a student lab
- Identifies technical, business, and privacy risks with mitigation ideas

## 2. Technology Selection Framework

The stack is chosen for transparency, local development, and a simple future path from planning to prototype. The main goal is not to build a production system yet, but to show how the components could work together.

### 2.1 External Knowledge
The external knowledge source will be a fictional property catalogue. Each listing can be represented as a searchable document with structured metadata such as location, property type, price, bedrooms, bathrooms, features, and availability status.

### 2.2 External Systems
In later stages, the agent may connect to a form, email inbox, CRM, or n8n workflow. For this lab, those integrations stay conceptual only. No external system should be called during the planning phase.

### 2.3 Multi-Step Reasoning
The lead qualification task needs multiple steps because the agent must first extract facts, then check completeness, then search property matches, and finally score the lead. LangGraph is a good fit because it supports conditional routing and visible workflow steps.

### 2.4 Business-System Integration
The planned agent supports business operations by converting messy inquiries into structured lead records. That makes it easier for the sales team to decide what to do next and reduces the time spent on repetitive reading and sorting.

### 2.5 Autonomous Execution
The agent should be autonomous only in the parts that are low risk and repetitive, such as extracting fields, checking missing information, ranking property matches, and preparing a draft recommendation. Human review remains required before any outward action.

### 2.6 Selected Technology Stack
The proposed stack is:
- OpenAI chat model for reasoning and text handling
- LangChain for prompt handling and retrieval building blocks
- LangGraph for the stateful workflow
- OpenAI embeddings for semantic property representation
- Chroma for a local vector database
- Streamlit for a simple prototype interface
- n8n for future orchestration
- Pydantic for data validation
- pytest for automated tests
- python-dotenv for local configuration

This stack fits the lab because it is small, testable, and common in Python-based AI projects.

### 2.7 Alternatives Considered
Alternative options include:
- A fully rule-based system with no LLM, which would be simpler but less flexible for natural-language inquiries
- A direct database search only, which would miss semantic understanding of buyer intent
- A more complex production stack with CRM integration, which is unnecessary for this lab

### 2.8 Trade-offs
The main trade-off is between flexibility and control. LLM-based extraction can handle messy input better, but it also introduces cost, latency, and the risk of errors. Using a local vector database and rule-based scoring keeps the system more transparent, but it limits scale and sophistication.

## 3. MVP Scope

The MVP should prove that the agent can support lead qualification in a controlled and understandable way. It should stay small enough to finish in a lab setting.

### 3.1 Feature Brainstorm
Possible features include inquiry extraction, completeness checks, follow-up questions, property retrieval, scoring, classification, human review, Streamlit output, and future integration with n8n or a CRM.

### 3.2 Must-Have Features
- Process one inquiry at a time
- Handle English-language inquiries
- Extract the six required lead fields
- Detect missing information
- Ask one follow-up question when needed
- Retrieve relevant fictional properties
- Score the lead with transparent rules
- Classify the lead as hot, warm, or cold
- Pause for human review

### 3.3 Should-Have Features
- Show the result in a simple Streamlit interface
- Include basic error handling
- Provide local execution only
- Add tests for scoring and routing
- Keep the reasoning steps visible to the user

### 3.4 Nice-to-Have Features
- Better property filtering
- Conversation memory
- Staff notifications
- n8n workflow export
- Feedback collection

### 3.5 Included in the MVP
The MVP includes structured lead extraction, completeness validation, one follow-up question, retrieval from fictional property JSON data, rule-based scoring, hot/warm/cold classification, human review, and a simple local prototype view.

### 3.6 Out of Scope
The MVP excludes real deployment, CRM integration, email automation, WhatsApp support, multilingual conversations, voice, images, mortgage advice, legal advice, property valuation, production authentication, analytics dashboards, and self-learning behavior.

### 3.7 Human-in-the-Loop Boundaries
Human approval is required before any customer-facing action. The agent must not contact a real lead, promise availability, make financial claims, or decide on financing. It may prepare suggestions only.

### 3.8 Assumptions
- All data in the lab is fictional
- The first version handles a single inquiry at a time
- The first version works in English only
- Property availability is a sample dataset, not a live feed
- The user will review any action that leaves the agent

## 4. Risk Assessment

The main risks are not only technical. They also include trust, privacy, cost, and business misuse. The table below captures the most relevant risks for the lab.

| Risk ID | Category | Risk description | Probability | Impact | Mitigation | Contingency |
|---|---|---|---|---|---|---|
| R1 | Technical | Hallucinated property details | Medium | High | Use structured property data and retrieval grounding | Show only verified listing fields and require human review |
| R2 | Data | Outdated availability information | Medium | High | Mark data as fictional sample data and separate it from live data | Treat all availability as draft-only until manual confirmation |
| R3 | Technical | Incorrect field extraction | Medium | Medium | Define clear schemas and test extraction cases | Add manual correction before qualification is sent forward |
| R4 | Retrieval | Irrelevant property retrieval | Medium | Medium | Combine semantic search with metadata filters | Allow the sales user to ignore and rerun the search |
| R5 | Infrastructure | API failure | Medium | High | Add retry handling and fallback messages | Pause the workflow and store the inquiry for later review |
| R6 | Cost | API cost growth | Medium | Medium | Limit context size and keep prompts short | Reduce model usage and review the prompt design |
| R7 | Performance | Model latency | Medium | Medium | Keep the workflow small and avoid unnecessary calls | Show a loading state and allow manual handling |
| R8 | Security | Prompt injection | Medium | High | Treat user text as untrusted input and isolate instructions | Ignore suspicious content and fall back to safe responses |
| R9 | Privacy | Exposure of personal data | Low | High | Use fictional data only and avoid real credentials | Remove sensitive content immediately if discovered |
| R10 | Compliance | Missing GDPR consent | Low | High | Include consent as a required field in the lead model | Stop processing and request human review |
| R11 | Fairness | Biased lead scoring | Low | High | Base scoring only on sales readiness fields | Review the scoring rules with a human before use |
| R12 | Adoption | Low staff trust | Medium | Medium | Keep scoring transparent and explainable | Let staff override the result and provide feedback |
| R13 | Process | Excessive automation | Medium | High | Keep human approval mandatory for outward actions | Disable auto-send and route everything through review |
| R14 | Scope | Scope creep | High | Medium | Freeze the MVP scope and document out-of-scope items | Defer extras to later versions |
| R15 | Integration | n8n integration failure | Medium | Medium | Treat n8n as a future integration only | Keep the local workflow usable without n8n |
| R16 | Dependency | Dependence on external providers | Medium | Medium | Design the workflow to degrade gracefully | Replace unavailable services with manual steps |

## 5. Implementation Plan

The implementation plan is a four-week MVP roadmap. It is still a plan, not a build result.

### 5.1 Phase 1 - Setup and Data Preparation
Set up the repository structure, confirm the required fields, prepare fictional lead and property examples, define schemas, and document the evaluation scenarios.

### 5.2 Phase 2 - Core Agent Development
Design the extraction, validation, and scoring logic. Build the planned LangGraph workflow and define how the agent should move from intake to classification.

### 5.3 Phase 3 - Integration and Testing
Implement the retrieval pipeline, connect the Streamlit prototype view, and test end-to-end sample cases with the fictional data set.

### 5.4 Phase 4 - Deployment and Monitoring
Add the human-review checkpoint, document the future n8n role, perform acceptance testing, measure the success metrics, and write down the limitations.

### 5.5 Timeline and Milestones
**Week 1**
- Confirm requirements
- Prepare fictional data
- Define schemas
- Configure the development environment
- Define evaluation scenarios

**Week 2**
- Develop extraction, validation, and scoring
- Build the LangGraph workflow
- Add initial tests

**Week 3**
- Implement the RAG pipeline
- Create the Streamlit interface
- Test end-to-end scenarios

**Week 4**
- Add the human-review checkpoint
- Document the proposed n8n integration
- Perform acceptance testing
- Measure success metrics
- Document limitations and next steps

### 5.6 Dependencies
The plan depends on:
- A working Python environment
- The planned package set in `requirements.txt`
- Fictional sample data
- OpenAI API access for later prototype testing
- Local development tools
- Git version control
- Optional n8n access for future orchestration

### 5.7 Resources and Roles
The project would benefit from:
- An AI consultant or project lead to shape the workflow
- A Python or AI developer to build the prototype later
- A real estate subject-matter expert to validate business logic
- One or two sales users to review the output
- An OpenAI API account
- A local development environment
- A GitHub repository for version control
- Optional n8n environment for future integration work

### 5.8 Budget Considerations
These are early planning estimates, not a commercial quotation.

**Prototype and planning**
- Internal learning project: mainly development time
- API testing budget: approximately EUR 10-EUR 30
- Local tools: no additional infrastructure cost

**Future business pilot**
- Initial implementation estimate: approximately EUR 2,500-EUR 5,000
- Monthly software and API estimate: approximately EUR 50-EUR 250, depending on usage and integrations

## 6. Success Metrics

The project should be evaluated with measurable pilot targets:
- At least 90% required-field extraction accuracy on a controlled test set
- At least 85% correct identification of missing fields
- At least 80% relevant property retrieval in test scenarios
- At least 90% correct workflow routing
- 100% of outgoing actions stopped for human approval during the MVP
- Average processing time below 10 seconds, excluding human review
- Average API cost below EUR 0.05 per processed lead
- Fewer than 15% of cases requiring major manual correction
- No real personal data or credentials included in the lab repository

## 7. Minimal Prototype

The minimal prototype should show a single lead entering the system, the extraction of the required fields, the detection of missing information, the retrieval of fictional property matches, and the transparent score plus classification. The interface should make it clear that the result is a draft for human review, not an automatic sales action.

## 8. Next Steps

The next steps are to turn this plan into a small working prototype, define the test cases in more detail, and prepare the fictional data set for retrieval and scoring tests. After that, the team can decide whether the next priority is Streamlit refinement, n8n planning, or stronger evaluation coverage.
