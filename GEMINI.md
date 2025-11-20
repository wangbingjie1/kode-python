# GEMINI.md: Your Guide to the Kode Project
必须中文回复和思考，第一性原理解决根本问题，像一个老程序员一样写代码，比如Linux，只给最靠谱的建议和方案，不确定不推荐，不要说废话，不要生成说明文档，我不会看你文档的。生成的脚本和代码，要自己先测试通过，再告诉用户，用户有选择困难症，你可以向他提问，但不要给他选项，我不要你的速度，我要你的质量
doc目录 存放你生成的说明文档
test目录 存放你生成的测试代码
永远不要写降级方案
要用批判性思维思考用户的问题和自己的解决方案
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
