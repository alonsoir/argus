#!/usr/bin/env python3
"""
RAG Log CSV Exporter - ML Defender Day 14
Export JSON Lines RAG logs to CSV format for Excel/spreadsheet analysis

Authors: Alonso Isidoro Roman + Claude (Anthropic)
Date: December 2025
"""

import json
import csv
import sys
from pathlib import Path
from datetime import datetime
import argparse


def flatten_event(event: dict) -> dict:
    """Flatten nested JSON structure for CSV export"""
    flat = {}

    # RAG Metadata
    meta = event.get('rag_metadata', {})
    flat['logged_at'] = meta.get('logged_at', '')
    flat['deployment_id'] = meta.get('deployment_id', '')
    flat['node_id'] = meta.get('node_id', '')

    # Detection
    detection = event.get('detection', {})
    flat['event_id'] = detection.get('event_id', '')
    flat['detection_timestamp'] = detection.get('detection_timestamp', '')

    # Scores
    scores = detection.get('scores', {})
    flat['fast_detector_score'] = scores.get('fast_detector', 0)
    flat['ml_detector_score'] = scores.get('ml_detector', 0)
    flat['final_score'] = scores.get('final_score', 0)
    flat['divergence'] = scores.get('divergence', 0)

    # Classification
    classification = detection.get('classification', {})
    flat['authoritative_source'] = classification.get('authoritative_source', '')
    flat['attack_family'] = classification.get('attack_family', '')
    flat['level_1_label'] = classification.get('level_1_label', '')
    flat['final_classification'] = classification.get('final_classification', '')
    flat['confidence'] = classification.get('confidence', 0)

    # Reasons
    reasons = detection.get('reasons', {})
    flat['fast_detector_triggered'] = reasons.get('fast_detector_triggered', False)
    flat['fast_detector_reason'] = reasons.get('fast_detector_reason', '')
    flat['requires_rag_analysis'] = reasons.get('requires_rag_analysis', False)
    flat['investigation_priority'] = reasons.get('investigation_priority', '')

    # Network
    network = event.get('network', {})
    five_tuple = network.get('five_tuple', {})
    flat['src_ip'] = five_tuple.get('src_ip', '')
    flat['src_port'] = five_tuple.get('src_port', 0)
    flat['dst_ip'] = five_tuple.get('dst_ip', '')
    flat['dst_port'] = five_tuple.get('dst_port', 0)
    flat['protocol'] = five_tuple.get('protocol', '')
    flat['interface'] = network.get('interface', '')

    # Features (select key features)
    features = event.get('features', {}).get('raw_features', {})
    flat['external_ips_30s'] = features.get('external_ips_30s', 0)
    flat['smb_diversity'] = features.get('smb_diversity', 0)
    flat['dns_requests_30s'] = features.get('dns_requests_30s', 0)
    flat['total_bytes'] = features.get('total_bytes', 0)
    flat['packet_count'] = features.get('packet_count', 0)

    # System State
    system = event.get('system_state', {})
    flat['events_processed_total'] = system.get('events_processed_total', 0)
    flat['memory_usage_mb'] = system.get('memory_usage_mb', 0)
    flat['cpu_usage_percent'] = system.get('cpu_usage_percent', 0)
    flat['uptime_seconds'] = system.get('uptime_seconds', 0)

    return flat


def export_to_csv(input_path: Path, output_path: Path):
    """Export RAG JSON Lines log to CSV"""

    print(f"📂 Reading: {input_path}")

    if not input_path.exists():
        print(f"❌ File not found: {input_path}")
        sys.exit(1)

    # Read all events
    events = []
    with open(input_path, 'r') as f:
        for line_num, line in enumerate(f, 1):
            try:
                event = json.loads(line)
                events.append(event)
            except json.JSONDecodeError as e:
                print(f"⚠️  Line {line_num}: JSON decode error: {e}")

    if not events:
        print("❌ No events found in log file")
        sys.exit(1)

    print(f"✅ Loaded {len(events)} events")

    # Flatten events
    print("🔄 Flattening events...")
    flat_events = [flatten_event(e) for e in events]

    # Get all keys (column names)
    all_keys = set()
    for event in flat_events:
        all_keys.update(event.keys())

    fieldnames = sorted(all_keys)

    # Write CSV
    print(f"💾 Writing: {output_path}")
    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(flat_events)

    print(f"✅ Exported {len(flat_events)} events to CSV")
    print(f"📊 Columns: {len(fieldnames)}")
    print(f"📄 File size: {output_path.stat().st_size / 1024:.1f} KB")


def main():
    parser = argparse.ArgumentParser(
        description='Export RAG JSON Lines logs to CSV format',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s input.jsonl output.csv
  %(prog)s /vagrant/logs/rag/events/2025-12-10.jsonl /vagrant/logs/rag/stats/2025-12-10.csv
        """
    )
    parser.add_argument('input_file', type=Path,
                        help='Path to RAG JSON Lines log file')
    parser.add_argument('output_file', type=Path,
                        help='Path to output CSV file')

    args = parser.parse_args()

    export_to_csv(args.input_file, args.output_file)


if __name__ == '__main__':
    main()