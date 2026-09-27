# System Requirements — Modular RAG Learning Platform

## 1. Project Overview

Build a modular **AI Agent + RAG learning platform** whose primary purpose is to learn, implement, compare, evaluate, and test different RAG strategies.

The project should support multiple implementations for each stage of the RAG pipeline, including:

- Document loading
- Document parsing
- Document cleaning
- Chunking
- Embedding generation
- Vector storage
- Retrieval
- Hybrid retrieval
- Re-ranking
- Query transformation
- Context construction
- LLM generation
- RAG evaluation
- Testing
- Monitoring

The most important architectural requirement is **swappability**.

For example, if the project has:

```text
chunking/
├── fixed_size.py
├── recursive.py
├── semantic.py
└── parent_child.py
```

the system should allow us to change:

```python
chunker = RecursiveChunker()
```

to:

```python
chunker = SemanticChunker()
```

without modifying the rest of the RAG pipeline.

The same principle should apply to retrieval, embeddings, document loaders, evaluation methods, and other components.

---

## 2. Main Goals

The system must:

1. Provide a clean and scalable project structure.
2. Keep each RAG component independent.
3. Allow multiple implementations of the same component.
4. Allow implementations to be swapped through configuration.
5. Make experiments easy to reproduce.
6. Make it easy to compare different RAG strategies.
7. Support automated testing and evaluation.
8. Provide a minimal ChatGPT-like chatbot UI.
9. Keep frontend, backend, AI agent, RAG pipeline, database, and evaluation code separated.
10. Make the architecture suitable for eventually evolving into a production-grade RAG system.

---

## 3. Technical Architecture

```text
                    ┌─────────────────────┐
                    │      React UI       │
                    │   ChatGPT-like UI   │
                    └──────────┬──────────┘
                               │
                               │ HTTP / SSE
                               ▼
                    ┌─────────────────────┐
                    │     FastAPI         │
                    │      Backend        │
                    └──────────┬──────────┘
                               │
             ┌─────────────────┼─────────────────┐
             │                 │                 │
             ▼                 ▼                 ▼
       ┌───────────┐    ┌──────────────┐   ┌────────────┐
       │ AI Agent  │    │ RAG Pipeline │   │  Services  │
       └───────────┘    └──────────────┘   └────────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │ PostgreSQL          │
                    │ + pgvector          │
                    └─────────────────────┘
```

### Frontend

- React
- TypeScript
- Minimal ChatGPT-style interface
- Streaming responses
- Conversation history
- Source/citation display
- Basic loading/error states

### Backend

- Python
- FastAPI
- REST APIs
- Streaming API using SSE where appropriate
- Request validation
- Configuration management
- Dependency injection

### Database

- PostgreSQL
- pgvector
- Store:
  - documents
  - chunks
  - embeddings
  - metadata
  - conversations
  - messages
  - evaluation results where appropriate

---

## 4. Recommended Folder Structure

Use a monorepo structure:

