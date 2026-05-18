(min 3 agents, +RAG and MCP)
Capstone project title:
Financial News Analyst
Data Agent fetches market data from various sources, News Agent scrapes financial news and reports, Analysis Agent combines RAG-retrieved historical patterns with current data to provide investment insights and market analysis.

1. Scenario of your choice
A student may propose a custom project topic. The student must discuss and get approval for the idea from the course team before starting work. The proposal may be approved if the idea and complexity level correspond to the example scenarios above and allow demonstration of all required skills and knowledge. The final decision on approval rests with the review committee.

The custom scenario must meet the following general requirements:

Multi-agent architecture: at least 3 agents with clearly defined, distinct roles and responsibilities
RAG pipeline: meaningful retrieval-augmented generation over a domain-specific knowledge base or document corpus
MCP integration: at least one external data source or tool connected via MCP protocol
Real-world applicability: the system must solve a tangible, clearly articulated problem
Inter-agent communication: agents must collaborate, delegate tasks, or share context — not operate in complete isolation
Testability: the use case must support both positive and negative test scenarios, including edge cases and adversarial inputs
Demonstrability: the system must be presentable in a 2–5 minute video demo showing end-to-end functionality

2. Non-Functional Requirements
Observability & Monitoring
LLM Tracing: Track all agent interactions, token usage, and response quality
Performance Metrics: Monitor response times, success rates, and system throughput
Error Tracking: Comprehensive logging of failures and system errors
User Feedback: Implement rating systems for response quality assessment
Resource Usage: Track memory, CPU, and API quota consumption

Input Validation: Sanitize all user inputs and API responses
Content Filtering: Implement guardrails against harmful or inappropriate content
Privacy Protection: PII detection and data anonymization capabilities
Access Control: Implement authentication and authorization mechanisms
Rate Limiting: Prevent abuse and manage resource consumption

RAG Quality Assurance
Retrieval Accuracy: Measure precision and recall of document retrieval
Answer Relevance: Evaluate semantic similarity and factual correctness
Source Attribution: Ensure proper citation and traceability
Hallucination Detection: Identify and flag potentially false information
Bias Assessment: Monitor for unfair or discriminatory outputs


Cost & Resource Management
Local-First Architecture: Minimize cloud dependencies and external costs
Free Tier Optimization: Stay within API limits and free service quotas
Efficient Processing: Implement caching and optimize resource usage
Scalability: Support concurrent users without performance degradation
Data Management: Implement retention policies and storage optimization

Compliance & Ethics
Industry Standards: Implement domain-specific compliance requirements
Transparency: Provide clear information about system capabilities and limitations
Consent Management: Handle user data with appropriate permissions
Audit Trail: Maintain logs for accountability and debugging
Graceful Degradation: Handle service failures with appropriate fallbacks

3. Success Criteria

Base Requirements (70 Points - Pass Threshold)
Working Application: Functional multi-agent system demonstrated in video
Code Delivery: Complete codebase with clear structure and comments
LLM Behavior Tests: Both positive and negative test scenarios
Normal user flow validation
Edge case and adversarial prompt handling
Video Demo: 2-5 minute demonstration showing:
Live system operation
Test execution (positive & negative cases)
Self-review with code commentary

Excellence Bonuses (30 Points Total)
+10 Points: UX & Presentation: Polished UI, smooth UX, investor-ready demo quality
+10 Points: Data Quality: Well-prepared datasets, proper data handling, quality validation
+10 Points: Code Excellence: Clean architecture, software engineering best practices, thoughtful design patterns (AI-generated code is fine, but show you understand it)

Deliverables [important]
Architecture Blueprint: Complete system design with technology stack and rationale
Video Demo: 2-5 minutes with voiceover explaining functionality and code choices
Code Repository: Well-structured project with README and setup instructions
Test Suite: Automated tests demonstrating LLM behavior validation
Self-Review: Code commentary addressing architecture decisions and trade-offs
Executive Summary: A concise 1-2 page overview of the project's objectives, key findings, and business value

