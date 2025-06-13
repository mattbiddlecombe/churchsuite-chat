# GLOBAL RULES

These rules define the behaviour, structure, and standards expected in this project. They apply to all assistant tasks unless explicitly overridden.

---

## 🧠 Assistant Behaviour

- Always respond professionally and clearly.
- Use UK English spelling and grammar.
- When uncertain, ask clarifying questions — never assume.
- Output should be consistent, concise, and complete.
- Format all outputs in markdown unless otherwise specified.

---

## 🔑 Golden Practices

- Use markdown files to manage project knowledge (`README.md`, `PLANNING.md`, `TASK.md`, etc.).
- Keep source files under 500 lines. Split into modules when needed.
- One task per message is ideal — avoid overloading instructions.
- Start fresh conversations often, especially after long threads.
- Test early, test often. Each new function should have at least one unit test.
- Be specific in your prompts and responses — examples are helpful.
- Write documentation and comments as you go.
- Never embed or use real API keys or secrets. Reference environment variables only.
- Always update `README.md`, `TASK.md`, and `PLANNING.md` when project structure, tasks, or implementation details change.

---

## 🔁 Project Awareness & Context

- Always read `PLANNING.md` at the start of a new session to understand goals, architecture, and constraints.
- Always check `TASK.md` before beginning a new task.
  - If a task isn’t listed, add it with a description and today’s date.
- Use consistent naming, folder structures, and conventions as described in `PLANNING.md` and streamed context.
- Honour context streamed from `vault`, `README.md`, or `mcp_context.md`.

---

## 🏗 Code Structure & Modularity

- Organise logic into small, purpose-specific modules.
- Never create a single file over 500 lines — split responsibilities.
- Use relative imports when working within packages.
- Ensure each module or component is loosely coupled and testable.

---

## 🧪 Testing & Validation

- Write `pytest`-based unit tests (or equivalent) for all new functions, classes, and features.
- Include:
  - One expected-use test
  - One edge-case test
  - One failure-condition test
- Place all tests in a `tests/` directory that mirrors the main structure.
- Mock external services like databases or APIs.
- Confirm existing tests still pass after changes.
- Aim for meaningful test coverage. If coverage decreases, document the rationale in `DECISIONS.md`.

---

### 🔁 Enhanced Testing Feedback & Progress Monitoring

- When a test fails, the assistant must:

  - Explain **why** it failed, referencing expected vs actual results.
  - Suggest specific fixes or debug steps.
  - Indicate whether the failure represents progress (e.g. resolving earlier errors, changing behaviour).

- During iterative testing:

  - Track whether repeated test failures are identical or evolving.
  - Flag if the same failure occurs more than twice without change — this suggests the process may be stuck.
  - If progress stalls, pause and summarise:
    - What has been tried
    - What has changed
    - What is still failing
    - Suggested next steps or alternatives

- After each round of changes:
  - Reassess whether the overall objective is closer, unchanged, or regressing.
  - If in doubt, recommend a checkpoint discussion or review in `DECISIONS.md`.

---

## ✅ Task Completion Protocol

- Mark completed tasks in `TASK.md` immediately.
- Log new TODOs or sub-tasks discovered during implementation.
- Update `DECISIONS.md` for any meaningful change in approach or tooling.
- When a feature is implemented, check for impact on `README.md`, environment setup, or deployment flow.

---

## ⏭ Task Progression Discipline

- Each task must be fully completed and tested before moving on to the next.
- "Completed" means:

  - Code is implemented in the appropriate file/module
  - A corresponding unit test exists and passes
  - Any affected existing tests still pass
  - The task is marked complete in `TASK.md`

- Exceptions:

  - Exploratory tasks or prototypes may proceed without tests, but must be clearly flagged as such.
  - If a task is blocked by an external dependency, note this in `TASK.md` and revisit when unblocked.

- Any skipped or deferred testing must be documented in `DECISIONS.md` with justification and a follow-up plan.

---

## 🧩 Prompting Rules

- Keep prompts modular: one clear task per request.
- Provide examples whenever possible to improve output quality.
- If working on multiple files, instruct changes in one file at a time.
- Restart the conversation if output becomes inconsistent.

---

## 📎 Style & Language Conventions

- Use type hints and follow PEP8 (for Python projects).
- Format code with `black` or project-standard formatter.
- Use docstrings for every function (Google-style preferred):

```python
def example(param1: int) -> str:
    """
    Brief description.

    Args:
        param1 (int): Example parameter.

    Returns:
        str: Example result.
    """
```

- Always comment non-obvious code.
- When writing complex logic, add an inline `# Reason:` comment to explain why, not just how.

---

## 🔧 Code Quality Standards

- All generated code must be properly indented and syntactically valid before being written to a file.
- Validate Python code with a linter such as `black`, `flake8`, or an equivalent before completing each task.
- If the assistant generates or modifies code, it must:
  - Review indentation and structural integrity.
  - Highlight any potential issues before saving.
  - Prompt the user to run linting if automated validation isn't available.

---

## 📚 Documentation Rules

- Update `README.md` after any change that affects:
  - Features
  - Setup instructions
  - Configuration
  - Deployment steps
- Document each major component or function with:
  - Purpose
  - Inputs/outputs
  - Dependencies (e.g. env vars, third-party tools)
- The `.env.example` file must stay in sync with all required environment variables in the actual `.env`.

---

## 🔒 Prohibited Actions

- Do not hallucinate libraries, tools, or APIs.
- Do not guess schema or external formats — ask if unsure.
- Do not overwrite existing files or functions unless the task specifically calls for it.
- Do not hard-code secrets or API keys — always use placeholder env vars.
- Do not add undocumented or untested environment variables — all must be explained and synced with `.env.example`.

---

## 🐳 Deployment & Packaging

- If containerising, use Docker and follow standard structure:
  - Use a slim base image
  - Install only necessary dependencies
  - Expose `CMD` clearly
- Use `.env` files for all environment configuration, but don’t commit them to version control.

---

## 🔗 MCP Integration (If Applicable)

- Use `context7` for architectural and planning context.
- Use `vault` to reference project-specific formats, decisions, or naming conventions.
- Reference external documentation using `@docs:<name>` or by prompting MCP servers where supported.
- All MCP usage must be reflected in `PLANNING.md` or `README.md`.
- When using streamed context (e.g. via `context7`), assume access to `README.md`, `PLANNING.md`, `GLOBAL_RULES.md`, `TASK.md`, and `vault`.
- The assistant must not invent decisions or file context not present in these sources.

---

## 📦 Final Thoughts

- Projects should be accessible to other developers — aim for clarity and self-documentation.
- Every assistant response should move the project forward while respecting all rules and structure.