```text
rag-learning-platform/
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── services/
│   │   ├── types/
│   │   ├── utils/
│   │   └── App.tsx
│   │
│   ├── package.json
│   └── README.md
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── chat.py
│   │   │   │   ├── documents.py
│   │   │   │   ├── evaluation.py
│   │   │   │   └── experiments.py
│   │   │   └── dependencies.py
│   │   │
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── logging.py
│   │   │   └── exceptions.py
│   │   │
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── main.py
│   │
│   ├── tests/
│   ├── requirements.txt
│   └── README.md
│
├── ai_agent/
│   ├── agent/
│   │   ├── agent.py
│   │   ├── state.py
│   │   ├── planner.py
│   │   └── executor.py
│   │
│   ├── tools/
│   ├── memory/
│   ├── prompts/
│   ├── guardrails/
│   └── tests/
│
├── rag/
│   │
│   ├── types/
│   │   ├── document.py
│   │   ├── chunk.py
│   │   ├── retrieval.py
│   │   └── evaluation.py
│   │
│   ├── ingestion/
│   │   ├── loaders/
│   │   │   ├── base.py
│   │   │   ├── pdf_loader.py
│   │   │   ├── docx_loader.py
│   │   │   ├── html_loader.py
│   │   │   └── text_loader.py
│   │   │
│   │   ├── parsers/
│   │   ├── cleaners/
│   │   └── pipeline.py
│   │
│   ├── chunking/
│   │   ├── base.py
│   │   ├── fixed_size.py
│   │   ├── recursive.py
│   │   ├── semantic.py
│   │   ├── sentence.py
│   │   └── parent_child.py
│   │
│   ├── embeddings/
│   │   ├── base.py
│   │   ├── openai.py
│   │   ├── sentence_transformer.py
│   │   └── local.py
│   │
│   ├── vectorstores/
│   │   ├── base.py
│   │   └── pgvector.py
│   │
│   ├── retrieval/
│   │   ├── base.py
│   │   ├── dense.py
│   │   ├── sparse.py
│   │   ├── hybrid.py
│   │   └── metadata.py
│   │
│   ├── reranking/
│   │   ├── base.py
│   │   ├── cross_encoder.py
│   │   └── llm_reranker.py
│   │
│   ├── query/
│   │   ├── rewriting.py
│   │   ├── multi_query.py
│   │   ├── hyde.py
│   │   └── decomposition.py
│   │
│   ├── context/
│   │   ├── builder.py
│   │   ├── compression.py
│   │   └── deduplication.py
│   │
│   ├── generation/
│   │   ├── base.py
│   │   └── llm.py
│   │
│   ├── evaluation/
│   │   ├── datasets/
│   │   ├── retrieval/
│   │   ├── generation/
│   │   ├── end_to_end/
│   │   └── metrics/
│   │
│   ├── testing/
│   │   ├── unit/
│   │   ├── integration/
│   │   ├── regression/
│   │   └── fixtures/
│   │
│   ├── monitoring/
│   │   ├── tracing.py
│   │   ├── metrics.py
│   │   └── logging.py
│   │
│   └── pipeline.py
│
├── database/
│   ├── migrations/
│   ├── schemas/
│   └── seed/
│
├── experiments/
│   ├── configs/
│   ├── results/
│   └── notebooks/
│
├── configs/
│   ├── development.yaml
│   ├── testing.yaml
│   └── production.yaml
│
├── tests/
│   ├── integration/
│   └── e2e/
│
├── docker/
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   └── docker-compose.yml
│
├── .env.example
├── README.md
└── Makefile
```

---

## 5. Strategy Swapping Requirement

This is the **most important requirement** of the project.

Do not hard-code implementations directly inside the pipeline.

For example, avoid:

```python
def run_rag(query):
    chunks = recursive_chunking(...)
```

Instead, use interfaces/abstract classes.

Example:

```python
class Chunker(ABC):

    @abstractmethod
    def chunk(self, documents):
        pass
```

Implementations:

```python
class RecursiveChunker(Chunker):
    ...

class SemanticChunker(Chunker):
    ...

class ParentChildChunker(Chunker):
    ...
```

Then configure the selected strategy:

```yaml
rag:
  chunking:
    strategy: semantic

  retrieval:
    strategy: hybrid

  reranking:
    strategy: cross_encoder

  embedding:
    strategy: sentence_transformer
```

The pipeline should dynamically construct the selected implementations.

Therefore changing:

```yaml
chunking:
  strategy: recursive
```

to:

```yaml
chunking:
  strategy: semantic
```

should be enough to run the same pipeline using another strategy.

---

## 6. Common Interfaces

Every swappable component should expose a common interface.

Required interfaces include:

```text
DocumentLoader
DocumentParser
DocumentCleaner
Chunker
EmbeddingModel
VectorStore
Retriever
Reranker
QueryTransformer
ContextBuilder
Generator
Evaluator
```

Each implementation must follow the same interface.

This allows experiments such as:

```text
Experiment A
Recursive Chunking + Dense Retrieval

Experiment B
Semantic Chunking + Dense Retrieval

Experiment C
Semantic Chunking + Hybrid Retrieval

Experiment D
Semantic Chunking + Hybrid Retrieval + Cross Encoder
```

without changing application code.

---

## 7. RAG Pipeline

The RAG pipeline should have clear stages:

```text
Document
   ↓
Loading
   ↓
Parsing
   ↓
Cleaning
   ↓
Chunking
   ↓
Embedding
   ↓
Vector Storage
   ↓
Query
   ↓
Query Transformation
   ↓
Retrieval
   ↓
Filtering
   ↓
Reranking
   ↓
Context Construction
   ↓
LLM
   ↓
Response
   ↓
Evaluation
```

Each stage should be independently testable.

---

## 8. Evaluation System

The project must treat evaluation as a first-class component.

### Retrieval

- Recall@K
- Precision@K
- Context relevance
- Context precision
- Context recall

### Generation

- Faithfulness
- Answer relevance
- Correctness
- Hallucination detection

### End-to-End

- Answer quality
- Citation correctness
- Latency
- Token usage
- Cost
- Error rate

The evaluation system should allow different evaluators to be plugged in without changing the RAG pipeline.

---

## 9. Testing Requirements

Implement multiple testing levels.

### Unit Tests

Test individual components:

