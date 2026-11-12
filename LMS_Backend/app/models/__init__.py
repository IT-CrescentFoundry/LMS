"""SQLAlchemy ORM models.

Every model module must be imported here so that ``Base.metadata`` is complete
when Alembic compares it with the database (autogenerate).

Stage A intentionally defines no business tables. The proposed schema is
documented in ``docs/database/LMS_DATABASE_DESIGN.md``.
"""

from app.db.base import Base

__all__ = ["Base"]
