Claude Code Project Guidelines

These rules define how Claude must operate when assisting with this project.
Claude should load and follow these guidelines for all future tasks in this workspace.

⸻

🧠 1. General Behavior Expectations
	•	Claude must preserve the existing architecture, coding style, and design conventions unless explicitly asked to change them.
	•	Claude must be clear, structured, and deliberate in its reasoning and proposals.
	•	Claude must never apply changes silently. Every modification must come with an explanation and a preview patch.
	•	Claude should ask clarifying questions before proceeding when instructions are ambiguous.
	•	Claude should avoid unnecessary rewrites or overly broad refactors. Favor minimal, precise changes.

⸻

📂 2. Workspace Awareness

Claude must:
	•	Understand the full workspace hierarchy and file purposes.
	•	Maintain a mental model of:
	•	Key modules
	•	Data flows
	•	API boundaries
	•	State management
	•	Shared utilities
	•	Respect .claudeignore rules and avoid scanning ignored directories.
	•	Update its understanding whenever files are added, removed, or renamed.

⸻

🛠️ 3. Editing and Patch Rules

When modifying the codebase, Claude must:
	1.	Provide a plan before making edits.
	2.	Explain:
	•	What will be changed
	•	Why it is needed
	•	What files will be affected
	3.	Apply patches in small, reviewable chunks.
	4.	Maintain consistency with:
	•	Naming conventions
	•	File organization
	•	Architectural principles
	5.	Avoid duplicating logic or creating unnecessary abstractions.
	6.	Never introduce breaking changes unless the user explicitly requests them.
	7.	Avoid “clever” solutions when a simple one exists.

⸻

📄 4. Documentation Maintenance Rules

Claude must ensure that project documentation stays synchronized with code changes.

Every time Claude adds, modifies, or removes code, it must:
	1.	Identify documentation impact.
	2.	Update these files when relevant:
	•	ARCHITECTURE.md
	•	CODE_MAP.md
	•	CLAUDE_GUIDELINES.md (if conventions are changed)
	•	Anything inside /docs
	3.	Maintain:
	•	Diagrams
	•	Data flow descriptions
	•	API signatures
	•	Type definitions
	•	Module descriptions
	4.	Propose documentation updates in the same patch as code changes.
	5.	Ask for confirmation only when the update is ambiguous.

⸻

🧱 5. Architecture Rules

Claude must follow these principles:
	•	Maintain separation of concerns.
	•	Keep functions and components small, focused, and testable.
	•	Adhere to the project’s chosen patterns (e.g., MVC, component-driven, service-layer, etc.).
	•	Preserve dependency boundaries unless refactoring is explicitly requested.
	•	Avoid introducing new major dependencies without approval.
	•	Keep imports organized and avoid circular dependencies.

⸻

🧪 6. Testing Rules

When adding or refactoring code, Claude must:
	•	Create or update tests for all significant logic.
	•	Follow existing testing frameworks and patterns.
	•	Ensure tests remain deterministic and isolated.
	•	When running tests, analyze failures and propose fixes.

⸻

🧹 7. Cleanup & Refactoring Rules

Claude should improve the codebase over time by:
	•	Removing dead code.
	•	Consolidating duplicated logic.
	•	Improving naming when clarity is needed.
	•	Strengthening type safety (where applicable).
	•	Suggesting—but not applying—bigger refactors unless approved.

⸻

⚠️ 8. Safety & Risk Management

Claude must:
	•	Never delete critical files without explicit permission.
	•	Never modify configuration, deployment, or CI/CD files unless instructed.
	•	Avoid touching secrets, credentials, or environment variables.
	•	Ask the user before performing:
	•	Large-scale refactors
	•	Architectural changes
	•	Mass file generation
	•	Command execution beyond simple tasks

⸻

🗺️ 9. File & Directory Conventions

Claude should use and maintain the following conventions:
	•	Follow the naming patterns already present in the repo.
	•	Place new files in logical, consistent directories.
	•	Keep feature-related code grouped together.
	•	Maintain CODE_MAP.md to reflect additions or relocations.

⸻

🔄 10. Change Summary Requirement

After any task, Claude must provide a summary containing:
	1.	What was changed
	2.	Why the change was made
	3.	How it affects the architecture
	4.	What documentation was updated
	5.	Any follow-up recommendations

⸻

🧭 11. Interaction & Workflow

Claude must follow this workflow for every substantial task:
	1.	Restate the user’s request
	2.	Propose a plan
	3.	Wait for approval
	4.	Apply patches in logical steps
	5.	Update documentation
	6.	Summarize changes

If additional instructions are needed, Claude should ask precisely targeted questions.

⸻

🎯 12. Goals of These Guidelines

These rules exist to:
	•	Ensure predictable, safe, and high-quality agent behavior
	•	Maintain clarity and organization across the project
	•	Keep code and documentation in sync
	•	Support incremental, maintainable changes
	•	Preserve architectural integrity
	•	Make collaboration seamless between human and AI

⸻

✔ End of Guidelines

Claude should load and obey these rules continuously while working in this project.