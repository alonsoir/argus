// tests/test_firewall_csv_event_loader.cpp
// Day 69 — Unit tests for FirewallCsvEventLoader
//
// AUTHORS: Alonso Isidoro Roman + Claude (Anthropic)

#include "firewall_csv_event_loader.hpp"
#include <cassert>
#include <iostream>

using namespace ml_defender;

static void test_parse_ok_no_hmac() {
    FirewallCsvEventLoader loader("");
    FirewallEvent ev;
    std::string line = "1771404108582,111.182.236.62,58.122.96.132,RANSOMWARE,BLOCKED,0.9586,c3ddc9c8691bc073";
    assert(loader.parse(line, ev) == FirewallParseResult::OK);
    assert(ev.timestamp_ms   == 1771404108582ULL);
    assert(ev.source_ip      == "111.182.236.62");
    assert(ev.dest_ip        == "58.122.96.132");
    assert(ev.classification == "RANSOMWARE");
    assert(ev.action         == "BLOCKED");
    assert(ev.score          >  0.958f && ev.score < 0.960f);
    assert(loader.parsed_ok() == 1);
    std::cout << "[PASS] test_parse_ok_no_hmac\n";
}

static void test_malformed_too_few_cols() {
    FirewallCsvEventLoader loader("");
    FirewallEvent ev;
    std::string line = "1771404108582,111.182.236.62,RANSOMWARE";
    assert(loader.parse(line, ev) == FirewallParseResult::MALFORMED);
    assert(loader.parse_errors() == 1);
    std::cout << "[PASS] test_malformed_too_few_cols\n";
}

static void test_empty_line() {
    FirewallCsvEventLoader loader("");
    FirewallEvent ev;
    assert(loader.parse("", ev) == FirewallParseResult::EMPTY_LINE);
    assert(loader.parsed_ok() == 0);
    std::cout << "[PASS] test_empty_line\n";
}

static void test_comment_line() {
    FirewallCsvEventLoader loader("");
    FirewallEvent ev;
    assert(loader.parse("# this is a comment", ev) == FirewallParseResult::EMPTY_LINE);
    std::cout << "[PASS] test_comment_line\n";
}

static void test_malformed_bad_score() {
    FirewallCsvEventLoader loader("");
    FirewallEvent ev;
    std::string line = "1771404108582,111.182.236.62,58.122.96.132,RANSOMWARE,BLOCKED,NOT_A_FLOAT,abc";
    assert(loader.parse(line, ev) == FirewallParseResult::MALFORMED);
    std::cout << "[PASS] test_malformed_bad_score\n";
}

static void test_stats_accumulate() {
    FirewallCsvEventLoader loader("");
    FirewallEvent ev;
    loader.parse("1,1.1.1.1,2.2.2.2,DDOS,BLOCKED,0.5,hmac", ev);  // OK
    loader.parse("bad",                                             ev);  // MALFORMED
    loader.parse("",                                                ev);  // EMPTY
    assert(loader.parsed_ok()    == 1);
    assert(loader.parse_errors() == 1);
    std::cout << "[PASS] test_stats_accumulate\n";
}

int main() {
    test_parse_ok_no_hmac();
    test_malformed_too_few_cols();
    test_empty_line();
    test_comment_line();
    test_malformed_bad_score();
    test_stats_accumulate();
    std::cout << "\n[Day69] firewall_csv_event_loader: all tests passed\n";
    return 0;
}