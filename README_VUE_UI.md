# ValueStorm Vue.js Frontend

This document provides instructions for setting up and using the Vue.js frontend for the ValueStorm research assistant.

## Overview

The Vue.js frontend provides a modern, responsive user interface for:
- Starting new research projects
- Viewing research progress
- Browsing research results
- Exploring detailed research findings

## Setup Instructions

### Prerequisites

- Node.js (v14 or later)
- npm (v6 or later)
- Python 3.8+

### Installation

1. Clone the repository (if you haven't already):
   ```
   git clone <repository-url>
   cd MyValueStorm
   ```

2. Install Python dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Build the Vue.js frontend (one-time setup):
   ```
   cd frontend/vue-ui
   npm install
   npm run build
   cd ../..
   ```

4. Run the application:
   ```
   ./run_vue_app.sh
   ```

   This will start the Flask server that serves the Vue.js frontend.

### Development Setup

If you want to develop the Vue.js frontend:

1. Navigate to the Vue.js project directory:
   ```
   cd frontend/vue-ui
   ```

2. Install dependencies:
   ```
   npm install
   ```

3. Start the development server:
   ```
   npm run serve
   ```

4. In a separate terminal, start the Flask API server:
   ```
   python app_with_vue.py
   ```

## Architecture

The Vue.js frontend consists of:

- **Vue.js 3**: The progressive JavaScript framework for building user interfaces
- **Vue Router**: For handling navigation between different views
- **Vuex**: For state management
- **Axios**: For making API requests to the backend

The backend API is built with:

- **Flask**: A lightweight WSGI web application framework
- **Knowledge Storm**: The core research engine

## API Endpoints

The Vue.js frontend communicates with the following API endpoints:

- `GET /api/research/topics`: Get a list of previous research topics
- `POST /api/research/start`: Start a new research task
- `GET /api/research/progress/:id`: Get the progress of a research task
- `GET /api/research/results`: Get all research results
- `GET /api/research/results/:id`: Get a specific research result

## File Structure

- `frontend/vue-ui/`: Vue.js frontend code
  - `src/`: Source code
    - `assets/`: Static assets
    - `components/`: Vue components
    - `views/`: Vue views/pages
    - `router/`: Vue Router configuration
    - `store/`: Vuex store for state management
    - `services/`: API services
- `api/`: Flask API code
  - `research_api.py`: API endpoints for research functionality
- `app_with_vue.py`: Flask application that serves the Vue.js frontend
- `run_vue_ui.sh`: Script to set up and run the Vue.js frontend

## Using Both Interfaces

You can run both the Streamlit interface and the Vue.js interface simultaneously by setting the `RUN_BOTH` environment variable:

```
RUN_BOTH=true python app_with_vue.py
```

This will start:
- The Streamlit interface on port 8501 (default Streamlit port)
- The Vue.js interface on port 5000

## Troubleshooting

If you encounter issues:

1. Make sure all dependencies are installed:
   ```
   pip install -r requirements.txt
   cd frontend/vue-ui && npm install
   ```

2. Check if the Flask server is running:
   ```
   curl http://localhost:5000/api/health
   ```

3. Check the Flask server logs for errors

4. If the Vue.js build fails, try clearing the node_modules directory:
   ```
   cd frontend/vue-ui
   rm -rf node_modules
   npm install
   ```
