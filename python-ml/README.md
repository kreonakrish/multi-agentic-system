# Multi-Agent ML Service

A Flask-based microservice for managing multi-agent interactions and ML operations.

## Features

- Agent management and interactions
- Team coordination and task distribution
- Tool integration (Database, API, Web Service)
- Comprehensive logging and monitoring
- Database connection pooling
- Error handling and recovery
- Metrics tracking

## Project Structure

```
python-ml/
├── app/
│   ├── config/         # Configuration files
│   ├── core/           # Core functionality
│   ├── database/       # Database management
│   ├── models/         # Data models
│   ├── routes/         # API routes
│   ├── services/       # Business logic
│   └── utils/          # Utilities
├── tests/              # Test files
├── logs/               # Log files
├── .env.example        # Environment variables example
├── requirements.txt    # Dependencies
└── main.py            # Application entry point
```

## Setup

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` and configure:
   ```bash
   cp .env.example .env
   ```

4. Configure environment variables:
   ```
   DB_HOST=localhost
   DB_USER=admin
   DB_PASSWORD=your_password
   DB_NAME=multi_agentic_system
   OPENAI_API_KEY=your_api_key
   ```

## Running the Service

1. Start the service:
   ```bash
   python main.py
   ```

   Or with Gunicorn (production):
   ```bash
   gunicorn -w 4 -b 0.0.0.0:5000 main:app
   ```

2. The service will be available at `http://localhost:5000`

## API Endpoints

### Agent Management

- `POST /api/ml/agent/<agent_id>/initialize`
  - Initialize an agent

- `POST /api/ml/agent/<agent_id>/send`
  - Send a message from an agent

- `POST /api/ml/agent/<agent_id>/receive/<interaction_id>`
  - Receive a message for an agent

- `POST /api/ml/agent/<agent_id>/execute_all`
  - Execute all tools for an agent

### Team Management

- Team-related endpoints (documentation pending)

### Tool Management

- Tool-related endpoints (documentation pending)

## Logging

Logs are stored in the `logs` directory with the following format:
- Console: Basic information
- File: Detailed information including line numbers
- Rotation: 10MB file size, 5 backup files

## Development

1. Running tests:
   ```bash
   python -m pytest tests/
   ```

2. Code formatting:
   ```bash
   black .
   ```

3. Type checking:
   ```bash
   mypy .
   ```

## Error Handling

The service includes comprehensive error handling:
- Database connection failures
- API request errors
- Invalid input validation
- Runtime exceptions

## Metrics

The service tracks various metrics:
- Agent performance
- Team efficiency
- Task completion rates
- Response times

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 