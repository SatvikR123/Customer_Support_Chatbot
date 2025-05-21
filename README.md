# boAt Customer Support Chatbot

A Retrieval-Augmented Generation (RAG) based chatbot for boAt customer support that provides information about return policies and service center locations.

## Overview

This project implements an advanced RAG system using ChromaDB as its vector database and a multi-agent architecture for intelligent query processing and response generation. The system integrates web scraping, data processing, and a modern web interface to provide accurate customer support information.

## Features

- Multi-agent architecture for sophisticated query processing and response generation
- Web scraping capabilities using Playwright for dynamic content
- Text preprocessing using Google's Gemini API
- Direct data loading pipeline for efficient processing
- Advanced data validation and quality assurance
- Vector database storage using ChromaDB with SentenceTransformer embeddings
- Modern web interface with real-time chat capabilities
- Query classification and intelligent routing
- Comprehensive API server implementation
- Automated testing suite for all components

## Project Structure

```
├── data/                     # Data storage directory
│   ├── chroma/              # ChromaDB persistence
│   └── debug/               # Debug outputs and screenshots
├── src/
│   ├── agents/              # Multi-agent system components
│   │   ├── agent_system.py  # Core agent system
│   │   ├── autogen_wrapper.py # AutoGen integration
│   │   ├── orchestrator.py  # Agent orchestration
│   │   ├── query_analyzer.py # Query analysis
│   │   ├── response_generator.py # Response generation
│   │   └── retrieval_agent.py # Information retrieval
│   ├── api/                 # API server implementation
│   │   ├── server.py        # FastAPI server
│   │   └── static/          # Static assets
│   ├── backend/             # Backend services
│   │   └── app.py          # Main application logic
│   ├── chatbot/            # Core chatbot components
│   │   └── rag_engine.py   # RAG implementation
│   ├── database/           # Database interactions
│   │   └── vector_store.py # ChromaDB integration
│   ├── frontend/           # Web interface
│   │   ├── index.html      # Main page
│   │   ├── script.js       # Frontend logic
│   │   └── styles.css      # Styling
│   ├── scraper/            # Web scraping tools
│   │   ├── playwright_scraper.py # Playwright implementation
│   │   └── web_scraper.py  # Base scraper class
│   └── utils/              # Utility functions
│       ├── data_pipeline.py # Data processing
│       ├── data_validator.py # Validation tools
│       ├── direct_loader.py # Direct data loading
│       ├── gemini_processor.py # Gemini API integration
│       └── test_pipeline.py # Testing utilities
├── scripts/                 # Script files and PRD
├── tests/                  # Test files and data
├── requirements.txt        # Project dependencies
├── run.py                 # Main entry point
└── .env                   # Environment configuration
```

## Installation

1. Clone this repository:

   ```bash
   git clone https://github.com/yourusername/boat-customer-support-chatbot.git
   cd boat-customer-support-chatbot
   ```

2. Create and activate a virtual environment:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file with your API keys:
   ```
   GOOGLE_API_KEY=your_gemini_api_key
   CHROMA_PERSIST_DIRECTORY=./data/chroma
   # Add other necessary API keys and configurations
   ```

## Usage

### Running the Application

Start the main application:

```bash
python run.py
```

This will:

- Initialize the agent system
- Start the API server
- Launch the web interface
- Begin processing user queries

### Web Scraping

To update the service center and return policy data:

```bash
python -m src.scraper.playwright_scraper
```

### Direct Data Loading

To process and load data without using the Gemini API:

```bash
python direct_load.py
```

### Testing

Run the test suite:

```bash
python test_database.py
python test_direct_loader.py
```

## Implementation Details

### Multi-Agent Architecture

- Orchestrator Agent: Coordinates between different specialized agents
- Query Analyzer: Classifies and processes user queries
- Retrieval Agent: Handles vector database interactions
- Response Generator: Creates natural language responses

### Vector Database

- ChromaDB with custom embedding functions
- Separate collections for different types of information
- Optimized retrieval strategies for each query type

### Web Interface

- Real-time chat interface
- Responsive design
- Error handling and loading states
- Session management

### API Server

- FastAPI implementation
- RESTful endpoints
- WebSocket support for real-time communication
- Comprehensive error handling

## Dependencies

- Python 3.8+
- ChromaDB
- Playwright
- FastAPI
- Google Generative AI (Gemini)
- Sentence Transformers
- AutoGen
- Additional requirements in requirements.txt

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- boAt Lifestyle for inspiration
- Google for the Gemini API
- The ChromaDB team for the vector database
- Microsoft for the AutoGen framework

---

Note: This is a demo project and not officially affiliated with boAt Lifestyle.
