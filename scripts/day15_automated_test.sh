#!/bin/bash
# 🎯 ML DEFENDER - DAY 15 AUTOMATED TESTING
# RAGLogger Validation & Neris Dataset Analysis

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  $1${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# ============================================================================
# PHASE 1: SYSTEM VERIFICATION
# ============================================================================

phase1_verify_system() {
    print_header "PHASE 1: System Verification"

    echo ""
    print_info "Checking dependencies..."

    # Check dependencies
    vagrant ssh defender -c "dpkg -l | grep -E 'libssl-dev|nlohmann-json3-dev|jq'" > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        print_success "Dependencies installed"
    else
        print_warning "Some dependencies missing, installing..."
        vagrant ssh defender -c "sudo apt-get update && sudo apt-get install -y libssl-dev nlohmann-json3-dev jq"
    fi

    # Initialize RAG directories
    print_info "Initializing RAG directories..."
    make rag-init 2>/dev/null || {
        vagrant ssh defender -c "mkdir -p /vagrant/logs/rag/events"
        vagrant ssh defender -c "mkdir -p /vagrant/logs/rag/artifacts"
        vagrant ssh defender -c "chmod 755 /vagrant/logs/rag -R"
    }
    print_success "RAG directories initialized"

    # Check config
    print_info "Checking RAG config..."
    vagrant ssh defender -c "cat /vagrant/config/rag_logger_config.json" > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        print_success "RAG config found"
    else
        print_error "RAG config missing!"
        echo "Create config/rag_logger_config.json first"
        exit 1
    fi

    echo ""
    print_success "System verification complete"
    echo ""
}

# ============================================================================
# PHASE 2: SMALLFLOWS TEST
# ============================================================================

phase2_test_smallflows() {
    print_header "PHASE 2: SmallFlows Test (~1 minute)"

    echo ""
    print_info "Cleaning previous RAG logs..."
    make rag-clean 2>/dev/null || {
        vagrant ssh defender -c "rm -rf /vagrant/logs/rag/events/*"
        vagrant ssh defender -c "rm -rf /vagrant/logs/rag/artifacts/*"
    }

    print_info "Running smallFlows test..."
    echo "Expected: 1,207 total events → ~80-100 RAG events"
    echo ""

    make test-replay-small

    echo ""
    print_info "Analyzing results..."
    sleep 2

    # Count RAG events
    rag_count=$(vagrant ssh defender -c "cat /vagrant/logs/rag/events/*.jsonl 2>/dev/null | wc -l" | tr -d ' ')

    if [ "$rag_count" -gt 0 ]; then
        print_success "RAG events logged: $rag_count"

        # Show statistics
        print_info "Statistics:"
        vagrant ssh defender -c "cat /vagrant/logs/rag/events/*.jsonl | jq -s '{
            total: length,
            divergent: [.[] | select(.detection.scores.divergence > 0.30)] | length,
            high_score: [.[] | select(.detection.scores.final_score >= 0.80)] | length
        }'"

        # Show sample event
        echo ""
        print_info "Sample RAG event:"
        vagrant ssh defender -c "cat /vagrant/logs/rag/events/*.jsonl | head -1 | jq '{
            event_id: .rag_metadata.logged_at,
            scores: .detection.scores,
            source: .detection.classification.authoritative_source,
            src_ip: .network.five_tuple.src_ip,
            dst_ip: .network.five_tuple.dst_ip
        }'"
    else
        print_error "No RAG events logged!"
        print_warning "Check detector logs for errors"
    fi

    echo ""
    print_success "SmallFlows test complete"
    echo ""
}

# ============================================================================
# PHASE 3: NERIS TEST (OPTIONAL)
# ============================================================================

