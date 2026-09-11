"""create app_user role and grants

Revision ID: b65d5f6dda81
Revises: 003_assignment_lock_flag
Create Date: 2026-09-09 23:19:44.013997

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'b65d5f6dda81'
down_revision: Union[str, None] = '003_assignment_lock_flag'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use DO block to prevent error if role already exists
    op.execute('''
    DO
    $do$
    BEGIN
       IF NOT EXISTS (
          SELECT FROM pg_catalog.pg_roles
          WHERE  rolname = 'app_user') THEN

          CREATE ROLE app_user WITH LOGIN PASSWORD 'app_password' NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
       END IF;
    END
    $do$;
    ''')
    # Grant permissions to app_user on public schema
    op.execute("GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO app_user;")
    op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO app_user;")
    op.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;")
    op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO app_user;")


def downgrade() -> None:
    # Downgrading roles is tricky because of dependent objects, but we can revoke
    op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL PRIVILEGES ON TABLES FROM app_user;")
    op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE USAGE, SELECT ON SEQUENCES FROM app_user;")
    op.execute("REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM app_user;")
    op.execute("REVOKE USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public FROM app_user;")
    op.execute("DROP ROLE IF EXISTS app_user;")
