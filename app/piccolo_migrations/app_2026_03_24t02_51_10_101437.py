from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.base import OnDelete
from piccolo.columns.base import OnUpdate
from piccolo.columns.column_types import ForeignKey
from piccolo.columns.indexes import IndexMethod


ID = "2026-03-24T02:51:10:101437"
VERSION = "1.30.0"
DESCRIPTION = ""


async def forwards():
    manager = MigrationManager(migration_id=ID, app_name="app", description=DESCRIPTION)

    manager.add_column(
        table_class_name="Lottery",
        tablename="lottery",
        column_name="winner",
        db_column_name="winner",
        column_class_name="ForeignKey",
        column_class=ForeignKey,
        params={
            "references": "User",
            "on_delete": OnDelete.cascade,
            "on_update": OnUpdate.cascade,
            "target_column": None,
            "null": True,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    return manager
