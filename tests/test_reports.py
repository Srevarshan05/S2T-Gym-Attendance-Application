"""
tests/test_reports.py
──────────────────────
Unit tests for the Reporting & Exports module utilities and schemas.
"""

from datetime import date
import io
import pandas as pd
import pytest

from app.schemas.reports import ReportFilterRequest
from app.utils.export_helpers import generate_csv, generate_excel


def test_generate_csv_empty():
    """Verify that an empty input list yields a single empty byte string."""
    gen = generate_csv([])
    chunks = list(gen)
    assert chunks == [b""]


def test_generate_csv_with_data():
    """Verify that list of dicts converts to a valid memory-efficient CSV format."""
    data = [
        {"Name": "John Doe", "Age": 30, "Plan": "Monthly"},
        {"Name": "Jane Smith", "Age": 25, "Plan": "Annually"}
    ]
    gen = generate_csv(data)
    chunks = list(gen)
    
    # Reassemble CSV content
    csv_bytes = b"".join(chunks)
    csv_str = csv_bytes.decode("utf-8")
    
    # Normalize line endings
    lines = csv_str.strip().replace("\r\n", "\n").split("\n")
    assert len(lines) == 3
    assert lines[0] == "Name,Age,Plan"
    assert lines[1] == "John Doe,30,Monthly"
    assert lines[2] == "Jane Smith,25,Annually"


def test_generate_excel_empty():
    """Verify that empty data yields a valid, empty Excel file stream."""
    excel_stream = generate_excel([])
    assert isinstance(excel_stream, io.BytesIO)
    
    # Read back workbook using pandas
    df = pd.read_excel(excel_stream)
    assert df.empty


def test_generate_excel_with_data():
    """Verify that Excel generator returns valid xlsx format with data matches."""
    data = [
        {"Name": "John Doe", "Age": 30, "Plan": "Monthly"},
        {"Name": "Jane Smith", "Age": 25, "Plan": "Annually"}
    ]
    excel_stream = generate_excel(data)
    assert isinstance(excel_stream, io.BytesIO)
    
    # Read back and assert values
    df = pd.read_excel(excel_stream)
    assert len(df) == 2
    assert list(df.columns) == ["Name", "Age", "Plan"]
    assert df.iloc[0]["Name"] == "John Doe"
    assert int(df.iloc[1]["Age"]) == 25
    assert df.iloc[1]["Plan"] == "Annually"


def test_report_filter_request_validation():
    """Verify that ReportFilterRequest validates dates and filters correctly."""
    req = ReportFilterRequest(
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 5),
        member_id="S2T101",
        plan_name="Monthly"
    )
    assert req.start_date == date(2026, 6, 1)
    assert req.end_date == date(2026, 6, 5)
    assert req.member_id == "S2T101"
    assert req.plan_name == "Monthly"
