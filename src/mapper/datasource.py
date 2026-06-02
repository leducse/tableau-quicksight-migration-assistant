"""Map Tableau connections to QuickSight data sources and datasets."""

from __future__ import annotations

from typing import Any

from ..common import slugify

# Tableau connection class -> QuickSight data source type.
_SUPPORTED_SOURCES: dict[str, str] = {
    "redshift": "REDSHIFT",
    "athena": "ATHENA",
    "postgres": "POSTGRESQL",
    "mysql": "MYSQL",
    "sqlserver": "SQLSERVER",
    "snowflake": "SNOWFLAKE",
    "aurora-postgres": "AURORA_POSTGRESQL",
}

# Tableau datatype -> QuickSight column type.
_TYPE_MAP: dict[str, str] = {
    "string": "STRING",
    "integer": "INTEGER",
    "real": "DECIMAL",
    "date": "DATETIME",
    "datetime": "DATETIME",
    "boolean": "STRING",
}


def _qs_column_type(tableau_type: str) -> str:
    return _TYPE_MAP.get(tableau_type, "STRING")


def map_datasources(metadata: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return (datasources_doc, datasets_doc) ready to emit as YAML."""
    workbook_id = metadata["workbook_id"]
    datasource_entries: list[dict[str, Any]] = []
    dataset_entries: list[dict[str, Any]] = []

    for ds in metadata.get("datasources", []):
        conn = ds.get("connection", {})
        conn_class = conn.get("class", "").lower()
        qs_type = _SUPPORTED_SOURCES.get(conn_class)
        supported = qs_type is not None
        name_slug = slugify(ds["name"])

        datasource_entries.append(
            {
                "tableau_id": ds["id"],
                "tableau_name": ds["name"],
                "quicksight_data_source_id": f"migration-{workbook_id}-{name_slug}-source",
                "quicksight_type": qs_type or "UNSUPPORTED",
                "supported": supported,
                "connection": {
                    "host": conn.get("server"),
                    "port": conn.get("port"),
                    "database": conn.get("database"),
                    "schema": conn.get("schema"),
                },
                "status": "READY" if supported else "MANUAL_REQUIRED",
                "notes": []
                if supported
                else [f"Connection class '{conn_class}' is not an auto-mappable QuickSight source."],
            }
        )

        for table in ds.get("tables", []):
            columns = [
                {
                    "name": fld["name"],
                    "tableau_type": fld.get("datatype", "string"),
                    "quicksight_type": _qs_column_type(fld.get("datatype", "string")),
                }
                for fld in table.get("fields", [])
            ]
            dataset_entries.append(
                {
                    "quicksight_dataset_id": f"migration-{workbook_id}-{slugify(table['name'])}-dataset",
                    "tableau_datasource": ds["id"],
                    "physical_table": table["name"],
                    "import_mode": "DIRECT_QUERY",
                    "columns": columns,
                }
            )

    datasources_doc = {"workbook_id": workbook_id, "datasources": datasource_entries}
    datasets_doc = {"workbook_id": workbook_id, "datasets": dataset_entries}
    return datasources_doc, datasets_doc
