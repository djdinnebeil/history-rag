# 📜 Historical Research Assistant

A powerful AI-driven application for historical research that combines document management, vector search, and intelligent question-answering capabilities. Upload historical documents, organize them into projects, and ask sophisticated questions that leverage both your historical sources and current web information.

## 🌟 Features

### 📁 Project Management
- **Multi-Project Support**: Organize research into separate projects
- **Document Organization**: Categorize documents by type (books, journals, newspapers, reports, web articles, etc.)
- **Project Archiving**: Archive completed projects for storage

### 📄 Document Processing
- **Multiple Format Support**: Upload and process various document types
- **Intelligent Parsing**: Specialized parsers for different document categories
- **Batch Processing**: Efficient processing of multiple documents
- **Vector Embeddings**: Automatic conversion to searchable vector representations using OpenAI embeddings

### 🤖 AI-Powered Q&A
- **Dual Search Modes**:
  - **Standard Mode**: Search only within your uploaded historical documents
  - **Advanced Mode**: Combine historical documents with current web search results
- **LangGraph Agent**: Sophisticated AI agent that can reason about historical context
- **Contextual Retrieval**: Advanced retrieval with optional Cohere reranking
- **Chat History**: Track and review previous research conversations

### 🔍 Advanced Search & Filtering
- **Source Type Filtering**: Filter by document categories (books, journals, newspapers, etc.)
- **Year Range Filtering**: Focus on specific time periods
- **Dynamic Retrieval Scaling**: Automatically adjust search parameters based on query complexity
- **Vector Store Browsing**: Explore your document collection and embeddings

### 🛠️ Management Tools
- **Document Sync**: Keep your document database in sync with file changes
- **Pending Document Processing**: Track and process documents in batches
- **Vector Store Viewer**: Inspect and manage your document embeddings
- **Database Management**: Built-in tools for maintaining data integrity

## 🚀 Installation

### Prerequisites
- Python 3.8+
- OpenAI API key
- Cohere API key (optional, for reranking)
- Tavily API key (for web search in Advanced mode)

### Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd history-rag
   ```

2. **Install dependencies**:
   ```bash
   uv pip install -r requirements.txt
   ```

3. **Environment Configuration**:
   Create a `.env` file in the project root:
   ```env
   OPENAI_API_KEY=your_openai_api_key_here
   COHERE_API_KEY=your_cohere_api_key_here
   TAVILY_API_KEY=your_tavily_api_key_here
   ```

4. **Run the application**:
   ```bash
   streamlit run app.py
   ```

## 📖 Usage

### Getting Started

1. **Create a Project**: Start by creating a new research project or selecting an existing one
2. **Upload Documents**: Use the document uploader to add your historical sources
3. **Process Documents**: Run the batch processor to convert documents into searchable vectors
4. **Ask Questions**: Use the Q&A interface to research your historical documents

### Document Types Supported

- **Books**: Academic texts, historical volumes, reference materials
- **Journals**: Academic papers, research articles, periodicals
- **Newspapers**: Historical newspaper articles and clippings
- **Reports**: Government reports, institutional documents, studies
- **Web Articles**: Online sources and digital publications
- **Miscellaneous**: Any other document types
- **Unsorted**: Documents to be categorized later

### Search Modes

#### Standard Mode
Perfect for pure historical research using only your uploaded documents:
- Searches exclusively within your document collection
- Maintains historical context and authenticity
- Ideal for academic research and source verification

#### Advanced Mode
Combines historical documents with current information:
- Uses your historical documents as primary sources
- Supplements with current web search results
- Provides modern context and contemporary perspectives
- Excellent for understanding historical events' lasting impact

### Workflow Example

1. **Project Setup**:
   - Create project: "Industrial Revolution Research"
   - Upload relevant books, journal articles, and newspaper clippings

2. **Document Processing**:
   - Use the uploader to categorize documents by type
   - Run batch processing to create vector embeddings
   - Verify documents are properly synced

3. **Research**:
   - Ask: "What were the main social impacts of factory work on families?"
   - Filter by newspapers and journals from 1800-1850
   - Review sources and continue with follow-up questions

## ⚙️ Configuration

### Key Settings (config.py)

- **Models**: Configure OpenAI models for embeddings and chat
- **Vector Store**: Adjust chunk size and overlap for document processing
- **Retrieval**: Enable/disable dynamic retrieval scaling
- **Logging**: Control application logging levels
- **Feature Flags**: Enable/disable Cohere reranking

### Directory Structure

```
history-rag/
├── projects/          # Individual research projects
├── archive/          # Archived projects
├── components/       # UI components
├── core/            # Core functionality
├── utils/           # Utility functions
├── app.py           # Main application
├── config.py        # Configuration settings
└── requirements.txt # Dependencies
```

## 🔧 Technical Architecture

### Core Components

- **Vector Store**: Qdrant-based vector database for document embeddings
- **LangGraph Agent**: Sophisticated AI reasoning with tool integration
- **Retrieval Chain**: Advanced document retrieval with filtering and reranking
- **Document Parsers**: Specialized processing for different document types
- **Streamlit UI**: Interactive web interface for research workflows

### Data Flow

1. **Document Upload** → **Parsing** → **Chunking** → **Embedding** → **Vector Storage**
2. **User Query** → **Vector Search** → **Retrieval** → **LLM Processing** → **Response**
3. **Advanced Mode**: Includes web search integration for comprehensive answers

## 🛡️ Privacy & Security

- All document processing happens locally
- Vector embeddings stored in local Qdrant instance
- API keys securely managed through environment variables
- No document content sent to external services except for embedding generation

## 🤝 Contributing

This is a research tool designed for historical analysis. Contributions welcome for:
- Additional document parsers
- Enhanced search capabilities
- UI improvements
- Performance optimizations

## 🆘 Support

For issues, questions, or feature requests:
1. Check the application logs (configurable in `config.py`)
2. Review the document sync status in the management tools
3. Verify API key configuration in your `.env` file
