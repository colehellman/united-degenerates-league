# Deployment Readiness TODO List

This document outlines critical, high-priority, and medium-priority tasks that should be completed to ensure the application is secure, stable, and ready for a production deployment.

---

## 🟥 Critical

These issues pose significant security or stability risks and must be addressed before any production deployment.

-   **[x] Prevent Seed Script from Running in Production:** ✅ Fixed — `seed_data.py` now exits with error if `ENVIRONMENT=production`
    -   **File**: `backend/scripts/seed_data.py`

-   **[ ] Remove Hardcoded Credentials from Configuration:**
    -   **File**: `backend/app/core/config.py`
    -   **Issue**: The `DATABASE_URL` is hardcoded with default credentials. This is a major security risk.
    -   **Action**: Modify the `Settings` class to load `DATABASE_URL` *only* from environment variables. The application should fail to start if the variable is not set. Remove the default value from the class definition.

-   **[ ] Strengthen Default `SECRET_KEY`:**
    -   **File**: `backend/app/core/config.py`
    -   **Issue**: The default `SECRET_KEY` is a well-known, weak string ("dev-secret-key-change-in-production"). While there's a startup check, a compromised development environment could still leak this key.
    -   **Action**: Change the default value to `None` or an empty string and make the `SECRET_KEY` a required environment variable for the app to start, regardless of the environment.

---

## 🟧 High Priority

These issues could lead to instability, poor performance, or security vulnerabilities in a production environment.

-   **[ ] Add Missing Production Environment Variables:**
    -   **File**: `render.yaml`
    -   **Issue**: The deployment configuration is missing environment variables for the various sports APIs (`ESPN_API_KEY`, `THE_ODDS_API_KEY`, etc.) and `SENTRY_DSN`. Without them, these integrations will fail silently or not be configured.
    -   **Action**: Add placeholders for all required API keys and the Sentry DSN to the `envVars` section of the `udl-api` service in `render.yaml`.

-   **[ ] Refactor Backend Dockerfile for Production:**
    -   **File**: `backend/Dockerfile`
    -   **Issue**: The Dockerfile is not optimized for production. It's a single-stage build and has inefficient layer caching, leading to longer build times and a larger image size.
    -   **Action**:
        1.  Convert to a multi-stage build. Use a `builder` stage to install dependencies (including dev dependencies needed for compilation like `gcc`).
        2.  In the final stage, copy only the necessary files and installed packages from the `builder` stage onto a slim base image.
        3.  Optimize layer caching by copying `requirements.txt` and running `pip install` *before* copying the rest of the application code.

-   **[x] Configure Generic Error Messages in Production:** ✅ Fixed — exception handler returns generic message unless `ENVIRONMENT=development`
    -   **File**: `backend/app/main.py`

-   **[ ] Clarify and Configure Worker Deployment:**
    -   **Files**: `render.yaml`, `worker.py`, `Procfile`, `Dockerfile.worker`
    -   **Issue**: The project contains files for a separate worker (`worker.py`, `Dockerfile.worker`), but the `render.yaml` deploys the background jobs in the same process as the API (`DISABLE_BACKGROUND_JOBS: "false"`). This is not ideal for scaling and reliability.
    -   **Action**:
        1.  Decide on the production worker strategy. (Recommended: a separate worker process).
        2.  If a separate worker is chosen, add a new service of type `worker` to `render.yaml` using `Dockerfile.worker`.
        3.  Update the `udl-api` service's `envVars` in `render.yaml` to set `DISABLE_BACKGROUND_JOBS` to `"true"`.

---

## 🟨 Medium Priority

These are recommended improvements for better maintainability, performance, and adherence to best practices.

-   **[ ] Review and Update Dependencies:**
    -   **Files**: `backend/requirements.txt`, `frontend/package.json`
    -   **Issue**: Dependencies are likely outdated and have loose version constraints. Unpinned dependencies can lead to unexpected issues in new deployments, and outdated packages can contain security vulnerabilities.
    -   **Action**:
        1.  Use `npm outdated` and `pip list --outdated` to identify outdated packages.
        2.  Research and update critical and major version differences.
        3.  For Python, consider using a tool like `pip-tools` to create a fully pinned `requirements.txt` from a `requirements.in` file for reproducible builds.