```text
chunker
retriever
embedding model
reranker
query transformer
context builder
```

### Integration Tests

Test combinations:

```text
Retriever + PGVector
Embedding + PGVector
RAG Pipeline + LLM
```

### Regression Tests

Maintain a golden/evaluation dataset containing:

```text
question
expected_answer
expected_documents
expected_evidence
metadata
```

Whenever we change:

- chunking
- embeddings
- retrieval
- reranking
- prompts
- LLM
- data

the regression suite should be runnable to compare results.

---

## 10. Experiment Framework

Create an experiment system so we can compare strategies.

Example:

```yaml
experiment:
  name: semantic_vs_recursive

  chunking:
    - recursive
    - semantic

  retrieval:
    - dense

  reranking:
    - none
    - cross_encoder
```

The experiment runner should execute the configurations and store:

```text
configuration
metrics
latency
cost
retrieval results
generated answers
evaluation results
timestamp
```

This will allow us to actually **learn which RAG strategy changes what behavior**.

---

## 11. AI Agent

The AI Agent should be separate from the RAG implementation.

```text
ai_agent/
```

The agent may use RAG as one of its tools/capabilities.

Example:

```text
User
 ↓
AI Agent
 ↓
Understand Intent
 ↓
Select Tool
 ↓
RAG Tool
 ↓
RAG Pipeline
 ↓
Answer
```

The agent should not contain RAG implementation details.

---

## 12. Chatbot UI

Build a minimal ChatGPT-like interface.

Required:

- Chat message list
- User/assistant messages
- Input box
- Send button
- Streaming response
- Markdown rendering
- Code block rendering
- Loading state
- Error state
- New conversation
- Source/citation display

Keep the UI simple. Do not spend significant effort on visual customization.

---

## 13. Backend APIs

At minimum provide:

```text
POST /api/chat
POST /api/documents/upload
GET  /api/documents
DELETE /api/documents/{id}

POST /api/evaluation/run
GET  /api/evaluation/results

POST /api/experiments/run
GET  /api/experiments/{id}

GET /api/health
```

The chat API should support streaming responses.

---

## 14. Configuration

All strategy selection should happen through configuration rather than modifying source code.

Example:

```yaml
llm:
  provider: openai
  model: ...

embedding:
  provider: sentence_transformers
  model: ...

chunking:
  strategy: recursive

retrieval:
  strategy: hybrid

reranking:
  strategy: cross_encoder

query_transformation:
  strategy: none

evaluation:
  strategy: ragas
```

The application should read this configuration during startup and construct the appropriate implementations.

---

## 15. Database Requirements

Use:

```text
PostgreSQL
+
pgvector
```

Suggested entities:

```text
documents
document_versions
chunks
embeddings
conversations
messages
evaluation_datasets
evaluation_results
experiments
experiment_runs
```

Store sufficient metadata to trace a RAG answer back to the source document and chunk.

---

## 16. Observability

Every RAG request should be traceable through:

```text
request_id
query
retrieval strategy
embedding model
chunking strategy
retrieved chunks
retrieval scores
reranking scores
prompt/model version
LLM response
latency
token usage
errors
```

This is important because when an answer is wrong, we should be able to identify **which stage caused the problem**.

---

## 17. Development Principles

Follow these principles throughout the project:

1. **Modularity**
2. **Separation of concerns**
3. **Dependency inversion**
4. **Configuration over hard-coding**
5. **Interface-based design**
6. **Testability**
7. **Reproducible experiments**
8. **Observability**
9. **Clear naming**
10. **Minimal coupling**

Do not create one large RAG service containing all strategies.

---

## 18. Definition of Done

The initial project setup is considered complete when:

- React frontend runs successfully.
- FastAPI backend runs successfully.
- PostgreSQL + pgvector is connected.
- A document can be uploaded.
- Document ingestion works.
- At least two chunking strategies can be selected.
- At least two retrieval strategies can be selected.
- Embedding strategy can be changed through configuration.
- Reranking can be enabled/disabled through configuration.
- RAG pipeline can execute end-to-end.
- Chatbot can answer questions using RAG.
- Responses can be streamed to the frontend.
- Evaluation can be executed against a dataset.
- Unit/integration/regression tests exist.
- Experiments can compare different RAG configurations.
- Changing a strategy does **not** require modifying the core RAG pipeline.
- README explains how to add a new strategy.

---

## Core Architectural Rule

> **Every RAG strategy must be implemented as a replaceable component behind a common interface. The core pipeline must depend on interfaces, not concrete implementations. Strategy selection must happen through configuration.**

This rule should be treated as the **highest-priority architectural requirement** for the entire learning project.
