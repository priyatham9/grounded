#!/usr/bin/env python3
"""
Check numeric claims in OSHA_PAPER.md against outputs in summary.json and CSV files.

Extracts numeric values from the paper (excluding references), checks whether each 
appears in the data outputs, and generates an audit report.
"""

import re
import json
import csv
import sys
from pathlib import Path
from typing import Tuple, List, Dict, Optional, Any


def get_paper_path() -> Path:
    """Get path to OSHA_PAPER.md."""
    return Path(__file__).parent.parent / "paper" / "OSHA_PAPER.md"


def get_outputs_dir() -> Path:
    """Get path to outputs directory."""
    return Path(__file__).parent.parent / "repos" / "ehs-osha-analysis" / "outputs"


def read_paper() -> str:
    """Read the OSHA paper markdown, excluding references section."""
    paper_path = get_paper_path()
    with open(paper_path, "r", encoding="utf-8") as f:
        text = f.read()

    # Find and exclude References section
    # References section starts with "## References"
    match = re.search(r'^## References\s*$', text, re.MULTILINE)
    if match:
        text = text[:match.start()]

    return text


def extract_numbers(text: str) -> List[Tuple[str, int, str, bool]]:
    """
    Extract numeric values from text.

    Returns list of (value_str, position, context, is_percentage) tuples.

    Extracts:
    - Integers with thousands separators: 2,801,064
    - Decimals: 0.134, 3.983
    - Percentages: 2.07%, 96.7%
    - Multipliers: 249x, 1.39x
    - Large numbers like 214,977

    Excludes:
    - Years 2016-2026
    - CFR section numbers (29 CFR 1904, etc.)
    - DOI patterns (10.1002, 10.1016, etc.)
    - arXiv references (2005.11401, etc.)
    - Citation years (1970, 1979, 1998, etc.)
    - Figure/table numbers (Figure 1, Table 2, etc.)
    """

    numbers = []
    processed_positions = set()

    # Find all numbers with their context (including trailing % or x)
    # This regex finds a number and checks what follows it
    pattern = r'(\d{1,3}(?:,\d{3})*(?:\.\d+)?)([%x]?)'

    for match in re.finditer(pattern, text):
        value_str = match.group(1)
        suffix = match.group(2)
        pos = match.start(1)

        # Skip if we've already processed this position
        if pos in processed_positions:
            continue

        # Determine if this is a percentage or multiplier
        is_percentage = suffix == '%'
        is_multiplier = suffix == 'x'

        # Get local context for filtering
        context_start = max(0, pos - 40)
        context_end = min(len(text), pos + 60)
        local_context = text[context_start:context_end]

        # Skip years 2016-2026 (4-digit numbers without decimals)
        if not is_percentage and not is_multiplier and len(value_str.replace(',', '')) == 4:
            try:
                year_val = int(value_str.replace(',', ''))
                if 2016 <= year_val <= 2026:
                    continue
            except ValueError:
                pass

        # Skip citation years and publication years
        if len(value_str.replace(',', '')) == 4:
            # Skip if surrounded by citation-like context
            if re.search(r'[\(\[].*' + re.escape(value_str) + r'.*[\)\]]', local_context):
                continue
            # Skip if preceded by "et al" or similar
            if re.search(r'\w+\s+et\s+al.*' + re.escape(value_str), local_context):
                continue

        # Skip CFR section references (29 CFR 1904, etc.)
        if re.search(r'\bCFR\b|\b\d+\s+CFR\b', local_context):
            continue

        # Skip DOI patterns (10.1002, 10.1016, etc.)
        if value_str.startswith('10.') or re.search(r'10\.\d{4}', local_context):
            continue

        # Skip arXiv patterns (2005.11401, 2303.08896, etc.)
        if re.match(r'^20[01]\d\.\d+$', value_str):
            continue

        # Skip "Figure X" or "Table X" numbers
        if re.search(r'(?:Figure|Table|Fig\.|Tbl\.)\s*' + re.escape(value_str), local_context):
            continue

        # Skip reference markers like [1], [smith2020], etc.
        if re.search(r'\[\s*' + re.escape(value_str) + r'\s*\]', local_context):
            continue

        # Skip single/double/small digit numbers (too many false positives)
        if len(value_str.replace(',', '')) <= 2 and '.' not in value_str:
            continue

        # Get 60 chars of context
        ctx_start = max(0, pos - 30)
        ctx_end = min(len(text), pos + 30)
        context = text[ctx_start:ctx_end].strip()

        # Format value_str with suffix if present
        formatted_value = value_str + suffix

        numbers.append((formatted_value, pos, context, is_percentage))
        processed_positions.add(pos)

    # Deduplicate while preserving first occurrence
    seen = set()
    unique_numbers = []
    for num in sorted(numbers, key=lambda x: x[0]):
        if num[0] not in seen:
            seen.add(num[0])
            unique_numbers.append(num)

    return unique_numbers


