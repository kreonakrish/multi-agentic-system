# Multi-Agentic System

This project is a full-stack analytics and reporting platform featuring a modern React frontend, a Node.js API backend, and a Python machine learning service. It is designed for interactive analytics, agent-based data orchestration, and dynamic charting with a chat-like user experience.

## Features

- **React Frontend (client/):**
  - Facebook-like Material UI theme
  - Resizable left/right panes
  - Agent management and chat interface
  - ChatGPT-style chat window with support for bar, line, and pie charts
  - Dynamic chart rendering based on backend responses

- **Node.js API (node-api/):**
  - Serves as the main API gateway
  - Forwards analytics/chat requests to the Python ML backend

- **Python ML Service (python-ml/):**
  - Handles advanced analytics, ML, and data processing
  - Returns results and chart data to the Node.js API

## Project Structure

```
client/         # React frontend (TypeScript, Material UI)
node-api/       # Node.js backend API (Express)
python-ml/      # Python ML microservice (Flask or FastAPI)
```

## Getting Started

### Prerequisites
- Node.js (v18+ recommended)
- Python 3.8+

### 1. Install Dependencies

#### Frontend
```
cd client
npm install
```

#### Node API
```
cd ../node-api
npm install
```

#### Python ML Service
```
cd ../python-ml
pip install -r requirements.txt
```

### 2. Run the Services

#### Start the Python ML Service
```
cd python-ml
python main.py
```

#### Start the Node API
```
cd ../node-api
node index.js
```

#### Start the React Frontend
```
cd ../client
npm start
```

The frontend will be available at [http://localhost:3000](http://localhost:3000).

## Usage
- Use the left pane to manage agents and tools.
- Interact with the chat window in the center to ask analytics questions.
- The chat will display responses and render charts dynamically (bar, line, pie) based on backend data.
- The right pane provides settings and document management.

## Customization
- **Theme:** Edit `client/src/theme.jsx` for custom Material UI theming.
- **Agent Logic:** Extend agent logic in the frontend or backend as needed.
- **ML/Analytics:** Add new endpoints or models in `python-ml/main.py`.

## Development Notes
- The chat window currently uses a mock backend for chart data. Connect the Node API to the Python ML service for real analytics.
- All panes are resizable for a flexible UI.

## License
This project is open for public contribution and free to use for community benefit. Contributions, suggestions, and improvements are welcome from everyone. See the LICENSE file for details.

---

*For questions or contributions, please open an issue or pull request.*

