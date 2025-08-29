# 🤖 PRMS Chatbot & Embedding Service

An intelligent service that combines conversational chat capabilities with embedding generation and storage for **PRMS (Performance Result Manangement System)** applications.

---

## 🌟 Key Features

### 💬 Chat Mode with RAG

- Intelligent conversations with Anthropic's Claude 3.7 Sonnet model
- Semantic search through Retrieval Augmented Generation (RAG)
- Relevant context automatically retrieved from vector database
- Accurate responses based on PRMS documentation and knowledge base

### 🧠 Embedding Generation

- Text vectorization with Amazon Titan Embed Text v2
- Efficient storage in Supabase Vector
- Q&A pair management for medical knowledge training
- Semantic similarity search for healthcare content

---

## 🔧 Technical Architecture

- **Language Models**: AWS Bedrock Runtime for chat and embeddings
- **Vector Database**: Supabase Vector
- **Configuration**: Centralized AWS and Supabase settings
- **Logging**: Structured monitoring and debugging

---

## 📂 Project Structure

```
ai-support-chatbot/
├── app/
│   ├── llm/
│   │   ├── chat_model.py          # Chat model with RAG
│   │   ├── generate_embeddings.py # Embedding generation
│   │   ├── store_vectors.py       # Supabase storage
│   │   ├── setup_supabase.py      # Supabase configuration
│   │   └── test_connection.py     # Connectivity tests
│   └── utils/
│       ├── logger/
│       │   └── logger_util.py     # Logging utilities
│       └── prompt/
│           └── prompt_prms_support.py # System prompts
├── main.py                        # Main application
├── requirements.txt               # Dependencies
└── .env                           # Environment variables
```

---

## 🛠️ Technology Stack

- 🤖 **Language Models**: AWS Bedrock (Anthropic Claude 3.7 Sonnet)
- 🔢 **Embeddings**: AWS Titan Embed Text v2
- 🗄️ **Vector Database**: Supabase Vector
- 🐍 **Language**: Python 3.8+
- 📊 **Logging**: Custom structured logging
- 🔐 **Authentication**: AWS IAM + Supabase Connection String

---

## 📋 Prerequisites

### Accounts and Services

- ✅ AWS Account with Bedrock Runtime access
- ✅ Supabase Service with Vector extension enabled
- ✅ IAM Credentials with Bedrock permissions

### Environment Variables

```bash
# AWS Configuration
AWS_ACCESS_KEY=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=us-east-1

# Supabase Configuration
DB_SUPABASE_CONNECTION=your_supabase_connection_string
SUPABASE_COLLECTION=your_collection_name
```

---

## 🚀 Installation and Setup

### 1. Clone and Setup Environment

```bash
git clone git clone https://github.com/AllianceBioversityCIAT/ai-services.git
cd ai_support_chatbot
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate   # Windows
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

```bash
cp .env.example .env
# Edit .env with your credentials
```

### 4. Test Connections

```bash
python -m app.llm.test_connection
```

---

## 💻 Usage

### Interactive Mode

```bash
python main.py
```

### Available Options

- 💬 **Chat with AI Model**: Interactive conversation with RAG
- 🧠 **Generate Embeddings**: Store new Q&A pairs for medical knowledge
- 🚪 **Exit**: Terminate the application

### Typical Workflow

1. Generate embeddings from PRMS documentation and knowledge base
2. Chat to get contextual responses about patient-reported measures
3. Add more knowledge as needed for specific medical domains

---

## 🔧 Advanced Configuration

### Supported Models

- `amazon.titan-embed-text-v2:0` (Embeddings)
- `us.anthropic.claude-3-7-sonnet-20250219-v1:0` (Chat)

### Adjustable Parameters

- **Temperature**: Response creativity control
- **Top-K**: Token sampling
- **Token Limit**: Maximum response length
- **Embedding Size**: 1024 dimensions

---

## 📊 Monitoring and Logging

The system includes detailed logging for:

- ✅ Successful connections
- ⚠️ Configuration warnings
- ❌ Execution errors
- 🔍 Query and response debugging
