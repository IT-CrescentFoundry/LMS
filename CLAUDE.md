# Crescent Foundry LMS – Project Instructions

## 1. Project Overview

Build a comprehensive Learning Management System
for Crescent Foundry employees.

The objective is to support:
- Organisational learning
- Role-based learning
- Competency development
- Career progression
- AI-assisted learning
- Continuous employee development

## 2. Technology Stack

Frontend:
- React
- TypeScript
- Vite
- Tailwind CSS v4

Backend:
- Python
- FastAPI
- SQLAlchemy 2
- Alembic
- Pydantic

Database:
- MySQL 8

## 3. Architecture

Use a modular monolith architecture.

Keep frontend and backend independently organised
within this repository.

Do not introduce microservices without a justified
architectural requirement.

## 4. Organisation Management

Organisation structure must be fully configurable.

Never hardcode a fixed organisational hierarchy
or a fixed number of organisational levels.

Support:
- Manual organisation management
- Configurable organisational unit types
- Parent-child relationships
- Multiple locations and plants
- Departments and subdepartments
- Job families and positions
- Employee assignments
- Reporting relationships
- Effective dates and historical records

Support structured Excel imports with:
- Column mapping
- Multiple worksheets
- Validation
- Preview and dry runs
- Duplicate detection
- Error reports
- Transactional imports
- Import history and audit records

Keep organisational units, positions,
employees and reporting relationships separate.

## 5. Security

- Never expose secrets in source code.
- Never commit .env files.
- Follow secure authentication practices.
- Apply role-based and scope-based permissions.
- Maintain audit trails for sensitive operations.
- Never use actual employee data in test fixtures.

## 6. Database Engineering

- Use SQLAlchemy models.
- Use Alembic for all schema migrations.
- Never silently modify production databases.
- Never delete existing data without explicit approval.
- Maintain appropriate database constraints and indexes.

## 7. Multilingual Support

Support:
- English
- Bengali
- Hindi
- Gujarati

Prepare the frontend for internationalisation
from the initial architecture.

## 8. AI Architecture

Claude is the initial AI provider.

Keep AI functionality behind provider-independent
interfaces.

Never hardcode AI credentials.

AI-generated technical learning material must
require appropriate human review before publication.

## 9. Development Discipline

- Inspect existing code before modifying it.
- Work in explicitly defined stages.
- Do not implement unrelated features.
- Write tests for important functionality.
- Run tests, linting and type checks.
- Use database migrations for schema changes.
- Update documentation when architecture changes.
- Do not claim a test passed unless it was run.

## 10. Reporting

After each development task, report:

1. What was implemented.
2. Files created or modified.
3. Dependencies installed.
4. Database changes.
5. Tests executed and actual results.
6. Outstanding issues.
7. Recommended next step.