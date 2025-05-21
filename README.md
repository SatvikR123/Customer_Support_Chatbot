# boAt Customer Support Chatbot

A Retrieval-Augmented Generation (RAG) based chatbot for boAt customer support that provides information about return policies and service center locations.

## Overview

This project implements a RAG system using ChromaDB as its vector database for storing and retrieving information, and leverages the Gemini API for both text processing and response generation. The current implementation focuses on the data ingestion pipeline and vector database setup for Task 3.

## Features

- Text preprocessing of scraped content using Google's Gemini API
- Data validation to ensure quality of processed information
- Vector database storage using ChromaDB with SentenceTransformer embeddings
- Query classification to route questions to the appropriate information source
- Retrieval of relevant documents based on semantic similarity
- Basic RAG implementation for testing database functionality

## Project Structure

```
├── data/                    # Data storage directory
├── src/
│   ├── chatbot/             # Chatbot core components
│   │   └── rag_engine.py    # Core RAG implementation
│   ├── database/
│   │   └── vector_store.py  # ChromaDB integration
│   └── utils/
│       ├── data_pipeline.py # Data processing pipeline
│       ├── data_validator.py # Data validation utilities
│       ├── gemini_processor.py # Text processing with Gemini
│       └── test_pipeline.py # Test utilities
├── test_database.py         # Test script for database functionality
└── task3_runner.py          # Runner for Task 3 demonstration
```

## Installation

1. Clone this repository:

   ```
   git clone https://github.com/yourusername/boat-customer-support-chatbot.git
   cd boat-customer-support-chatbot
   ```

2. Create and activate a virtual environment:

   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

4. Create a `.env` file with your API keys:
   ```
   GOOGLE_API_KEY=your_gemini_api_key
   CHROMA_PERSIST_DIRECTORY=./data/chroma
   ```

## Usage

### Setting up the Data

Before using the vector database, you need to set up the data pipeline. This can be done using the included test data:

```bash
python task3_runner.py setup --test-data
```

Or with your own scraped data placed in the `data/` directory:

```bash
python task3_runner.py setup
```

### Testing the Database

To run a comprehensive test of the database functionality:

```bash
python test_database.py
```

### Interactive Query Interface

To query the vector database directly:

```bash
python task3_runner.py query
```

### RAG Demo

To test the RAG engine with the vector database:

```bash
python task3_runner.py rag --question "What is boAt's return policy for damaged items?"
```

## Task 3 Implementation Details

### ChromaDB Setup

- Implemented custom embedding function using SentenceTransformer to address NumPy 2.0 compatibility issues
- Created separate collections for return policy and service center information
- Set up persistence for embeddings and metadata

### Embedding Strategy

- Using SentenceTransformer with "all-MiniLM-L6-v2" model
- Return policy documents are embedded as complete policy chunks
- Service center locations are embedded with state, address, and contact information

### Data Ingestion Pipeline

- Process scraped data using Gemini API to structure the information
- Validate data structure and content using schema validation
- Transform processed data into vector-ready documents
- Load documents into appropriate ChromaDB collections

### Retrieval Functions

- Implemented semantic search for both return policy and service center information
- Added query classification to route questions to the appropriate collection
- Created metadata-enhanced results for better context in responses

## Dependencies

- Python 3.8+
- ChromaDB
- Google Generative AI (Gemini)
- Sentence Transformers

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- boAt Lifestyle for inspiration
- Google for the Gemini API
- The ChromaDB team for the vector database

---

Note: This is a demo project and not officially affiliated with boAt Lifestyle.
