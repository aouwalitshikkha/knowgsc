# KnowGSC — Complete Product & Technical Blueprint

**KnowGSC — Google Search Console Problem-Solving Platform**

*Diagnose. Understand. Learn. Fix. Verify.*

A knowledge-driven platform that helps website owners and SEO professionals investigate Google Search Console problems through contextual explanations, guided diagnostic workflows, curated resources, and structured learning.

> **Core principle:** KnowGSC will be knowledge-first, workflow-driven, and AI-assisted — not an AI chatbot that independently diagnoses SEO problems.
>
> The platform will work even without a paid AI API. AI will be an optional enhancement, while the knowledge base, diagnostic rules, evidence collection, and workflow engine remain under our control.

---

## Table of Contents

1. [Product Vision and Objectives](#1-product-vision-and-objectives)
2. [Product Architecture](#2-product-architecture)
3. [Knowledge-First Assistant](#3-knowledge-first-assistant)
4. [Diagnostic Workflow Engine](#4-diagnostic-workflow-engine)
5. [RAG and Hallucination Prevention](#5-rag-and-hallucination-prevention)
6. [Handling Misspellings and Incorrect Grammar](#6-handling-misspellings-and-incorrect-grammar)
7. [Problem Knowledge Base](#7-problem-knowledge-base)
8. [Learning Roadmap](#8-learning-roadmap)
9. [Resource Library](#9-resource-library)
10. [Database Architecture](#10-database-architecture)
11. [Knowledge-Gap Management](#11-knowledge-gap-management)
12. [Technical Implementation](#12-technical-implementation)
13. [API Requirements](#13-api-requirements)
14. [Diagnostic Report Generation](#14-diagnostic-report-generation)
15. [GSC Practice Lab](#15-gsc-practice-lab)
16. [Admin Dashboard and Content Management](#16-admin-dashboard-and-content-management)
17. [Development Roadmap](#17-development-roadmap)
18. [MVP Acceptance Criteria](#18-mvp-acceptance-criteria)
19. [Product Development Priorities](#19-product-development-priorities)
20. [Final Architectural Decision](#20-final-architectural-decision)
21. [What to Build First](#21-what-to-build-first)
22. [Suggested Next Development Task](#22-suggested-next-development-task)

---

## 1. Product Vision and Objectives

### The Fundamental Problem

KnowGSC should solve a fundamental problem: people can find thousands of SEO articles, but they often don't know which information applies to their particular website.

Instead of simply explaining what a GSC status means, KnowGSC should help users investigate why they are experiencing it.

### Core Product Objectives

1. Explain every major GSC status and technical SEO problem.
2. Retrieve relevant articles, images, diagrams, and external documentation.
3. Let users investigate their own websites through conversational questions.
4. Select follow-up questions based on previous answers.
5. Separate confirmed evidence from possible explanations.
6. Recommend corrective actions with verification instructions.
7. Teach users how to perform diagnostics independently.
8. Build a growing knowledge base from reviewed content and recurring unanswered questions.

### Target Audiences

| Audience | Experience |
| --- | --- |
| Website owners | Simple explanations and guided questions |
| Beginner SEOs | Step-by-step diagnostic guidance |
| SEO professionals | Advanced technical investigation |
| Technical SEO consultants | Evidence, hypotheses, and detailed action plans |
| SEO learners | Learning roadmaps and practice scenarios |

The platform should have Beginner and Advanced modes. Both use the same diagnostic engine.

---

## 2. Product Architecture

### Eight Main Modules

| Module | Purpose | Priority |
| --- | --- | --- |
| Knowledge-first assistant | Explain problems and retrieve relevant content | Critical |
| Diagnostic workflow engine | Ask adaptive questions and evaluate evidence | Critical |
| Problem knowledge base | Store reviewed explanations, causes, and solutions | Critical |
| Resource library | Connect external references and testing tools | High |
| Learning roadmap | Teach GSC and technical SEO | High |
| Practice lab | Simulate Google Search Console investigations | High |
| User workspace | Save investigations, findings, and progress | High |
| Technical SEO tools | Perform selected website checks | Later |

### Main Navigation

- Home
- Ask KnowGSC
- Problem Solver
- Workflows
- Learning Roadmap
- Practice Lab
- Resources
- SEO Tools
- My Workspace

The assistant should be accessible from the homepage and throughout the platform.

### Homepage

The homepage should have a single primary objective: help the visitor identify their problem.

**Suggested headline:** Solve Google Search Console Problems Step by Step.

**Subheadline:** Understand indexing, crawling, canonicalization, server errors, and search performance through guided troubleshooting and practical learning.

Homepage sections:

1. Hero with conversational search.
2. Popular GSC problems.
3. Start a diagnostic session.
4. Explore troubleshooting workflows.
5. Learning roadmap.
6. Interactive GSC practice lab.
7. Official Google resources.
8. Latest technical SEO guides.

The search interface should accept natural-language questions, not just predefined keywords.

---

## 3. Knowledge-First Assistant

This is the most important user-facing feature.

The assistant must not immediately ask diagnostic questions whenever someone asks about an SEO problem. It should first explain the problem, show useful resources, and then offer an investigation.

### Conversation Lifecycle

#### Stage 1: Understand the Question

The user might write:

> "My site pages are discovered not index. What can be problem?"

The system identifies:

- Topic: Indexing.
- GSC status: Discovered – currently not indexed.
- Intent: Understand possible causes.
- User experience: Not yet known.

#### Stage 2: Retrieve Knowledge

Retrieve relevant content from:

- Problem explanation.
- Possible causes.
- Technical guides.
- Images and diagrams.
- Official Google documentation.
- Related lessons.

#### Stage 3: Generate the Educational Response

The assistant explains:

- What the status means.
- What it doesn't mean.
- Why it can happen.
- What factors are worth investigating.
- Which articles and diagrams can help.

#### Stage 4: Invite Investigation

Example:

> "Would you like me to investigate your website? I can ask a few questions and help narrow down the possible causes."

Offer two actions:

- Help me investigate.
- I'll read more first.

#### Stage 5: Start Diagnostic Session

Only after the user accepts should the diagnostic workflow begin.

### Response Composition

Every knowledge-first answer should use reusable content blocks.

| Block | Content |
| --- | --- |
| Introduction | Explain the user's problem |
| Definition | What the status or error means |
| Possible causes | Reviewed potential explanations |
| Visual explanation | Image, diagram, or infographic |
| Related articles | Internal knowledge-base links |
| External resources | Official documentation and testing tools |
| Diagnostic invitation | Offer to investigate the user's website |

The assistant should not display every possible article. It should select the most relevant material.

### Content Block Types

Create a reusable content system with these types:

- `explanation`
- `possible_cause`
- `technical_note`
- `image`
- `diagram`
- `article_card`
- `external_link`
- `warning`
- `diagnostic_invitation`
- `related_problem`
- `verification_instruction`

This allows you to compose different answers from the same approved knowledge blocks.

For example, one TTFB diagram could be reused in multiple workflows without duplicating the image or explanation.

---

## 4. Diagnostic Workflow Engine

The workflow engine is the decision-making core of KnowGSC.

It determines what to ask, when to ask it, and what action should follow.

RAG retrieves knowledge. The workflow engine controls the diagnostic sequence.

### Diagnostic Lifecycle

1. User selects a problem.
2. System creates a diagnostic session.
3. The first question is selected.
4. User submits an answer.
5. System validates and stores the answer.
6. Diagnostic rules evaluate the evidence.
7. The next question is selected.
8. Relevant knowledge is retrieved.
9. Assistant explains why the next question matters.
10. The process continues until sufficient evidence exists.
11. System generates findings and an action plan.
12. User performs actions and records verification results.

### Adaptive Questions

Questions must not be fixed in one long sequence.

| User Answer | Next Diagnostic Direction |
| --- | --- |
| URL missing from sitemap | Check whether omission is intentional |
| URL included in sitemap | Investigate other discovery signals |
| Few internal links | Investigate internal linking and crawl depth |
| HTTP 504 | Investigate timeout reproducibility |
| HTTP 200 | Continue with crawl accessibility and other evidence |
| Intermittent 5xx | Investigate server stability and logs |

The system should ask one useful question at a time.

It should also support:

- I don't know.
- Skip this question.
- Show me how to check.
- Enter my own answer.
- Upload evidence.
- Return to a previous answer.

### Workflow Node Types

Use a structured workflow format with these node types:

| Node | Purpose |
| --- | --- |
| Start | Initialize investigation |
| Question | Collect user information |
| Condition | Evaluate an answer |
| Evidence check | Validate available evidence |
| Explanation | Explain a finding |
| Action | Recommend a test or fix |
| Resource | Show related documentation |
| Lesson | Recommend educational content |
| Finding | Record a diagnostic conclusion |
| Verification | Check the result |
| End | Complete the workflow |

### Example Workflow

Problem: Discovered – currently not indexed.

```
START
  |
  v
Confirm GSC status
  |
  v
Check sitemap inclusion
  |
  +-- Missing --> Check intended URL eligibility
  |
  +-- Present --> Check sitemap validity
  |
  v
Check internal links
  |
  +-- Weak --> Investigate internal linking
  |
  +-- Strong --> Continue investigation
  |
  v
Check HTTP response
  |
  +-- 5xx --> Investigate server error
  |
  +-- 200 --> Continue investigation
  |
  +-- Redirect --> Investigate redirect behavior
  |
  v
Collect additional evidence
  |
  v
Generate findings and action plan
  |
  v
Verify results
```

This is a simplified illustrative flow. The production workflow should include more branches, including intentional exclusions, URL accessibility, and missing evidence.

### Workflow Versioning

Every workflow must have a version.

If you update a diagnostic workflow, existing sessions should retain their original version unless the user explicitly migrates to a newer one.

This prevents an ongoing investigation from changing unexpectedly.

---

## 5. RAG and Hallucination Prevention

This is where you need to be especially careful.

RAG does not eliminate hallucinations. It improves grounding by retrieving relevant information, but the model can still misinterpret it or produce unsupported claims.

KnowGSC should use controlled knowledge retrieval and deterministic rules.

### The Three Knowledge Layers

**Layer A — Structured knowledge**

Contains:

- GSC statuses.
- Definitions.
- Diagnostic rules.
- Questions.
- Possible causes.
- Recommended checks.
- Approved actions.
- Verification methods.

This is the authoritative source for diagnostic decisions.

**Layer B — RAG knowledge**

Contains:

- Articles.
- Technical SEO explanations.
- Google documentation.
- Diagrams.
- Case studies.
- Tutorials.
- Internal learning materials.

This provides supporting information and explanations.

**Layer C — External knowledge**

Contains approved external resources, with source attribution and review information.

External search should be optional and must not silently turn an unverified webpage into an approved KnowGSC recommendation.

### Retrieval Pipeline

1. Receive the user's question.
2. Normalize likely spelling mistakes.
3. Identify possible GSC terms and intent.
4. Search using keyword matching.
5. Search using semantic similarity.
6. Combine and rerank results.
7. Check whether the retrieved documents are relevant.
8. Return the strongest supporting content.
9. Generate an answer using the retrieved content.
10. Validate source references and unsupported claims.

### Hallucination Safeguards

| Risk | Protection |
| --- | --- |
| Invented SEO advice | Only approved diagnostic actions |
| Incorrect GSC status | Structured status definitions |
| Unsupported cause | Label causes as hypotheses |
| Wrong follow-up question | Workflow-controlled transitions |
| Fabricated website test | Separate user-reported and verified evidence |
| Outdated documentation | Source review dates |
| Missing knowledge | Ask for clarification or acknowledge limitations |
| Unsafe technical changes | Review requirements and warnings |

The AI should never automatically publish its generated answers into the permanent knowledge base.

### Do You Need an AI API?

Not for the entire system.

You can build:

- Workflows.
- Rules.
- Keyword search.
- Typo-tolerant search.
- Articles.
- Images.
- Diagnostic sessions.
- Learning roadmaps.

without a generative AI API.

An AI API becomes useful for flexible natural-language interpretation and explanations. You can also run an open-source model locally, depending on available hardware and performance requirements.

---

## 6. Handling Misspellings and Incorrect Grammar

Users may write:

- "my page not index"
- "discovred not indexd"
- "google not crwal my site"
- "sitemap submited but no index"
- "why google dont index my urls"

KnowGSC should understand these without requiring perfect English.

### Recommended Retrieval Stack

| Component | Technology | Purpose |
| --- | --- | --- |
| Keyword search | PostgreSQL Full Text Search | Find matching terminology |
| Typo tolerance | PostgreSQL pg_trgm | Handle spelling differences |
| Terminology dictionary | Django database | Recognize SEO and GSC terms |
| Semantic retrieval | Embedding model | Understand meaning beyond exact words |
| Optional language model | AI API or local model | Normalize ambiguous natural language |

### GSC Terminology Dictionary

Create a table containing:

- Official term.
- Common spelling mistakes.
- Informal expressions.
- Related terms.
- Synonyms.
- Problem category.

Example:

```
Official: Discovered – currently not indexed

Variations:
discovered not indexed
discovred not indexd
discovered but not indexed
google discovered my url
google found page but not crawled
```

### Ambiguity Handling

If a user says "Google not indexing my pages", don't automatically choose a workflow.

Present the most likely interpretations:

- Discovered – currently not indexed.
- Crawled – currently not indexed.
- Excluded by noindex.
- Blocked by robots.txt.

Ask the user to select one or explain how to find the status.

---

## 7. Problem Knowledge Base

Build a comprehensive library of GSC problems.

Each problem record should contain:

1. Name.
2. Slug.
3. Category.
4. Official status classification.
5. Definition.
6. Explanation.
7. Possible causes.
8. Diagnostic questions.
9. Recommended checks.
10. Corrective actions.
11. Verification steps.
12. Images and diagrams.
13. Related articles.
14. External references.
15. Related workflows.
16. Review date.

### Initial Categories

#### A. Indexing

- Discovered – currently not indexed.
- Crawled – currently not indexed.
- Excluded by noindex.
- Blocked by robots.txt.
- Page with redirect.
- Soft 404.
- Not found (404).
- Duplicate without user-selected canonical.
- Google-selected canonical differs from user-declared canonical.

#### B. Crawling and Server

- Server error (5xx).
- 403 Forbidden.
- Redirect errors.
- Robots.txt fetch errors.
- Sitemap retrieval errors.
- Unexpected HTTP responses.

#### C. Rendering

- JavaScript rendering problems.
- Missing rendered content.
- Blocked resources.
- Rendering differences.

#### D. Sitemap and Discovery

- Invalid sitemap.
- Sitemap not fetched.
- URLs excluded from sitemap.
- Incorrect canonical URLs in sitemap.
- Internal linking issues.
- Orphan pages.

#### E. Core Web Vitals

- LCP.
- INP.
- CLS.
- Field data versus laboratory data.

#### F. Search Performance

- Traffic decline.
- Impressions decline.
- Low CTR.
- Ranking changes.
- Query-level performance problems.

#### G. Other Reports

- Structured data.
- Manual actions.
- Security issues.
- International SEO.

Distinguish actual GSC statuses and reports from technical conditions that may explain them.

---

## 8. Learning Roadmap

Build the learning system around practical competencies.

| Level | Subject | Practical Outcome |
| --- | --- | --- |
| 1 | GSC fundamentals | Understand reports and indexing terminology |
| 2 | Indexing diagnostics | Investigate common indexing exclusions |
| 3 | Technical SEO | Analyze HTTP, crawling, rendering, and server behavior |
| 4 | Search performance | Investigate traffic and ranking changes |
| 5 | Advanced SEO | Handle large-scale and complex technical cases |

Each lesson should have:

- Learning objectives.
- Explanation.
- Example.
- Images or diagrams.
- Practical exercise.
- Knowledge check.
- Related diagnostic workflow.
- Official documentation.
- Next recommended lesson.

Track user progress, prerequisites, and assessment results.

The roadmap should also recommend lessons based on weaknesses discovered during diagnostic sessions.

---

## 9. Resource Library

Resources should be contextual, not just a list of external links.

For example, when investigating canonical problems, show documentation about canonicalization. When investigating server errors, show relevant HTTP and server troubleshooting resources.

### Initial Official Resource Collection

| Resource | Purpose |
| --- | --- |
| Google Search Central | Search and crawling documentation |
| Google Search Console Help | GSC reports and troubleshooting |
| PageSpeed Insights | Performance analysis |
| Rich Results Test | Structured data testing |
| Search Console API | Future integration |

**Important starting links:**

- [https://developers.google.com/search/docs](https://developers.google.com/search/docs?utm_source=chatgpt.com)
- [https://support.google.com/webmasters/](https://support.google.com/webmasters/?utm_source=chatgpt.com)
- [https://pagespeed.web.dev/](https://pagespeed.web.dev/?utm_source=chatgpt.com)
- [https://search.google.com/test/rich-results](https://search.google.com/test/rich-results?utm_source=chatgpt.com)
- [https://developers.google.com/webmaster-tools/v1/api_reference_index](https://developers.google.com/webmaster-tools/v1/api_reference_index?utm_source=chatgpt.com)

Each resource should include its URL, category, source type, related problems, last-checked date, and publication status.

---

## 10. Database Architecture

Use PostgreSQL as the primary database.

### Recommended Django Applications

```
knowgsc/
│
├── accounts/
├── problems/
├── knowledge/
├── workflows/
├── diagnostics/
├── evidence/
├── resources/
├── learning/
├── practice_lab/
├── assistant/
├── reports/
├── integrations/
└── core/
```

### Core Database Models

| Model | Responsibility |
| --- | --- |
| UserProfile | User preferences and experience level |
| ProblemCategory | Problem classification |
| Problem | Individual GSC problems |
| KnowledgeArticle | Reviewed knowledge articles |
| KnowledgeBlock | Reusable answer components |
| KnowledgeDocument | RAG source documents |
| KnowledgeChunk | Searchable document chunks |
| Resource | External links and references |
| Workflow | Versioned diagnostic definitions |
| WorkflowNode | Questions, conditions, and actions |
| DiagnosticSession | Individual investigations |
| DiagnosticAnswer | User answers |
| EvidenceItem | User-reported and verified evidence |
| DiagnosticFinding | Findings and hypotheses |
| RecommendedAction | Suggested corrective steps |
| LearningPath | Learning roadmaps |
| Lesson | Individual lessons |
| UserLessonProgress | Learning progress |
| PracticeScenario | Simulated GSC scenarios |
| PracticeAttempt | User practice results |
| KnowledgeGap | Unanswered or poorly answered questions |
| Conversation | Assistant conversations |
| ConversationMessage | User and assistant messages |

### Important Relationships

- A problem can have multiple workflows.
- A workflow can have many diagnostic sessions.
- A session can have many answers and evidence items.
- A session can produce many findings and actions.
- An article can contain many knowledge blocks.
- A resource can support multiple problems.
- A knowledge document can produce multiple searchable chunks.
- A lesson can belong to multiple learning paths.

Store workflow versions and session references explicitly.

---

## 11. Knowledge-Gap Management

A question that is not answered by your existing knowledge base should not cause the assistant to invent an answer.

Create a fallback process:

1. Search exact terms.
2. Search related terminology.
3. Search semantically.
4. Check approved external resources if available.
5. Ask for clarification if needed.
6. If no reliable answer exists, acknowledge the limitation.
7. Record the knowledge gap.
8. Let an administrator review it.

### Admin Knowledge-Gap Dashboard

Show:

- Unanswered questions.
- Frequently repeated questions.
- Failed retrievals.
- Low-relevance results.
- Missing documentation.
- Suggested new articles.
- Questions requiring expert review.

Group similar questions together so that one new article can solve many knowledge gaps.

Do not automatically publish AI-generated answers.

---

## 12. Technical Implementation

Given your existing Django development experience, I recommend a Django monolith for the first release.

### Proposed Stack

| Layer | Technology |
| --- | --- |
| Backend | Django |
| Database | PostgreSQL |
| Frontend | Django Templates + Tailwind CSS |
| Interactive UI | JavaScript |
| Keyword retrieval | PostgreSQL Full Text Search |
| Typo tolerance | pg_trgm |
| Semantic retrieval | pgvector |
| Embeddings | Local embedding model or embedding API |
| AI responses | Optional LLM API |
| Background jobs | Celery + Redis when needed |
| File storage | Private object storage |
| Authentication | Django authentication |

You do not need a separate React application for the MVP.

### Important Application Services

- KnowledgeRetriever — Retrieves relevant articles, chunks, images, and references.
- QueryNormalizer — Identifies common spelling mistakes, technical terms, and likely user intent.
- DiagnosticEngine — Evaluates answers and chooses the next diagnostic step.
- ConversationManager — Maintains session context and stores conversation history.
- ResponseAssembler — Builds the knowledge-first response from approved content blocks.
- KnowledgeGapManager — Records unanswered questions and retrieval failures.
- VerificationService — Performs permitted technical checks and records actual results.

---

## 13. API Requirements

You can launch the manual diagnostic platform without Google Search Console API access or a paid generative AI API.

| Capability | External API |
| --- | --- |
| Django workflows | No |
| Database and user accounts | No |
| Knowledge articles | No |
| Keyword and typo-tolerant search | No |
| Local semantic search | No |
| Curated diagrams and images | No |
| Server-side HTTP checks | No external API required |
| AI conversational responses | Optional AI model API |
| Live web research | Optional search service |
| Google Search Console data | Google Search Console API |
| Embeddings | Optional embedding API |

### Future GSC Integration

After the manual version is stable, add:

- Google OAuth.
- Property selection.
- URL Inspection.
- Search Analytics.
- Sitemap information where supported.
- Historical diagnostic comparisons.

Remember that the API does not expose every GSC report or all Google's internal indexing decisions.

---

## 14. Diagnostic Report Generation

Every completed investigation should produce a structured report.

```
Problem: Discovered – currently not indexed.

User-provided evidence:
- Sitemap inclusion: Missing.
- Internal links: Weak.
- HTTP response: 504.
- Duration: Unknown.

Potential explanations:
- Weak internal discovery signals.
- Sitemap omission.
- Intermittent or persistent server timeout.

Unverified information:
- Whether the 504 is reproducible.
- Whether Googlebot received the same response.
- Whether the pages are intended to be indexed.
- Whether the server issue affects other URLs.

Recommended next actions:
1. Repeat the HTTP check.
2. Inspect relevant proxy and application logs.
3. Check whether affected URLs should be in the sitemap.
4. Improve meaningful internal linking where appropriate.
5. Verify Google can successfully fetch the URLs.

Verification:
Repeat the relevant tests and review subsequent GSC observations.
```

The report must not claim that an indexing problem is fixed just because a server response has improved.

---

## 15. GSC Practice Lab

This should be a major differentiator.

Build a simulated Google Search Console interface with fictional:

- Performance reports.
- Indexing reports.
- URL Inspection results.
- Sitemap reports.
- Page experience data.
- Example URLs.
- Technical errors.

Users investigate scenarios and receive feedback.

### Initial Scenarios

1. Discovered – currently not indexed.
2. Crawled – currently not indexed.
3. Duplicate canonical issue.
4. Redirect error.
5. 5xx server error.
6. Blocked by robots.txt.
7. Sitemap errors.
8. Soft 404.
9. Core Web Vitals problems.
10. Sudden traffic decline.

The practice environment should resemble GSC where appropriate, but clearly identify itself as a simulation.

---

## 16. Admin Dashboard and Content Management

You need an efficient way to manage the platform without editing Python files every time you create a new workflow.

Admin capabilities:

- Manage problems.
- Create and edit articles.
- Upload diagrams and screenshots.
- Add resource links.
- Create workflow questions.
- Define conditional branches.
- Link articles to workflow steps.
- Preview beginner and advanced responses.
- Test workflow branches.
- Review AI-generated answers.
- Review knowledge gaps.
- Manage learning paths.
- Publish versioned workflows.

**Important:** Build a workflow preview and validation interface early. It will save considerable development time when the problem library grows.

---

## 17. Development Roadmap

A focused MVP can be built in approximately 8–10 weeks, depending on how much content and interface development you undertake.

| Phase | Duration | Main Deliverables |
| --- | --- | --- |
| 1. Foundation | Week 1 | Architecture, taxonomy, database, wireframes |
| 2. Core application | Weeks 2–3 | Homepage, problem library, user accounts, admin |
| 3. Workflow engine | Weeks 3–5 | Questions, branches, evidence, sessions |
| 4. Knowledge retrieval | Weeks 5–6 | Search, typo handling, content retrieval |
| 5. Assistant | Week 6–7 | Conversational interface and optional AI |
| 6. Learning and practice | Weeks 7–8 | Roadmap, lessons, practice lab |
| 7. Testing and launch | Weeks 9–10 | Security, QA, performance, deployment |

The first launch should focus on 20–30 thoroughly reviewed problem guides rather than hundreds of incomplete articles.

---

## 18. MVP Acceptance Criteria

The first release should satisfy these requirements:

- Users can ask questions in natural language.
- Misspelled questions can retrieve relevant knowledge.
- The assistant explains the problem before offering diagnosis.
- Responses can contain articles, images, diagrams, and external links.
- Users can voluntarily start a diagnostic session.
- The workflow engine asks adaptive questions.
- Previous answers are remembered.
- Unknown answers are handled gracefully.
- The system distinguishes user-reported and verified evidence.
- Diagnostic conclusions are supported by evidence.
- The assistant does not invent causes or fixes.
- Findings and action plans can be saved.
- Admins can create and test workflows without changing code.
- Users can access structured learning paths.
- Users can practice in a simulated GSC environment.
- Unanswered questions can be reviewed and added to the knowledge base.

---

## 19. Product Development Priorities

### Release 1 — KnowGSC Core

- Knowledge-first assistant.
- Problem library.
- Search and typo handling.
- Guided diagnostic engine.
- Session history.
- Resource links.
- Admin content management.

### Release 2 — KnowGSC Learning

- Learning roadmap.
- Interactive lessons.
- Practice lab.
- Progress tracking.
- Diagnostic reports.
- Knowledge-gap dashboard.

### Release 3 — KnowGSC Intelligence

- Optional AI conversational layer.
- More advanced semantic retrieval.
- Automated HTTP and technical checks.
- Google Search Console API.
- Property-based investigations.
- Historical comparison and reporting.

This order ensures the platform is useful before introducing more complicated AI capabilities.

---

## 20. Final Architectural Decision

This is the architecture I recommend committing to.

### KnowGSC System Architecture

**User interface:**

- Chat · Problem Solver · Learning · Practice Lab

**Conversation and intent layer:**

- Intent recognition · Typo correction · Session management

**Knowledge engine:**

- Articles · Resources · Images · RAG

**Diagnostic engine:**

- Rules · Questions · Evidence · Findings

**Response and reporting layer:**

- Knowledge-first answers · Adaptive questions · Diagnostic reports

**PostgreSQL + Django:**

- Persistent knowledge, workflow versions, user sessions, and learning progress.

---

## 21. What to Build First

I would not start with the entire platform. Start by developing one complete, production-quality diagnostic experience.

### First Development Target

**Workflow: Discovered – currently not indexed**

Build these components first:

1. Problem knowledge base entry.
2. Knowledge-first conversational response.
3. Relevant article and diagram display.
4. Diagnostic invitation.
5. Adaptive question engine.
6. Answer and evidence storage.
7. Conditional diagnostic branches.
8. Final findings and action plan.
9. Admin workflow editor.
10. Session history.

### Most Important Principle

You should be able to add a new GSC problem, its knowledge, images, questions, and diagnostic rules through the admin interface without writing new Python code for every problem. That is what will make KnowGSC scalable.

---

## 22. Suggested Next Development Task

Build the actual Django project foundation, starting with the database models and workflow engine, then implement the first diagnostic workflow end to end.

This is the best way to turn the blueprint into a working product rather than spending time building a chatbot before the underlying diagnostic system exists.

---

*This document consolidates the complete KnowGSC plan into a single product and technical blueprint.*
