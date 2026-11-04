from alembic import context
from sqlalchemy import create_engine

from app import core, models

target_metadata = models.Base.metadata


def run():
    url = context.config.get_main_option("sqlalchemy.url") or core.DB_URL
    engine = create_engine(url)
    with engine.connect() as conn:
        context.configure(connection=conn, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


run()
