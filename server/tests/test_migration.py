from pytest_alembic.tests import (
    test_model_definitions_match_ddl,  # models vs. migrations: no drift
    test_single_head_revision,  # ← replaces your grep check
    test_up_down_consistency,  # every downgrade actually works
    test_upgrade,  # base → head applies cleanly
)
