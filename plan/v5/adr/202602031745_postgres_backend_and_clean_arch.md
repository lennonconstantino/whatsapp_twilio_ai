# ADR 24: Postgres Backend Support and Clean Architecture Refactoring

## Status
Accepted

## Context
The project initially relied heavily on Supabase as the primary backend. To increase flexibility, reduce vendor lock-in, and support self-hosted deployments, a decision was made to introduce full PostgreSQL support as an alternative backend. This required refactoring the data access layer to decouple business logic from specific database implementations.

Additionally, as the codebase grew, direct instantiation of repositories created tight coupling and made testing difficult. A transition to Clean Architecture principles and Dependency Injection was necessary to improve maintainability and testability.

## Decision
1.  **Multi-Backend Support**: Implemented a dual-backend strategy supporting both `Supabase` (via REST/Client) and `Postgres` (via direct SQL/Psycopg2). The active backend is configured via the `DB_BACKEND` environment variable.
2.  **Clean Architecture for Repositories**:
    *   Defined Abstract Base Classes (ABCs) for repositories (e.g., `ConversationRepository`, `UserRepository`) in the root of their respective modules.
    *   Moved concrete implementations to subpackages: `impl/supabase` and `impl/postgres`.
3.  **Dependency Injection (DI)**:
    *   Adopted a centralized `Container` (based on `dependency_injector` or custom factory pattern) to manage object lifecycles.
    *   Services and Tools now receive repositories via injection rather than instantiating them directly.
    *   Legacy helper functions (e.g., `get_user_service`) were updated to use the DI container internally to maintain backward compatibility while leveraging the new architecture.
4.  **Hybrid Search with RRF**: Implemented Reciprocal Rank Fusion (RRF) for hybrid search (Vector + Full-Text) to improve retrieval quality in the memory system.
5.  **Refactoring**: Updated key modules (`finance`, `identity`) to use concrete repository classes or injected services, removing reliance on deprecated interfaces.

## Detailed Changes (Commit Log)
The following changes were introduced in the `version_5_0_0-Postgres-OnOff` branch:

- **68b7ee7** `feat: add PostgreSQL backend support with repository reorganization`
    - Initial groundwork for Postgres support and repository structure changes.
- **dfd3d50** `docs: add consolidated compliance analysis and action plan`
    - Documentation for compliance and architectural alignment.
- **e0f0c6d** `docs: add modular cohesion and coupling analysis reports`
    - Static analysis reports driving the refactoring decisions.
- **17144d8** `refactor(repositories): implement clean architecture with interfaces and multiple backends`
    - Core refactoring of the repository layer into ABCs and concrete implementations.
- **b0cdaf6** `feat(memory): implement hybrid search with RRF fusion and improve logging`
    - Enhancement of the memory retrieval system using advanced search techniques.
- **ecd8f35** `feat(database): add full postgres support with migrations, repositories, and scripts`
    - Comprehensive addition of Postgres-specific migrations and repository logic.
- **dfce027** `refactor(finance): replace interfaces with concrete repository classes`
    - Updates to the Finance module to align with the new repository patterns.
- **85381d3** `refactor: replace direct repository injection with dependency injection`
    - Global refactoring to enforce DI patterns across the application.

## Stability Fixes (Uncommitted/Recent)
In addition to the committed changes, the following stability improvements were applied to ensure test suite pass rate:
- **Test Compatibility**: Updated test fixtures to use concrete repository implementations (`SupabaseConversationRepository`) instead of abstract base classes.
- **Circular Imports**: Resolved circular dependencies in `update_preferences.py` using lazy imports.
- **Legacy Support**: Restored bridge files (`user_repository.py`, etc.) and helper functions to prevent breaking existing tools and scripts during the transition.

## Consequences
- **Positive**:
    - Application is now backend-agnostic (can run on pure Postgres or Supabase).
    - Testing is significantly easier due to dependency injection (repositories can be mocked easily).
    - Clearer separation of concerns between domain logic and data access.
- **Negative**:
    - Increased complexity in the repository layer (more files/classes).
    - Need to maintain two implementations for each repository (Supabase and Postgres) until full migration or unification is decided.
    - Requires careful management of imports to avoid circular dependencies between DI container and modules.

## Compliance
- **Security**: RLS policies were updated/added for the new Postgres tables.
- **Performance**: Hybrid search improves relevance but adds computational overhead; monitored via observability stack.
