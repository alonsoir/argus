# Obsolete Tests Archive

Tests moved here during Day 47 audit (29 Jan 2026).

## Reason for Archival:
These tests were experiments or validations that have been superseded 
by the comprehensive Day 46 test suite:
- test_sharded_flow_full_contract.cpp
- test_ring_consumer_protobuf.cpp
- test_sharded_flow_multithread.cpp

## Contents:

### Day 44 Race Condition Experiments:
- test_data_race_mut.cpp
- test_data_race_mut_fix3.cpp
- test_race_initialize.cpp
- test_race_initialize_fix1.cpp

Purpose: Reproduce and fix thread_local race conditions.
Status: Issues resolved in Day 45-46. Replaced by ShardedFlowManager tests.

### Phase 1 Legacy Tests:
- test_fast_detector.cpp
- test_integration_simple_event.cpp
- test_ransomware_feature_extractor.cpp

Purpose: Early Phase 1 validation.
Status: Superseded by comprehensive Day 46 integration tests.

### Standalone ShardedFlowManager Test:
- test_sharded_flow_manager.cpp (if duplicate)

Purpose: Early ShardedFlowManager validation.
Status: Merged into test_sharded_flow_full_contract.cpp

---

These tests are preserved for historical reference and can be restored
if needed. They are NOT compiled by default.

### Day 43 Prototype (Superseded by Day 46):
- test_sharded_flow_manager.cpp (271 lines, 25 Enero)

Purpose: Early prototype for ShardedFlowManager unit testing.
Status: REPLACED by test_sharded_flow_full_contract.cpp (Day 46).
Reason: Day 46 version is more comprehensive:
  - 313 lines vs 271 lines
  - 95.2% field population validation
  - TimeWindowManager integration
  - Complete contract validation

Note: This test was NEVER added to CMakeLists.txt (Day 43-47).
      It remained as an unused prototype file.
