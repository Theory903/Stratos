"""Initial schema — companies, countries, world_state, market_ticks.

Revision ID: 001_initial
Revises: None
Create Date: 2024-02-13
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Companies
    op.create_table(
        "companies",
        sa.Column("ticker", sa.String(20), nullable=False),
        sa.Column(
            "stored_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("earnings_quality", sa.Float, nullable=False),
        sa.Column("leverage_ratio", sa.Float, nullable=False),
        sa.Column("free_cash_flow_stability", sa.Float, nullable=False),
        sa.Column("fraud_score", sa.Float, nullable=False),
        sa.Column("moat_score", sa.Float, nullable=False),
        sa.PrimaryKeyConstraint("ticker", "stored_at"),
    )

    # Countries
    op.create_table(
        "countries",
        sa.Column("country_code", sa.String(3), nullable=False),
        sa.Column(
            "stored_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("debt_gdp", sa.Float, nullable=False),
        sa.Column("fx_reserves", sa.Float, nullable=False),
        sa.Column("fiscal_deficit", sa.Float, nullable=False),
        sa.Column("political_stability", sa.Float, nullable=False),
        sa.Column("currency_volatility", sa.Float, nullable=False),
        sa.PrimaryKeyConstraint("country_code", "stored_at"),
    )

    # World State
    op.create_table(
        "world_state",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("interest_rate", sa.Float, nullable=False),
        sa.Column("inflation", sa.Float, nullable=False),
        sa.Column("liquidity_index", sa.Float, nullable=False),
        sa.Column("geopolitical_risk", sa.Float, nullable=False),
        sa.Column("volatility_index", sa.Float, nullable=False),
        sa.Column("commodity_index", sa.Float, nullable=False),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "stored_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_world_state_stored_at", "world_state", ["stored_at"])

    # Market Ticks
    op.create_table(
        "market_ticks",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("ticker", sa.String(20), nullable=False),
        sa.Column("asset_class", sa.String(20), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "stored_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("open", sa.Numeric(18, 6), nullable=False),
        sa.Column("high", sa.Numeric(18, 6), nullable=False),
        sa.Column("low", sa.Numeric(18, 6), nullable=False),
        sa.Column("close", sa.Numeric(18, 6), nullable=False),
        sa.Column("volume", sa.BigInteger, nullable=False),
    )
    op.create_index("ix_market_ticks_ticker", "market_ticks", ["ticker"])
    op.create_index(
        "ix_market_ticks_ticker_valid_stored",
        "market_ticks",
        ["ticker", "timestamp", "stored_at"],
    )


def downgrade() -> None:
    op.drop_table("market_ticks")
    op.drop_table("world_state")
    op.drop_table("countries")
    op.drop_table("companies")
