"""Assemble the migration package (mappings + generated artifacts + manifest)."""

from .builder import MigrationPackage, build_package

__all__ = ["MigrationPackage", "build_package"]
