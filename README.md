# Voice RAG Chatbot

A full-stack application that combines voice interaction with Retrieval-Augmented Generation (RAG) to enable natural language conversations with PDF documents. Users can upload PDFs, ask questions about their content using voice or text, and receive intelligent answers with visual highlighting of relevant sections.

## 🚀 Features

- **PDF Document Processing**: Upload and parse PDF files with text and image extraction
- **Voice Interaction**: Speech-to-text 
- **RAG-powered Q&A**: Intelligent question answering using vector embeddings and retrieval
- **Hybrid Search**: Combines document search with web search for comprehensive answers
- **Visual Highlighting**: Automatically highlights relevant text sections in PDF pages

## 🏗️ Architecture

### Backend (FastAPI + Python)
- **FastAPI** web framework with CORS support
- **PyMuPDF** for PDF parsing and text extraction
- **Pinecone** vector database for embeddings storage
- **Google Generative AI** for answer generation
- **Serper API** for web search integration
- **NLTK** for text processing and chunking
- **PIL** for image processing and highlighting

### Frontend (Next.js + TypeScript)
- **Next.js 14** with TypeScript
- **Axios** for API communication
- **Web Speech API** for voice interaction

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.8+
- Node.js 16+
- Pinecone account and API key
- Google AI API key
- Serper API key (for web search)

### Backend Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/deepanshu-iitm/voice-rag-chatbot.git
   cd voice-rag-chatbot
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # macOS/Linux
   source venv/bin/activate
   ```

3. **Install Python dependencies**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   Create a `.env` file in the root directory:
   ```env
   PINECONE_API_KEY=your_pinecone_api_key
   PINECONE_ENVIRONMENT=your_pinecone_environment
   GOOGLE_API_KEY=your_google_ai_api_key
   SERPER_API_KEY=your_serper_api_key
   ```

5. **Start the backend server**
   ```bash
   cd backend
   uvicorn src.main:app --reload --port 8000
   ```

### Frontend Setup

1. **Install Node.js dependencies**
   ```bash
   cd frontend
   npm install
   ```

2. **Start the development server**
   ```bash
   npm run dev
   ```

The application will be available at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000












