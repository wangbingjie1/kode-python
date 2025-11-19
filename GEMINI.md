# GEMINI.md: Your Guide to the Kode Project

This document provides a comprehensive overview of the Kode project, an AI-native coding assistant. It's designed to help developers understand the project structure, how to build and run it, and the development conventions to follow.

## Project Overview

Kode is a full-stack web application that functions as an AI-powered coding assistant. It's built with a modern technology stack, featuring a Python backend and a Vue.js frontend.

*   **Backend:**
    *   **Framework:** FastAPI
    *   **AI Integration:** LangChain, with support for Anthropic and OpenAI models.
    *   **Database:** SQLAlchemy ORM with Alembic for migrations, supporting PostgreSQL.
    *   **Dependency Management:** Poetry
    *   **Key Features:** Real-time chat, project management, database introspection, user authentication, billing and subscription management, and plugin support for various tools.

*   **Frontend:**
    *   **Framework:** Vue.js 3 with Vite
    *   **Language:** TypeScript
    *   **State Management:** Pinia
    *   **Styling:** Tailwind CSS
    *   **API Communication:** Axios
    *   **Key Features:** A rich user interface for interacting with the AI assistant, including a chat interface, context panel, database schema viewer, and real-time updates via Server-Sent Events (SSE).

*   **Operations:**
    *   **Containerization:** The entire application is containerized using Docker and managed with Docker Compose.
    *   **Deployment:** The project includes configurations for both development and production environments, with Nginx serving as a reverse proxy in production.

## Building and Running

The recommended way to run the project is by using Docker.

### Prerequisites

*   Docker
*   Docker Compose

### Running with Docker (Recommended)

1.  **Set up environment variables:**
    ```bash
    cp .env.example .env
    ```
    Edit the `.env` file to include your API keys and other necessary configurations.

2.  **Build and start the services:**
    The `Makefile` provides convenient shortcuts for managing the Docker containers.

    *   **Start in development mode:**
        ```bash
        make up
        ```
    *   **Start in production mode (with Nginx):**
        ```bash
        make prod-up
        ```
    *   **Stop the services:**
        ```bash
        make down
        ```
    *   **View logs:**
        ```bash
        make logs
        ```

3.  **Database Migrations:**
    The first time you start the application, you need to run the database migrations.
    ```bash
    make db-migrate
    ```

### Running Manually (for development)

#### Backend

1.  **Install dependencies using Poetry:**
    ```bash
    poetry install
    ```

2.  **Run the FastAPI server:**
    ```bash
    poetry run uvicorn kode.web.main:app --host 0.0.0.0 --port 8001 --reload
    ```
    Alternatively, you can run the `run.py` script:
    ```bash
    poetry run python run.py
    ```

#### Frontend

1.  **Navigate to the frontend directory:**
    ```bash
    cd web-frontend
    ```

2.  **Install dependencies:**
    ```bash
    npm install
    ```

3.  **Start the development server:**
    ```bash
    npm run dev
    ```

### Accessing the Application

*   **Frontend:** [http://localhost:3000](http://localhost:3000)
*   **Backend API:** [http://localhost:8001](http://localhost:8001)
*   **API Docs (Swagger UI):** [http://localhost:8001/docs](http://localhost:8001/docs)

## Development Conventions

### Backend

*   **Code Style:** The project uses `black` for code formatting and `ruff` for linting. Please format your code before committing.
*   **Type Checking:** `mypy` is used for static type checking.
*   **Testing:** Tests are written using `pytest` and are located in the `test/` directory.

### Frontend

*   **Code Style:** The project uses `eslint` with the TypeScript and Vue.js plugins for linting.
*   **Dependencies:** Manage frontend dependencies using `package.json`.
