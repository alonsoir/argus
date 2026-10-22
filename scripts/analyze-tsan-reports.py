#!/usr/bin/env python3
# scripts/analyze-tsan-reports.py

import sys
import os
import re
from pathlib import Path
from datetime import datetime

def parse_tsan_log(filepath):
    """Parse TSAN log and extract warnings/errors."""
    if not os.path.exists(filepath):
        return {"warnings": 0, "errors": 0, "issues": []}

    warnings = 0
    errors = 0
    issues = []

    current_issue = []
    in_issue = False

    with open(filepath, 'r', errors='ignore') as f:
        for line in f:
            if 'WARNING: ThreadSanitizer' in line:
                if current_issue:
                    issues.append('\n'.join(current_issue))
                current_issue = [line.strip()]
                in_issue = True

                if 'data race' in line:
                    warnings += 1
                elif 'deadlock' in line:
                    errors += 1
                else:
                    warnings += 1

            elif in_issue:
                if line.strip() == '' or line.startswith('===='):
                    if current_issue:
                        issues.append('\n'.join(current_issue))
                        current_issue = []
                    in_issue = False
                else:
                    current_issue.append(line.strip())

    if current_issue:
        issues.append('\n'.join(current_issue))

    return {"warnings": warnings, "errors": errors, "issues": issues}

def generate_summary(report_dir):
    """Generate markdown summary of all TSAN reports."""
    report_path = Path(report_dir)

    components = ['sniffer', 'ml-detector', 'etcd-server']
    results = {}

    for comp in components:
        test_log = report_path / f"{comp}-tsan-tests.log"
        integration_log = report_path / f"{comp}-integration.log"

        test_results = parse_tsan_log(test_log)
        integration_results = parse_tsan_log(integration_log)

        results[comp] = {
            'unit_tests': test_results,
            'integration': integration_results
        }

    # Generate markdown report
    summary_path = report_path / "TSAN_SUMMARY.md"

    with open(summary_path, 'w') as f:
        f.write(f"# TSAN Analysis Report - Day 48\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"## 📊 Summary\n\n")

        # Summary table
        f.write("| Component | Unit Tests | Integration | Status |\n")
        f.write("|-----------|------------|-------------|--------|\n")

        total_warnings = 0
        total_errors = 0

        for comp, data in results.items():
            unit_w = data['unit_tests']['warnings']
            unit_e = data['unit_tests']['errors']
            int_w = data['integration']['warnings']
            int_e = data['integration']['errors']

            total_warnings += unit_w + int_w
            total_errors += unit_e + int_e

            unit_status = "✅" if (unit_w + unit_e) == 0 else "⚠️" if unit_e == 0 else "❌"
            int_status = "✅" if (int_w + int_e) == 0 else "⚠️" if int_e == 0 else "❌"

            f.write(f"| {comp} | {unit_w}W/{unit_e}E {unit_status} | ")
            f.write(f"{int_w}W/{int_e}E {int_status} | ")

            if (unit_w + unit_e + int_w + int_e) == 0:
                f.write("✅ CLEAN |\n")
            elif (unit_e + int_e) == 0:
                f.write("⚠️ WARNINGS |\n")
            else:
                f.write("❌ ERRORS |\n")

        f.write(f"\n**Total:** {total_warnings} warnings, {total_errors} errors\n\n")

        # Detailed issues
        f.write("## 🔍 Detailed Issues\n\n")

        for comp, data in results.items():
            f.write(f"### {comp}\n\n")

            if data['unit_tests']['issues']:
                f.write(f"#### Unit Tests ({len(data['unit_tests']['issues'])} issues)\n\n")
                for i, issue in enumerate(data['unit_tests']['issues'], 1):
                    f.write(f"**Issue #{i}:**\n```\n{issue}\n```\n\n")

            if data['integration']['issues']:
                f.write(f"#### Integration ({len(data['integration']['issues'])} issues)\n\n")
                for i, issue in enumerate(data['integration']['issues'], 1):
                    f.write(f"**Issue #{i}:**\n```\n{issue}\n```\n\n")

            if not data['unit_tests']['issues'] and not data['integration']['issues']:
                f.write("✅ No issues detected\n\n")

        # Recommendations
        f.write("## 🎯 Recommendations\n\n")

        if total_errors > 0:
            f.write("❌ **CRITICAL:** Deadlocks or severe race conditions detected. Must fix before production.\n\n")
        elif total_warnings > 0:
            f.write("⚠️ **WARNING:** Data races detected. Review and fix during hardening phase.\n\n")
        else:
            f.write("✅ **EXCELLENT:** No concurrency issues detected. Pipeline is thread-safe.\n\n")

        f.write("## 📁 Log Files\n\n")
        for comp in components:
            f.write(f"- `{comp}-tsan-tests.log` - Unit test TSAN output\n")
            f.write(f"- `{comp}-integration.log` - Integration test output\n")
        f.write("\n")

    print(f"\n✅ Summary generated: {summary_path}")

    # Print to console
    with open(summary_path, 'r') as f:
        print(f.read())

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: analyze-tsan-reports.py <report_dir>")
        sys.exit(1)

    generate_summary(sys.argv[1])