phase3_test_neris() {
    print_header "PHASE 3: Neris Botnet Test (~30-45 minutes)"

    echo ""
    print_warning "This will take 30-45 minutes to complete"
    read -p "Do you want to continue? (y/n) " -n 1 -r
    echo ""

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Skipping Neris test"
        return
    fi

    echo ""
    print_info "Cleaning previous RAG logs..."
    make rag-clean 2>/dev/null || {
        vagrant ssh defender -c "rm -rf /vagrant/logs/rag/events/*"
        vagrant ssh defender -c "rm -rf /vagrant/logs/rag/artifacts/*"
    }

    print_info "Starting Neris test..."
    echo "Total events: 492,358"
    echo "Expected RAG events: ~10,000-15,000"
    echo "Botnet IPs: 147.32.84.165, 147.32.84.191, 147.32.84.192"
    echo ""
    print_info "Monitor progress in another terminal with:"
    echo "  tail -f /vagrant/logs/rag/events/\$(date +%Y-%m-%d).jsonl | jq ."
    echo ""

    # Run test
    make test-replay-neris

    echo ""
    print_info "Analyzing Neris results..."
    sleep 2

    # Count RAG events
    rag_count=$(vagrant ssh defender -c "cat /vagrant/logs/rag/events/*.jsonl 2>/dev/null | wc -l" | tr -d ' ')
    print_success "Total RAG events: $rag_count"

    # Count botnet events
    print_info "Analyzing botnet IPs..."
    botnet_count=$(vagrant ssh defender -c "cat /vagrant/logs/rag/events/*.jsonl | \
        jq -r 'select(.network.five_tuple.src_ip == \"147.32.84.165\" or
                      .network.five_tuple.src_ip == \"147.32.84.191\" or
                      .network.five_tuple.src_ip == \"147.32.84.192\")' | wc -l" | tr -d ' ')

    print_success "Botnet IPs in RAG: $botnet_count"

    # Show botnet statistics
    echo ""
    print_info "Botnet IP statistics:"
    vagrant ssh defender -c "cat /vagrant/logs/rag/events/*.jsonl | \
        jq -s '[.[] | select(.network.five_tuple.src_ip |
               IN(\"147.32.84.165\", \"147.32.84.191\", \"147.32.84.192\"))] |
               {
                 count: length,
                 avg_fast_score: (map(.detection.scores.fast_detector) | add / length),
                 avg_ml_score: (map(.detection.scores.ml_detector) | add / length),
                 avg_final_score: (map(.detection.scores.final_score) | add / length),
                 avg_divergence: (map(.detection.scores.divergence) | add / length)
               }'"

    # Show file sizes
    echo ""
    print_info "Storage usage:"
    vagrant ssh defender -c "du -h /vagrant/logs/rag/events/"
    vagrant ssh defender -c "du -h /vagrant/logs/rag/artifacts/ 2>/dev/null || echo 'No artifacts'"

    echo ""
    print_success "Neris test complete"
    echo ""
}

# ============================================================================
# PHASE 4: SUMMARY & RECOMMENDATIONS
# ============================================================================

phase4_summary() {
    print_header "PHASE 4: Summary & Recommendations"

    echo ""
    print_info "Test Summary:"

    # Get final counts
    rag_count=$(vagrant ssh defender -c "cat /vagrant/logs/rag/events/*.jsonl 2>/dev/null | wc -l" | tr -d ' ')

    echo "  📊 Total RAG events: $rag_count"

    # Overall statistics
    vagrant ssh defender -c "cat /vagrant/logs/rag/events/*.jsonl 2>/dev/null | jq -s '{
        total_events: length,
        divergent: [.[] | select(.detection.scores.divergence > 0.30)] | length,
        high_score: [.[] | select(.detection.scores.final_score >= 0.80)] | length,
        sources: [.[] | .detection.classification.authoritative_source] | group_by(.) |
                 map({source: .[0], count: length})
    }' 2>/dev/null || echo '  No statistics available'"

    echo ""
    print_info "Next Steps:"
    echo "  1. Review RAG logs: make rag-analyze"
    echo "  2. Adjust thresholds if needed in config/rag_logger_config.json"
    echo "  3. Prepare for Day 16: RAG ingestion pipeline"
    echo ""

    print_success "All tests complete!"
    echo ""
}

# ============================================================================
# MAIN
# ============================================================================

main() {
    clear
    print_header "ML DEFENDER - DAY 15 AUTOMATED TESTING"
    echo ""

    # Check if we're in the right directory
    if [ ! -d "ml-detector" ]; then
        print_error "Must be run from argus directory"
        exit 1
    fi

    # Run phases
    phase1_verify_system

    read -p "Continue with SmallFlows test? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        phase2_test_smallflows
    fi

    phase3_test_neris
    phase4_summary

    print_success "DAY 15 TESTING COMPLETE! 🚀"
}

# Run main
main