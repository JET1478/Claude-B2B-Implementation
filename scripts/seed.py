#!/usr/bin/env python3
"""Seed the database with a demo tenant and sample configs."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database import Base
from app.models.tenant import Tenant

SAMPLES_DIR = Path(__file__).parent.parent / "samples"


def seed():
    engine = create_engine(settings.database_url_sync)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Check if demo tenant already exists
    existing = session.query(Tenant).filter_by(slug="demo-company").first()
    if existing:
        print(f"Demo tenant already exists: {existing.id}")
        session.close()
        return

    # Load sample configs
    support_yaml = (SAMPLES_DIR / "support.yaml").read_text()
    sales_yaml = (SAMPLES_DIR / "sales.yaml").read_text()

    tenant = Tenant(
        name="Demo Company",
        slug="demo-company",
        allowed_domains="demo.com,example.com",
        is_active=True,
        max_runs_per_day=100,
        max_tokens_per_day=100000,
        max_items_per_minute=5,
        support_workflow_enabled=True,
        sales_workflow_enabled=True,
        autosend_enabled=False,
        confidence_threshold=0.85,
        support_config_yaml=support_yaml,
        sales_config_yaml=sales_yaml,
    )

    session.add(tenant)
    session.commit()
    print(f"Created demo tenant: {tenant.id} (slug: {tenant.slug})")
    session.close()


if __name__ == "__main__":
    seed()
