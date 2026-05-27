#!/usr/bin/env python3
"""
RAG Log Analyzer - ML Defender Day 14
Analyzes JSON Lines logs from RAGLogger

Authors: Alonso Isidoro Roman + Claude (Anthropic)
Date: December 2025
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict
from typing import Dict, List, Any
import argparse


class RAGLogAnalyzer:
    """Analyze RAG logs for statistics and insights"""

    def __init__(self, log_path: Path):
        self.log_path = log_path
        self.events = []
        self.load_events()

    def load_events(self):
        """Load all events from JSON Lines file"""
        print(f"📂 Loading events from: {self.log_path}")

        if not self.log_path.exists():
            print(f"❌ File not found: {self.log_path}")
            sys.exit(1)

        with open(self.log_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    event = json.loads(line)
                    self.events.append(event)
                except json.JSONDecodeError as e:
                    print(f"⚠️  Line {line_num}: JSON decode error: {e}")

        print(f"✅ Loaded {len(self.events)} events\n")

    def analyze_scores(self):
        """Analyze score distributions"""
        print("=" * 80)
        print("📊 SCORE DISTRIBUTION ANALYSIS")
        print("=" * 80)

        fast_scores = []
        ml_scores = []
        final_scores = []
        divergences = []

        for event in self.events:
            scores = event.get('detection', {}).get('scores', {})
            fast_scores.append(scores.get('fast_detector', 0))
            ml_scores.append(scores.get('ml_detector', 0))
            final_scores.append(scores.get('final_score', 0))
            divergences.append(scores.get('divergence', 0))

        def print_stats(name, values):
            if not values:
                return
            print(f"\n{name}:")
            print(f"  Min:     {min(values):.4f}")
            print(f"  Max:     {max(values):.4f}")
            print(f"  Avg:     {sum(values)/len(values):.4f}")
            print(f"  Median:  {sorted(values)[len(values)//2]:.4f}")

        print_stats("Fast Detector Scores", fast_scores)
        print_stats("ML Detector Scores", ml_scores)
        print_stats("Final Scores", final_scores)
        print_stats("Divergence Values", divergences)

        # Histogram
        print("\n📈 Score Histogram (Final Scores):")
        bins = [0, 0.3, 0.5, 0.7, 0.85, 1.0]
        counts = [0] * (len(bins) - 1)

        for score in final_scores:
            for i in range(len(bins) - 1):
                if bins[i] <= score < bins[i+1]:
                    counts[i] += 1
                    break
            else:
                if score >= bins[-1]:
                    counts[-1] += 1

        for i in range(len(bins) - 1):
            pct = (counts[i] / len(final_scores) * 100) if final_scores else 0
            bar = "█" * int(pct / 2)
            print(f"  [{bins[i]:.2f}-{bins[i+1]:.2f}): {counts[i]:4d} ({pct:5.1f}%) {bar}")

    def analyze_sources(self):
        """Analyze authoritative sources"""
        print("\n" + "=" * 80)
        print("🎯 AUTHORITATIVE SOURCE DISTRIBUTION")
        print("=" * 80 + "\n")

        sources = []
        for event in self.events:
            source = event.get('detection', {}).get('classification', {}).get('authoritative_source', 'UNKNOWN')
            sources.append(source)

        counter = Counter(sources)
        total = len(sources)

        print(f"{'Source':<35} {'Count':>8} {'Percentage':>12}")
        print("-" * 60)

        for source, count in counter.most_common():
            pct = (count / total * 100) if total else 0
            print(f"{source:<35} {count:>8} {pct:>11.1f}%")

    def analyze_attack_families(self):
        """Analyze attack family distribution"""
        print("\n" + "=" * 80)
        print("🦠 ATTACK FAMILY DISTRIBUTION")
        print("=" * 80 + "\n")

        families = []
        for event in self.events:
            family = event.get('detection', {}).get('classification', {}).get('attack_family', 'UNKNOWN')
            families.append(family)

        counter = Counter(families)
        total = len(families)

        for family, count in counter.most_common():
            pct = (count / total * 100) if total else 0
            print(f"{family:<30} {count:>8} ({pct:5.1f}%)")

    def analyze_divergence(self):
        """Analyze divergence patterns"""
        print("\n" + "=" * 80)
        print("⚡ DIVERGENCE ANALYSIS")
        print("=" * 80 + "\n")

        high_divergence = []
        medium_divergence = []
        low_divergence = []

        for event in self.events:
            div = event.get('detection', {}).get('scores', {}).get('divergence', 0)
            if div > 0.40:
                high_divergence.append(event)
            elif div > 0.30:
                medium_divergence.append(event)
            else:
                low_divergence.append(event)

        total = len(self.events)
        print(f"High divergence (>0.40):    {len(high_divergence):5d} ({len(high_divergence)/total*100:5.1f}%)")
        print(f"Medium divergence (0.30-0.40): {len(medium_divergence):5d} ({len(medium_divergence)/total*100:5.1f}%)")
        print(f"Low divergence (<0.30):     {len(low_divergence):5d} ({len(low_divergence)/total*100:5.1f}%)")

        # Divergence reasons
        if high_divergence:
            print("\n🔍 High Divergence Events (sample):")
            for event in high_divergence[:5]:
                scores = event.get('detection', {}).get('scores', {})
                reasons = event.get('detection', {}).get('reasons', {})
                print(f"  Event: {event.get('detection', {}).get('event_id', 'N/A')}")
                print(f"    Fast: {scores.get('fast_detector', 0):.4f}, ML: {scores.get('ml_detector', 0):.4f}")
                print(f"    Reason: {reasons.get('fast_detector_reason', 'N/A')}")
                print(f"    Priority: {reasons.get('investigation_priority', 'N/A')}")

    def analyze_network(self):
        """Analyze network patterns"""
        print("\n" + "=" * 80)
        print("🌐 NETWORK ANALYSIS")
        print("=" * 80 + "\n")

        src_ips = Counter()
        dst_ips = Counter()
        protocols = Counter()
        dst_ports = Counter()

        for event in self.events:
            network = event.get('network', {}).get('five_tuple', {})
            src_ips[network.get('src_ip', 'unknown')] += 1
            dst_ips[network.get('dst_ip', 'unknown')] += 1
            protocols[network.get('protocol', 'unknown')] += 1
            dst_ports[network.get('dst_port', 0)] += 1

        print("Top 10 Source IPs:")
        for ip, count in src_ips.most_common(10):
            print(f"  {ip:<20} {count:>8}")

        print("\nTop 10 Destination IPs:")
        for ip, count in dst_ips.most_common(10):
            print(f"  {ip:<20} {count:>8}")

        print("\nProtocol Distribution:")
        for proto, count in protocols.most_common():
            print(f"  {proto:<10} {count:>8}")

        print("\nTop 10 Destination Ports:")
        for port, count in dst_ports.most_common(10):
            print(f"  {port:<10} {count:>8}")

    def analyze_temporal(self):
        """Analyze temporal patterns"""
        print("\n" + "=" * 80)
        print("⏰ TEMPORAL ANALYSIS")
        print("=" * 80 + "\n")

        timestamps = []
        for event in self.events:
            ts_str = event.get('rag_metadata', {}).get('logged_at', '')
            if ts_str:
                try:
                    ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                    timestamps.append(ts)
                except ValueError:
                    pass

        if not timestamps:
            print("No valid timestamps found")
            return

        timestamps.sort()
        first = timestamps[0]
        last = timestamps[-1]
        duration = (last - first).total_seconds()

        print(f"First event: {first}")
        print(f"Last event:  {last}")
        print(f"Duration:    {duration:.1f} seconds ({duration/60:.1f} minutes)")
        print(f"Event rate:  {len(timestamps)/duration:.2f} events/second")

    def generate_summary(self):
        """Generate executive summary"""
        print("\n" + "=" * 80)
        print("📋 EXECUTIVE SUMMARY")
        print("=" * 80 + "\n")

        total = len(self.events)

        # Count by classification
        malicious = sum(1 for e in self.events
                        if e.get('detection', {}).get('classification', {}).get('final_classification') == 'MALICIOUS')
        benign = total - malicious

        # Count by source
        divergent = sum(1 for e in self.events
                        if e.get('detection', {}).get('classification', {}).get('authoritative_source') == 'DETECTOR_SOURCE_DIVERGENCE')
        consensus = sum(1 for e in self.events
                        if e.get('detection', {}).get('classification', {}).get('authoritative_source') == 'DETECTOR_SOURCE_CONSENSUS')

        # RAG analysis required
        rag_required = sum(1 for e in self.events
                           if e.get('detection', {}).get('reasons', {}).get('requires_rag_analysis', False))

        print(f"Total events logged:        {total}")
        print(f"  Malicious:                {malicious} ({malicious/total*100:.1f}%)")
        print(f"  Benign:                   {benign} ({benign/total*100:.1f}%)")
        print(f"\nDetector Agreement:")
        print(f"  Divergent:                {divergent} ({divergent/total*100:.1f}%)")
        print(f"  Consensus:                {consensus} ({consensus/total*100:.1f}%)")
        print(f"\nRAG Analysis:")
        print(f"  Requires investigation:   {rag_required} ({rag_required/total*100:.1f}%)")

        # Artifacts
        artifacts_saved = sum(1 for e in self.events
                              if 'protobuf_artifact' in e)
        print(f"\nArtifacts:")
        print(f"  Protobuf artifacts saved: {artifacts_saved}")

    def run_full_analysis(self):
        """Run complete analysis"""
        if not self.events:
            print("❌ No events to analyze")
            return

        self.generate_summary()
        self.analyze_scores()
        self.analyze_sources()
        self.analyze_attack_families()
        self.analyze_divergence()
        self.analyze_network()
        self.analyze_temporal()

        print("\n" + "=" * 80)
        print("✅ Analysis complete")
        print("=" * 80)


def main():
    parser = argparse.ArgumentParser(
        description='Analyze RAG logs from ML Defender',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s /vagrant/logs/rag/events/2025-12-10.jsonl
  %(prog)s /vagrant/logs/rag/events/$(date +%%Y-%%m-%%d).jsonl
        """
    )
    parser.add_argument('log_file', type=Path,
                        help='Path to RAG JSON Lines log file')

    args = parser.parse_args()

    analyzer = RAGLogAnalyzer(args.log_file)
    analyzer.run_full_analysis()


if __name__ == '__main__':
    main()