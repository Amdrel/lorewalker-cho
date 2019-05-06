"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""

# pylint: disable=no-member

import sqlalchemy as sa
${imports if imports else ""}

from alembic import op


# Revision identifiers, used by Alembic.
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade():
    """Upgrades the database a single revision."""

    ${upgrades if upgrades else "pass"}


def downgrade():
    """Downgrades the database a single revision."""

    ${downgrades if downgrades else "pass"}
