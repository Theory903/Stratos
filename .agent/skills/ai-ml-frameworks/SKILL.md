---
name: ai-ml-frameworks
description: AI/ML framework standards — LangChain, LlamaIndex, Transformers, scikit-learn, PyTorch, RAG patterns, agent architectures, and model deployment
---

# AI/ML Frameworks

## LangChain (0.2+)

### Structure
```
src/
├── chains/           # LangChain chain definitions
├── agents/           # Agent configurations
├── prompts/          # Prompt templates (stored as files)
├── retrievers/       # RAG retriever logic
├── tools/            # Custom tool definitions
├── memory/           # Conversation memory
└── callbacks/        # Logging, tracing callbacks
```

### Rules
- **Store prompts in separate files** — version-control and iterate independently.
- **Use Pydantic for structured output** — parse LLM responses into typed objects.
- **Wrap LLM calls in try-except** — handle rate limits, timeouts, malformed responses.
- **Use caching** for expensive operations (`InMemoryCache`, `SQLiteCache`).
- **Trace with LangSmith** for debugging and evaluation.

### Patterns
```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

class AnalysisResult(BaseModel):
    sentiment: str = Field(description="positive, negative, or neutral")
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str

parser = PydanticOutputParser(pydantic_object=AnalysisResult)
prompt = ChatPromptTemplate.from_messages([
    ("system", "Analyze the following text. {format_instructions}"),
    ("user", "{text}"),
])

chain = prompt | ChatOpenAI(temperature=0) | parser
result: AnalysisResult = await chain.ainvoke({
    "text": "...",
    "format_instructions": parser.get_format_instructions(),
})
```

### RAG Pattern
```python
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.chains import RetrievalQA

vectorstore = Chroma.from_documents(documents, OpenAIEmbeddings())
retriever = vectorstore.as_retriever(search_kwargs={"k": 5})

qa_chain = RetrievalQA.from_chain_type(
    llm=ChatOpenAI(temperature=0),
    retriever=retriever,
    return_source_documents=True,
)
```

---

## LlamaIndex (0.10+)

### Rules
- **Proper metadata extraction** — enrich documents with structured metadata.
- **Choose index type wisely**: VectorStoreIndex (default), TreeIndex (hierarchical), KeywordTableIndex.
- **Customize query engine** for your use case.

### Patterns
```python
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding

Settings.llm = OpenAI(model="gpt-4o", temperature=0)
Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")

documents = SimpleDirectoryReader("data").load_data()
index = VectorStoreIndex.from_documents(documents)
query_engine = index.as_query_engine(similarity_top_k=5, response_mode="compact")
response = query_engine.query("What are the key risk factors?")
```

---

## HuggingFace Transformers

### Rules
- **Set `cache_dir`** for model caching.
- **Use quantization** (bitsandbytes, GPTQ) for inference optimization.
- **Batch process** for efficiency.
- **Use pipelines** for common tasks.

```python
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
import torch

# Simple pipeline
classifier = pipeline(
    "text-classification",
    model="ProsusAI/finbert",
    device=0 if torch.cuda.is_available() else -1,
)
results = classifier(["Markets rallied today", "Revenue declined sharply"])

# Custom loading with quantization
tokenizer = AutoTokenizer.from_pretrained("model-name")
model = AutoModelForSequenceClassification.from_pretrained(
    "model-name",
    torch_dtype=torch.float16,
    device_map="auto",
)
```

---

## scikit-learn

### Rules
- **Always use pipelines** to chain preprocessing and models.
- **Cross-validate** — never evaluate on training data.
- **Use stratified splits** for imbalanced data.

```python
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score, StratifiedKFold

pipeline = Pipeline([
    ("scaler", StandardScaler()),
    ("classifier", RandomForestClassifier(random_state=42, n_jobs=-1)),
])

scores = cross_val_score(
    pipeline, X, y,
    cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=42),
    scoring="f1_weighted",
)
```

---

## PyTorch

### Rules
- **Use `torch.no_grad()`** for inference.
- **Move data to device** consistently. Use `device = torch.device("cuda" if torch.cuda.is_available() else "cpu")`.
- **Use `DataLoader`** for batching.
- **Save with `state_dict`** for portability.

```python
import torch
import torch.nn as nn

class FinancialModel(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int, output_dim: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_dim, output_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)

# Save/Load
torch.save(model.state_dict(), "model.pt")
model.load_state_dict(torch.load("model.pt", weights_only=True))
```

---

## Agent Architecture Patterns

### Tool-Calling Agent
```python
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.tools import tool

@tool
def analyze_company(ticker: str) -> dict:
    """Analyze a company's financials given its stock ticker."""
    return fetch_financial_data(ticker)

agent = create_tool_calling_agent(llm, [analyze_company], prompt)
executor = AgentExecutor(agent=agent, tools=[analyze_company], verbose=True)
result = await executor.ainvoke({"input": "Analyze AAPL"})
```

### Multi-Agent (LangGraph)
- Use LangGraph for complex multi-agent workflows.
- Define agents as nodes, edges as communication.
- Use state machines for workflow control.

---

## Key Libraries

| Library | Purpose |
|---|---|
| langchain | LLM chains, agents, RAG |
| llama-index | Document indexing, retrieval |
| transformers | Pre-trained models |
| scikit-learn | Classical ML pipelines |
| torch / pytorch | Deep learning |
| sentence-transformers | Embeddings |
| chromadb / pinecone | Vector databases |
| langsmith | LLM tracing & evaluation |
| mlflow | Experiment tracking |
| onnxruntime | Model inference optimization |
