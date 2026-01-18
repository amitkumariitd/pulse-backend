"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
# Revision ID is Unix timestamp (seconds) for chronological ordering
revision: str = ${repr(up_revision)}
down_revision: Union[str, Sequence[str], None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    """Upgrade schema.

    IMPORTANT: When modifying tables, update THREE things:
    1. Main table - Add/remove columns
    2. History table - Add/remove same columns
    3. Trigger function - Update INSERT statements to include/exclude columns

    See alembic/README for best practices and examples.
    """
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """Downgrade schema.

    IMPORTANT: Reverse all changes in opposite order.
    Test downgrade before committing!
    """
    ${downgrades if downgrades else "pass"}
