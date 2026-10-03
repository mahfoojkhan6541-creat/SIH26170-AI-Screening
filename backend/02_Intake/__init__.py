"""
Stage 02: Dataset Intake & Registration
Handles multi-format ingestion (CSV, Excel, MAT, JSON, Text),
provenance calculation (SHA-256), and dataset registry metadata.
"""
from .adapters import (
    BaseSourceAdapter,
    CSVSourceAdapter,
    ExcelSourceAdapter,
    JSONSourceAdapter,
    TextSourceAdapter,
    IntakeAdapterFactory,
    get_adapter,
    compute_file_sha256,
)
from .nasa_adapter import NasaMatAdapter
from .registry import DatasetRegistry, DatasetMetadata

__all__ = [
    "BaseSourceAdapter",
    "CSVSourceAdapter",
    "ExcelSourceAdapter",
    "JSONSourceAdapter",
    "TextSourceAdapter",
    "IntakeAdapterFactory",
    "get_adapter",
    "compute_file_sha256",
    "NasaMatAdapter",
    "DatasetRegistry",
    "DatasetMetadata",
]
