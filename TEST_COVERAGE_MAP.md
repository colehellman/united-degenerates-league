# Test Coverage Map

This document provides a high-level and file-level overview of test coverage
across the project. Claude must update this file whenever:

- New tests are added
- Existing tests are modified
- Code changes shift test responsibilities
- New modules, components, or features are created
- Files are moved or renamed

This file is both a reference and a working checklist for maintaining adequate
test coverage and ensuring critical paths are validated.

---

# 1. Overview

## 1.1 Current Test Strategy
Describe the main testing frameworks, tools, and conventions used in the project:

- Framework: (Claude will fill)
- Test directory structure: (Claude will fill)
- Mocking / stubbing approach: (Claude will fill)
- Integration vs unit test breakdown: (Claude will fill)

Claude should update this section as the test strategy evolves.

---

# 2. Coverage Summary by Major Area

Claude must maintain this table to reflect which areas of the application have
full, partial, or missing test coverage.

| Area / Module | Purpose | Coverage Level | Notes |
|---------------|----------|----------------|-------|
| Example: `/src/api` | API endpoints | ⚠️ Partial | Needs auth edge-case tests |
| Example: `/src/models` | Domain logic | ✅ Good | Update when models change |
| Example: `/src/utils` | Shared helpers | ❌ Missing | No tests yet |

Coverage Levels:
- ✅ **Good** — Core flows fully tested  
- ⚠️ **Partial** — Some tests exist but gaps remain  
- ❌ **Missing** — No meaningful coverage  

Claude must keep this table up-to-date.

---

# 3. File-Level Test Mapping

Claude should maintain a mapping between source files and their corresponding test files.

Example format:

| Source File | Test File | Coverage Notes |
|-------------|-----------|----------------|
| `/src/api/userApi.js` | `/tests/api/userApi.test.js` | Missing error-path tests |
| `/src/utils/formatDate.js` | `/tests/utils/formatDate.test.js` | Fully covered |
| `/src/components/NavBar.jsx` | `/tests/components/NavBar.test.jsx` | Snapshot exists, behavior tests missing |

Claude must automatically update this table whenever new files or tests are added or modified.

---

# 4. Critical Path Coverage

Claude must ensure the following *critical user and system flows* are always covered by tests:

### Authentication
- Login success/failure  
- Session persistence  
- Role-based access (if applicable)  

### Data Integrity
- CRUD flows  
- Validation  
- Error propagation  

### Business Logic
- Non-trivial computations  
- Decision-making branches  
- Side effects  

### UI/UX (if applicable)
- Render behavior  
- Interactive flows  
- Edge-state rendering  

Claude should expand or refine this section as the project evolves.

---

# 5. Test Gaps & Recommendations

Claude must maintain a list of known or newly discovered testing gaps.

Example format:

| Area | Gap Description | Recommended Test | Priority |
|------|-----------------|------------------|----------|
| API: User creation | No test for duplicate emails | Add 409 conflict test | High |
| Utils: Date formatter | No timezone tests | Add tz-based tests | Medium |

Claude should update this list proactively whenever code changes introduce new potential test requirements.

---

# 6. Recently Added Tests

Claude must maintain a short rolling list of recently added or updated test cases.

Format:

- **YYYY-MM-DD** — `tests/api/userApi.test.js`  
  - Added tests for rate-limit handling  
- **YYYY-MM-DD** — `tests/utils/math.test.js`  
  - Expanded coverage for edge inputs  

This section helps track recent progress.

---

# 7. Testing Conventions

Claude must follow (and keep current) the project’s testing rules:

- Test file naming conventions  
- Folder layout  
- Mocking guidelines  
- Patterns for async tests  
- Setup/teardown rules  
- Required test coverage targets  

If any of these evolve, Claude must update this section.

---

# 8. Actions Claude Should Take

Whenever Claude modifies code, it MUST:

1. Identify affected logic paths
2. Determine whether new tests are needed
3. Add or update test files
4. Update this TEST_COVERAGE_MAP.md
5. Include test changes in the same patch set

If Claude is unsure whether a test is required, Claude must ask the user.

---

# End of TEST_COVERAGE_MAP.md