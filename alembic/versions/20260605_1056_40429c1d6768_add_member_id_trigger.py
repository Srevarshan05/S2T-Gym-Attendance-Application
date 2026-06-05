"""add_member_id_trigger

Revision ID: 40429c1d6768
Revises: b6db4804d164
Create Date: 2026-06-05 10:56:47.360124+00:00
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '40429c1d6768'
down_revision: Union[str, None] = 'b6db4804d164'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create sequence starting at 101
    op.execute("CREATE SEQUENCE member_id_seq START WITH 101;")
    
    # Create function to set member_id
    op.execute("""
    CREATE OR REPLACE FUNCTION set_member_id()
    RETURNS TRIGGER AS $$
    BEGIN
        IF NEW.role = 'member' AND NEW.member_id IS NULL THEN
            NEW.member_id := 'S2T' || nextval('member_id_seq');
        END IF;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)
    
    # Create trigger on users table
    op.execute("""
    CREATE TRIGGER trigger_set_member_id
    BEFORE INSERT ON users
    FOR EACH ROW
    EXECUTE FUNCTION set_member_id();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trigger_set_member_id ON users;")
    op.execute("DROP FUNCTION IF EXISTS set_member_id();")
    op.execute("DROP SEQUENCE IF EXISTS member_id_seq;")
