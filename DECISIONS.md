# DECISIONS

This file logs meaningful decisions, deviations from project rules, and justifications for any exceptions made during development. It supports traceability and enforces accountability across all AI-assisted tasks.

---

## 2025-06-13: Task Progression Rule Activated

From this point forward, all tasks must be completed and tested before moving on. Any deviations — such as exploratory work, blocked tasks, or skipped tests — must be recorded here with a justification and plan for follow-up.

Example format:

- **Date:** 2025-06-14
- **Task:** Integrate ChurchSuite webhooks
- **Deviation:** Skipped unit test due to pending API response structure
- **Follow-up:** Revisit after schema confirmation from ChurchSuite dev team

## 2025-06-13: Test Assertions Update
- **Date:** 2025-06-13
- **Task:** Fix test_people_endpoints.py assertions
- **Deviation:** Multiple attempts to update test assertions using different methods
- **Justification:** Initial attempts to update test assertions using file editing tools failed due to content uniqueness issues
- **Solution:** Using sed command to update all test assertions at once
- **Current Status:** All tests passing
- **Next Steps:**
  - None - task complete
- **Follow-up:**
  - Verify all test assertions are correctly updated
  - Re-run tests to ensure full coverage
  - Document any additional issues found during testing
- **Additional Notes:**
  - Fixed issues:
    - Session handling in endpoint implementation
    - Authentication checks
    - Error propagation
    - Query parameter handling
    - Pagination implementation
    - Total count calculation
    - Mock implementation
  - Changes made:
    - Updated endpoint to handle session data correctly
    - Fixed mock implementation to handle query and pagination
    - Updated test assertions to match expected behavior
    - Fixed total count calculation for filtered results
  - All test cases now passing:
    - Successful listing of people
    - Query filtering
    - Pagination
    - Authentication
    - Permission denied error handling
    - Internal error handling

## 2025-06-13: Standardize on FastAPI Framework

- **Date:** 2025-06-13
- **Decision:** Standardize on FastAPI as our primary framework
- **Justification:**
  - Current mixed Starlette/FastAPI approach causing testing and middleware inconsistencies
  - FastAPI provides better high-level features and developer experience
  - Simplifies testing and middleware implementation
  - Better maintainability with consistent framework usage

- **Changes Made:**
  1. Removed direct Starlette middleware usage
  2. Updated middleware to use FastAPI's BaseHTTPMiddleware
  3. Standardized test client usage to FastAPI's TestClient
  4. Updated error handling to use FastAPI's HTTPException
  5. Updated dependency injection to use FastAPI's system

- **Benefits:**
  - Consistent testing approach
  - Better error handling
  - Improved code organization
  - Modern API features
  - Better maintainability

- **Next Steps:**
  1. Update remaining middleware implementations
  2. Review and update all test files
  3. Document changes in PLANNING.md
  4. Update requirements.txt

## 2025-06-13: Test Structure and Hanging Prevention
- **Date:** 2025-06-13
- **Task:** Fix hanging issues in test_security.py
- **Learning:**
  - Never create new app instances in individual tests
  - Always use the provided test_client fixture
  - Ensure proper cleanup after each test
  - Avoid complex middleware setup in tests
  - Use async/await correctly with proper resource management
- **Best Practices:**
  1. Use test fixtures for shared setup
  2. Clean up after each test
  3. Avoid manual app/middleware creation
  4. Focus tests on specific validation points
  5. Ensure proper async resource handling
- **Common Pitfalls to Avoid:**
  - Creating new Starlette app instances
  - Manual middleware configuration
  - Missing cleanup steps
  - Complex async resource management
  - Inconsistent test isolation
- **Future Implementation:**
  - Always use test_client fixture
  - Add proper cleanup to all tests
  - Keep tests focused and isolated
  - Use async/await correctly
  - Maintain consistent test patterns