def normalize_number(num_str: str) -> Optional[float]:
    """
    Normalize a number string to float.

    Handles:
    - Thousands separators: 2,801,064 -> 2801064
    - Percentages: 96.7% -> 96.7
    - Multipliers: 249x -> 249
    """

    num_str = num_str.strip()

    # Remove trailing x or %
    if num_str.endswith('x'):
        num_str = num_str[:-1].strip()
    elif num_str.endswith('%'):
        num_str = num_str[:-1].strip()

    # Remove thousands separators
    num_str = num_str.replace(',', '')

    try:
        return float(num_str)
    except ValueError:
        return None


def get_decimals(num_str: str) -> int:
    """Get number of decimal places in a number string."""
    # Remove formatting
    num_str = num_str.strip().rstrip('x%')
    num_str = num_str.replace(',', '')

    if '.' in num_str:
        return len(num_str.split('.')[1])
    return 0


def walk_json_values(obj: Any) -> List[float]:
    """Walk through all numeric values in a JSON object."""
    values = []

    if isinstance(obj, dict):
        for v in obj.values():
            values.extend(walk_json_values(v))
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, (int, float)):
                values.append(float(item))
            elif isinstance(item, (dict, list)):
                values.extend(walk_json_values(item))
    elif isinstance(obj, (int, float)):
        values.append(float(obj))

    return values


def round_to_decimals(value: float, decimals: int) -> float:
    """Round a value to specified number of decimals."""
    if decimals < 0:
        return value

    multiplier = 10 ** decimals
    return round(value * multiplier) / multiplier


def check_in_json(value: float, decimals: int, is_pct: bool) -> Optional[str]:
    """Check if value exists in summary.json."""
    outputs_dir = get_outputs_dir()
    json_path = outputs_dir / "summary.json"

    if not json_path.exists():
        return None

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    json_values = walk_json_values(data)

    for json_val in json_values:
        # Allow for rounding tolerance
        rounded_target = round_to_decimals(value, decimals)
        rounded_json = round_to_decimals(json_val, decimals)

        if abs(rounded_target - rounded_json) < 1e-9:
            return "summary.json"

        # If the original value is a percentage, also check against decimal form
        if is_pct:
            decimal_value = value / 100.0
            rounded_decimal = round_to_decimals(decimal_value, decimals + 2)
            if abs(rounded_decimal - json_val) < 1e-3:
                return "summary.json"

    return None


def check_in_csvs(value: float, decimals: int, is_pct: bool) -> Optional[str]:
    """Check if value exists in any CSV file."""
    outputs_dir = get_outputs_dir()
    tables_dir = outputs_dir / "tables"

    if not tables_dir.exists():
        return None

    for csv_file in sorted(tables_dir.glob("*.csv")):
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    for cell in row:
                        try:
                            cell_value = float(cell)
                            rounded_target = round_to_decimals(value, decimals)
                            rounded_cell = round_to_decimals(cell_value, decimals)

                            if abs(rounded_target - rounded_cell) < 1e-9:
                                return f"tables/{csv_file.name}"

                            # If the original value is a percentage, also check decimal form
                            if is_pct:
                                decimal_value = value / 100.0
                                rounded_decimal = round_to_decimals(decimal_value, decimals + 2)
                                if abs(rounded_decimal - cell_value) < 1e-3:
                                    return f"tables/{csv_file.name}"
                        except ValueError:
                            continue
        except Exception as e:
            print(f"Error reading {csv_file}: {e}", file=sys.stderr)
            continue

    return None


