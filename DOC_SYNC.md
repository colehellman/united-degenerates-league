# Documentation Sync Checklist

This file defines the rules Claude must follow to keep all project documentation
current, accurate, and synchronized with the codebase.

Claude must reference this checklist after **every task** that modifies,
adds, removes, or reorganizes code.

---

## 1. Required Documentation Updates

Whenever Claude performs work that affects the codebase, Claude MUST:

### 🔹 1.1 Update Core Documentation Files
Update the following files when applicable:

- `ARCHITECTURE.md`
- `CODE_MAP.md`
- `CLAUDE_GUIDELINES.md` (if conventions are changed)
- Files inside:
  - `/docs/`
  - `/docs/api/`
  - `/docs/features/`
  - `/docs/models/`

---

## 2. Situations That Always Require Documentation Updates

Claude must update documentation whenever ANY of the following occur:

### **2.1 New Feature or New Module**
- Add a section describing the feature/module.
- Update CODE_MAP.md with file purposes.
- Update ARCHITECTURE.md with flows and interactions.

### **2.2 API or Interface Changes**
- Change request/response schemas.
- Update any relevant diagrams.
- Update endpoint lists.

### **2.3 Model, Schema, or Type Updates**
- Reflect all changes to interfaces, classes, models, or domain objects.

### **2.4 File Creation, Movement, or Deletion**
- Document where new files live.
- Update CODE_MAP.md.
- Remove references to deleted components.

### **2.5 Refactoring**
- Describe architectural implications.
- Update module relationships.

### **2.6 Dependency Changes**
- Note new SDKs, libraries, or tools.
- Update ARCHITECTURE.md tooling section.

---

## 3. Patch Requirements

Documentation updates MUST:

### ✓ Be included in the same patch set as code updates  
### ✓ Be grouped logically (docs together, code together)  
### ✓ Be previewed before applying  
### ✓ Contain a clear explanation of what was updated and why  

---

## 4. Summary Requirements

After applying patches, Claude must provide:

- A documentation change summary  
- Mention of every file updated  
- A short explanation of alignment between code and docs  

---

## 5. Responsibilities

Claude is responsible for:

- Ensuring all documentation remains accurate  
- Keeping the project’s conceptual model consistent  
- Preventing outdated or misleading docs  
- Updating diagrams when necessary  
- Maintaining readability and clarity  

---

# End of DOC_SYNC.md
Claude must load this file during workspace indexing and apply it automatically after every coding task.