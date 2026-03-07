# United Degenerates League (UDL) - Developer Documentation

## Introduction

This document provides a comprehensive overview of the United Degenerates League (UDL) application for developers. It covers the architecture, setup, development, deployment, and testing of the application.

## Architecture

The UDL application is a modern web application with a decoupled frontend and backend.

*   **Frontend**: A Single Page Application (SPA) built with React, Vite, and TypeScript.
*   **Backend**: A Python-based API built with FastAPI, SQLAlchemy, and PostgreSQL.
*   **Services**:
    *   **PostgreSQL**: The primary database for the application.
    *   **Redis**: Used for caching and background jobs.
*   **Deployment**: The application is designed to be deployed using Docker and can be hosted on platforms like Render.

## Getting Started (Local Development)

For a complete guide on setting up the project for local development, please refer to the main [README.md](README.md) file. It provides a step-by-step guide on how to get the entire application stack running with Docker Compose.

## Frontend

The frontend is a single-page application built with React.

### Technologies

*   **React**: The core UI library.
*   **Vite**: The build tool and development server.
*   **TypeScript**: For static typing.
*   **React Router**: For client-side routing.
*   **Zustand**: For state management.
*   **TanStack Query**: For data fetching and caching.
*   **Axios**: For making HTTP requests to the backend API.
*   **Tailwind CSS**: For styling.
*   **Vitest**: For unit and integration testing.

### Project Structure

The frontend code is located in the `frontend` directory.

```
frontend/
├── src/
│   ├── components/      # Reusable UI components
│   ├── hooks/           # Custom React hooks
│   ├── pages/           # Application pages
│   ├── services/        # API services and state management
│   ├── styles/          # Global styles
│   ├── types/           # TypeScript types
│   ├── utils/           # Utility functions
│   ├── App.tsx          # Main application component
│   └── main.tsx         # Application entry point
├── package.json         # Project dependencies and scripts
└── vite.config.ts     # Vite configuration
```

### Getting Started

1.  **Navigate to the frontend directory:**
    ```bash
    cd frontend
    ```
2.  **Install dependencies:**
    ```bash
    npm install
    ```
3.  **Run the development server:**
    ```bash
    npm run dev
    ```
    The frontend will be available at `http://localhost:3000`.

### Building for Production

To create a production build of the frontend, run the following command:

```bash
npm run build
```

This will create a `dist` directory with the optimized static assets.

## Backend

The backend is a RESTful API built with Python and FastAPI.

### Technologies

*   **FastAPI**: The web framework for building the API.
*   **SQLAlchemy**: The ORM for interacting with the database.
*   **Alembic**: For database migrations.
*   **Pydantic**: For data validation and settings management.
*   **PostgreSQL**: The relational database.
*   **Redis**: For caching and background tasks.
*   **Uvicorn**: The ASGI server to run the application.

### Project Structure

The backend code is located in the `backend` directory.

```
backend/
├── app/
│   ├── api/           # API endpoint definitions
│   ├── core/          # Core application logic (config, security)
│   ├── db/            # Database session management
│   ├── models/        # SQLAlchemy ORM models
│   ├── schemas/       # Pydantic schemas for data validation
│   └── services/      # Business logic and services
│   └── main.py        # FastAPI application entry point
├── alembic/           # Alembic migration scripts
├── requirements.txt   # Python dependencies
└── Dockerfile         # Dockerfile for building the backend image
```

## Database

### Migrations

Database migrations are managed with Alembic.

*   **To apply migrations:**
    ```bash
    docker-compose exec backend alembic upgrade head
    ```
*   **To create a new migration after changing a model:**
    ```bash
    docker-compose exec backend alembic revision --autogenerate -m "Your migration message"
    ```

### Seeding

The project includes a script to seed the database with sample data.

*   **To run the seed script:**
    ```bash
    docker-compose exec backend python -m scripts.seed_data
    ```

## Services

### PostgreSQL

*   **Description**: The primary relational database for the application.
*   **Configuration**: Defined in `docker-compose.yml`.
*   **Access**: Port `5432` is exposed on the host for local connections.

### Redis

*   **Description**: Used for caching and as a message broker for background jobs.
*   **Configuration**: Defined in `docker-compose.yml`.
*   **Access**: Port `6379` is exposed on the host.

## MCP Server (Gemini Code Assist)

The `mcp_server` directory contains a Python server that extends Gemini Code Assist with Playwright capabilities. This allows the AI assistant to run browser automation scripts.

### Purpose

This server listens for requests from the Gemini Code Assist extension and executes Playwright scripts to perform browser automation tasks. This can be used for tasks like automated testing, web scraping, or other interactions with web pages.

### Getting Started

1.  **Navigate to the `mcp_server` directory:**
    ```bash
    cd mcp_server
    ```
2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Install Playwright browsers:**
    ```bash
    playwright install
    ```
4.  **Run the server:**
    ```bash
    uvicorn main:app --reload --port 8001
    ```

For more details on configuring this with your IDE, see `mcp_server/README.md`.

## Testing

### Backend

The backend has a suite of tests using `pytest`.

*   **To run the tests:**
    ```bash
    docker-compose exec backend pytest
    ```

### Frontend

The frontend uses Vitest for unit and component testing.

*   **To run the tests:**
    ```bash
    cd frontend
    npm test
    ```

## Deployment

The application is designed for containerized deployments. The `render.yaml` file provides a blueprint for deploying to Render. For other platforms, you can use a standard Docker deployment.

1.  **Build the Docker images:**
    ```bash
    docker-compose build
    ```
2.  **Push the images to a container registry** (e.g., Docker Hub, Google Container Registry).
3.  **Deploy the images** to your hosting provider, ensuring all environment variables from `backend/.env.example` are set.
4.  **Run database migrations** in your production environment.