def find_value(value_str: str, is_pct: bool) -> Optional[str]:
    """Find where a numeric value appears in the outputs."""
    value = normalize_number(value_str)
    if value is None:
        return None

    decimals = get_decimals(value_str)

    # Check JSON first
    result = check_in_json(value, decimals, is_pct)
    if result:
        return result

    # Check CSVs
    result = check_in_csvs(value, decimals, is_pct)
    if result:
        return result

    return None


def generate_audit_report(numbers: List[Tuple[str, int, str, bool]]) -> Tuple[List[Dict], Dict]:
    """
    Generate audit report for all numbers.

    Returns (audit_rows, summary_counts).
    """

    audit_rows = []
    found_count = 0
    not_found_count = 0

    for value_str, pos, context, is_pct in numbers:
        location = find_value(value_str, is_pct)

        if location:
            status = f"found in {location}"
            found_count += 1
        else:
            status = "NOT FOUND"
            not_found_count += 1

        audit_rows.append({
            'value': value_str,
            'context': context,
            'status': status,
            'position': pos,
        })

    summary_counts = {
        'total': len(numbers),
        'found': found_count,
        'not_found': not_found_count,
    }

    return audit_rows, summary_counts


def write_audit_markdown(audit_rows: List[Dict], summary_counts: Dict) -> None:
    """Write audit report to NUMBER_AUDIT.md."""
    output_path = get_paper_path().parent / "NUMBER_AUDIT.md"

    with open(output_path, 'w', encoding='utf-8') as f:
        # Write header
        f.write("# Number Audit Report\n\n")
        f.write("## Summary\n\n")
        f.write(f"- Total numeric values: {summary_counts['total']}\n")
        f.write(f"- Found in outputs: {summary_counts['found']}\n")
        f.write(f"- Not found: {summary_counts['not_found']}\n\n")

        # Write table
        f.write("## Detailed Results\n\n")
        f.write("| Value | Context | Status |\n")
        f.write("|-------|---------|--------|\n")

        for row in audit_rows:
            value = row['value'].replace('|', '\\|')
            context = row['context'].replace('|', '\\|').replace('\n', ' ')
            status = row['status']
            f.write(f"| {value} | {context} | {status} |\n")


def main():
    """Main entry point."""
    # Read paper
    paper_text = read_paper()

    # Extract numbers
    print("Extracting numbers from OSHA_PAPER.md...", file=sys.stderr)
    numbers = extract_numbers(paper_text)
    print(f"Found {len(numbers)} unique numeric values", file=sys.stderr)

    # Generate audit
    print("Checking values against outputs...", file=sys.stderr)
    audit_rows, summary_counts = generate_audit_report(numbers)

    # Write report
    print("Writing audit report...", file=sys.stderr)
    write_audit_markdown(audit_rows, summary_counts)

    # Print NOT FOUND rows
    print("\n" + "="*70, file=sys.stderr)
    print("NOT FOUND VALUES:", file=sys.stderr)
    print("="*70, file=sys.stderr)

    not_found_rows = [r for r in audit_rows if "NOT FOUND" in r['status']]

    for row in not_found_rows:
        print(f"\nValue: {row['value']}")
        print(f"Context: {row['context']}")

    print(f"\nTotal NOT FOUND: {len(not_found_rows)}", file=sys.stderr)

    # Summary
    print(f"\n" + "="*70, file=sys.stderr)
    print(f"Total: {summary_counts['total']}", file=sys.stderr)
    print(f"Found: {summary_counts['found']}", file=sys.stderr)
    print(f"Not found: {summary_counts['not_found']}", file=sys.stderr)
    print(f"="*70, file=sys.stderr)


if __name__ == "__main__":
    main()
