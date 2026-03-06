# Testing Guide (Test-Driven Development)

This document outlines the testing strategy and Test-Driven Development (TDD) workflow for the United Degenerates League application. Adhering to this process is crucial for maintaining code quality, reducing bugs, and ensuring a stable, reliable application.

---

## Philosophy: Red, Green, Refactor

We follow the "Red, Green, Refactor" TDD cycle:

1.  **RED**: Before writing any implementation code, write a test that describes a new feature or improvement. Run the test and see it **fail**. This is the "Red" phase. This proves that the feature is not yet implemented and that your test works.

2.  **GREEN**: Write the *minimum* amount of code necessary to make the test pass. Don't worry about code quality at this stage. Just get to a passing state. This is the "Green" phase.

3.  **REFACTOR**: With the safety of a passing test, clean up your implementation code. Improve its structure, remove duplication, and enhance readability without changing its external behavior. The test should still pass.

---

## Backend Testing (Python, pytest)

The backend testing framework is built on `pytest`.

### Running Tests

To run all backend tests, navigate to the `backend` directory and run:

```bash
pytest
```

This command will automatically:
*   Discover all `test_*.py` files.
*   Run the tests.
*   Generate a code coverage report.
*   **Fail the test suite if code coverage drops below 80%**.

### TDD Workflow Example (Backend)

Let's say you need to add a new utility function to `app/core/utils.py` that formats a username.

1.  **RED**: First, create a test in `backend/tests/test_unit.py`:

    ```python
    # tests/test_unit.py
    from app.core import utils

    def test_format_username():
        assert utils.format_username(" john_doe ") == "John_Doe"
    ```
    Run `pytest`. It will fail because `format_username` doesn't exist.

2.  **GREEN**: Now, create the function in `app/core/utils.py` with the simplest possible implementation to make the test pass:

    ```python
    # app/core/utils.py
    def format_username(name: str) -> str:
        return name.strip().title()
    ```
    Run `pytest`. The test will now pass.

3.  **REFACTOR**: The code is already simple, but if it were more complex, this would be the time to clean it up, add comments, or improve performance, all while ensuring the test continues to pass.

### Test Types

*   **Unit Tests (`@pytest.mark.unit`)**: These test a single function or class in isolation. They should be fast and have no external dependencies (like a database or network). Place them in `tests/test_unit.py` or similar files.
*   **Integration Tests (`@pytest.mark.integration`)**: These test the interaction between multiple components, often including the database and API endpoints. They are found in `tests/test_critical_paths.py` and are essential for verifying user flows.

---

## Frontend Testing (React, Vitest)

The frontend testing framework uses `vitest` and `React Testing Library`.

### Running Tests

To run all frontend tests, navigate to the `frontend` directory and run:

```bash
npm test
```

To run tests in watch mode during development:
```bash
npm test -- --watch
```

### TDD Workflow Example (Frontend)

Imagine you need to add a "Login" button to the `HomePage.tsx` component.

1.  **RED**: First, create a test file `frontend/src/pages/HomePage.test.tsx`:

    ```tsx
    // src/pages/HomePage.test.tsx
    import { render, screen } from '@testing-library/react';
    import HomePage from './HomePage';

    it('should have a login button', () => {
      render(<HomePage />);
      expect(screen.getByRole('button', { name: /login/i })).toBeInTheDocument();
    });
    ```
    Run `npm test`. It will fail because the button doesn't exist.

2.  **GREEN**: Add the button to `HomePage.tsx`:

    ```tsx
    // src/pages/HomePage.tsx
    function HomePage() {
      return (
        <div>
          <h1>Welcome</h1>
          <button>Login</button>
        </div>
      );
    }
    export default HomePage;
    ```
    Run `npm test`. The test will now pass.

3.  **REFACTOR**: Now you can style the button, add an `onClick` handler, and structure the component better, knowing the test will fail if you accidentally remove the button.

### File Structure

Place test files directly alongside the component they are testing, using the `*.test.tsx` naming convention. For example, `Layout.tsx` and `Layout.test.tsx`.
