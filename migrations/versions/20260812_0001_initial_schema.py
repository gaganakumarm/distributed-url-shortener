"""Initial URL shortener schema."""

from alembic import op
import sqlalchemy as sa


revision = "20260812_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Adopt databases created by the project's original create_all startup
    # path without deleting their existing data.
    if sa.inspect(op.get_bind()).has_table("users"):
        return
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_table(
        "short_urls",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("short_code", sa.String(32), nullable=False),
        sa.Column("original_url", sa.Text(), nullable=False),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_short_urls_short_code", "short_urls", ["short_code"], unique=True)
    op.create_index("ix_short_urls_owner_id", "short_urls", ["owner_id"])
    op.create_table(
        "click_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("url_id", sa.Integer(), sa.ForeignKey("short_urls.id", ondelete="CASCADE"), nullable=False),
        sa.Column("referrer", sa.String(512), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("clicked_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_click_events_url_id", "click_events", ["url_id"])


def downgrade() -> None:
    op.drop_index("ix_click_events_url_id", table_name="click_events")
    op.drop_table("click_events")
    op.drop_index("ix_short_urls_owner_id", table_name="short_urls")
    op.drop_index("ix_short_urls_short_code", table_name="short_urls")
    op.drop_table("short_urls")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
