# Design Doc: CI Quality Reporting System

**Date**: 2026-03-05
**Status**: Approved
**Topic**: Pytest Command Options, Artifact Capture, and Quality Scoring

## 1. Overview
This system automates the collection of test artifacts and the computation of a "Quality Score" during the CI full cycle. It provides a human-readable Markdown report in `test_reports/` to facilitate quick failure analysis and quality tracking.

## 2. Architecture & Data Flow

### 2.1. Data Collection (Pytest)
Pytest is configured to emit machine-readable artifacts:
- **Test Results**: `pytest-json-report` generates `report.json` containing test statuses, durations, and failure details.
- **Code Coverage**: `pytest-cov` generates `coverage.json` with line-level coverage metrics.

### 2.2. Processing (Reporting Script)
A Python script (`scripts/generate_quality_report.py`) parses these artifacts to:
1. Verify **Hard Gates**.
2. Compute the **Soft Quality Score**.
3. Generate the **Markdown Summary**.

## 3. Metrics & Scoring Framework

### 3.1. Hard Gates (Blocking)
- **Pass Rate**: Must be 100% (Exit code 0).
- **Coverage Floor**: Total coverage must be $\ge 80\%$.

### 3.2. Soft Quality Score (0-100)
The score is a weighted average of three components:
- **Pass Rate (50%)**: Percentage of passing tests.
- **Coverage (30%)**: Total line coverage percentage.
- **Performance (20%)**: Based on average test duration.
  - $PerfScore = \max(0, 100 - (\text{AvgDuration} \times 10))$

## 4. Artifacts
- `test_reports/report.json`: Full test execution metadata.
- `test_reports/coverage.json`: Detailed coverage data.
- `test_reports/quality_report.md`: The primary CI summary.

## 5. Implementation Plan
1. Add `pytest-json-report` and `pytest-cov` to development dependencies.
2. Create `scripts/generate_quality_report.py` for artifact parsing and scoring.
3. Update `.github/workflows/ci.yml` to run pytest with reporting flags and execute the reporting script.
4. Configure CI to archive the `test_reports/` directory.
