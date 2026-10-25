"""Initial canonical schema.

Revision ID: 0001_initial
Revises: None
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ingestion_requests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("idempotency_key", sa.String(64), nullable=False),
        sa.Column("automation_id", sa.String(255)),
        sa.Column("automation_name", sa.String(255)),
        sa.Column("automation_period", sa.String(100)),
        sa.Column("automation_aggregation", sa.String(100)),
        sa.Column("session_id", sa.String(255)),
        sa.Column("stream", sa.String(50), nullable=False),
        sa.Column("received_at", sa.String(40), nullable=False),
        sa.Column("processing_started_at", sa.String(40)),
        sa.Column("processed_at", sa.String(40)),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("payload_size", sa.Integer, nullable=False),
        sa.Column("raw_path", sa.Text, nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("error", sa.Text),
        sa.Column("records_received", sa.Integer, nullable=False, server_default="0"),
        sa.Column("records_inserted", sa.Integer, nullable=False, server_default="0"),
        sa.Column("records_updated", sa.Integer, nullable=False, server_default="0"),
        sa.Column("records_ignored", sa.Integer, nullable=False, server_default="0"),
    )
    for name, cols, unique in [
        ("ix_ingestion_requests_idempotency_key", ["idempotency_key"], True),
        ("ix_ingestion_requests_stream", ["stream"], False),
        ("ix_ingestion_requests_received_at", ["received_at"], False),
        ("ix_ingestion_requests_payload_hash", ["payload_hash"], False),
        ("ix_ingestion_requests_status", ["status"], False),
    ]:
        op.create_index(name, "ingestion_requests", cols, unique=unique)

    op.create_table(
        "health_samples",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("sample_hash", sa.String(64), nullable=False),
        sa.Column("metric_name", sa.String(100), nullable=False),
        sa.Column("timestamp_utc", sa.String(40), nullable=False),
        sa.Column("end_timestamp_utc", sa.String(40)),
        sa.Column("local_date", sa.String(10), nullable=False),
        sa.Column("value", sa.Float),
        sa.Column("text_value", sa.Text),
        sa.Column("unit", sa.String(50)),
        sa.Column("source", sa.String(255)),
        sa.Column("metadata_json", sa.Text, nullable=False, server_default="{}"),
        sa.Column("ingestion_id", sa.String(36), sa.ForeignKey("ingestion_requests.id"), nullable=False),
    )
    op.create_index("ix_health_samples_sample_hash", "health_samples", ["sample_hash"], unique=True)
    op.create_index("ix_health_samples_metric_name", "health_samples", ["metric_name"])
    op.create_index("ix_health_samples_timestamp_utc", "health_samples", ["timestamp_utc"])
    op.create_index("ix_health_samples_local_date", "health_samples", ["local_date"])
    op.create_index("ix_health_samples_ingestion_id", "health_samples", ["ingestion_id"])
    op.create_index("ix_health_metric_date", "health_samples", ["metric_name", "local_date"])

    op.create_table(
        "workouts",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("external_id", sa.String(255), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("start_utc", sa.String(40), nullable=False),
        sa.Column("end_utc", sa.String(40), nullable=False),
        sa.Column("local_date", sa.String(10), nullable=False),
        sa.Column("duration_seconds", sa.Float, nullable=False),
        sa.Column("location", sa.String(100)),
        sa.Column("is_indoor", sa.Integer),
        sa.Column("active_energy_kcal", sa.Float),
        sa.Column("total_energy_kcal", sa.Float),
        sa.Column("distance_km", sa.Float),
        sa.Column("avg_hr", sa.Float),
        sa.Column("max_hr", sa.Float),
        sa.Column("metadata_json", sa.Text, nullable=False, server_default="{}"),
        sa.Column("ingestion_id", sa.String(36), sa.ForeignKey("ingestion_requests.id"), nullable=False),
    )
    for name, cols, unique in [
        ("ix_workouts_external_id", ["external_id"], True), ("ix_workouts_name", ["name"], False),
        ("ix_workouts_start_utc", ["start_utc"], False), ("ix_workouts_local_date", ["local_date"], False),
        ("ix_workouts_ingestion_id", ["ingestion_id"], False),
    ]:
        op.create_index(name, "workouts", cols, unique=unique)

    op.create_table(
        "workout_samples",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("sample_hash", sa.String(64), nullable=False),
        sa.Column("workout_id", sa.Integer, sa.ForeignKey("workouts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("metric_name", sa.String(100), nullable=False),
        sa.Column("timestamp_utc", sa.String(40), nullable=False),
        sa.Column("value", sa.Float),
        sa.Column("min_value", sa.Float),
        sa.Column("avg_value", sa.Float),
        sa.Column("max_value", sa.Float),
        sa.Column("unit", sa.String(50)),
        sa.Column("source", sa.String(255)),
        sa.Column("metadata_json", sa.Text, nullable=False, server_default="{}"),
    )
    for name, cols, unique in [
        ("ix_workout_samples_sample_hash", ["sample_hash"], True), ("ix_workout_samples_workout_id", ["workout_id"], False),
        ("ix_workout_samples_metric_name", ["metric_name"], False), ("ix_workout_samples_timestamp_utc", ["timestamp_utc"], False),
    ]:
        op.create_index(name, "workout_samples", cols, unique=unique)

    op.create_table(
        "derived_metrics",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("metric_name", sa.String(100), nullable=False),
        sa.Column("algorithm_version", sa.String(100), nullable=False),
        sa.Column("local_date", sa.String(10), nullable=False),
        sa.Column("scope_type", sa.String(30), nullable=False, server_default="day"),
        sa.Column("scope_id", sa.String(255), nullable=False, server_default=""),
        sa.Column("value", sa.Float),
        sa.Column("unit", sa.String(50)),
        sa.Column("components_json", sa.Text, nullable=False, server_default="{}"),
        sa.Column("inputs_hash", sa.String(64), nullable=False, server_default=""),
        sa.Column("computed_at", sa.String(40), nullable=False),
        sa.UniqueConstraint("metric_name", "algorithm_version", "local_date", "scope_type", "scope_id", name="uq_derived_metric_version_scope"),
    )
    op.create_index("ix_derived_metrics_metric_name", "derived_metrics", ["metric_name"])
    op.create_index("ix_derived_metrics_algorithm_version", "derived_metrics", ["algorithm_version"])
    op.create_index("ix_derived_metrics_local_date", "derived_metrics", ["local_date"])
    op.create_index("ix_derived_name_date", "derived_metrics", ["metric_name", "local_date"])

    op.create_table(
        "user_profile",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("hr_max", sa.Float),
        sa.Column("hr_rest", sa.Float),
        sa.Column("trimp_exponential_coefficient", sa.Float, nullable=False, server_default="1.92"),
        sa.Column("target_sleep_hours", sa.Float, nullable=False, server_default="8.0"),
        sa.Column("locale", sa.String(20), nullable=False, server_default="pt-BR"),
        sa.Column("updated_at", sa.String(40), nullable=False),
    )


def downgrade() -> None:
    # Downgrade is intentionally destructive and should never be run against production without a verified backup.
    for table in ["user_profile", "derived_metrics", "workout_samples", "workouts", "health_samples", "ingestion_requests"]:
        op.drop_table(table)
