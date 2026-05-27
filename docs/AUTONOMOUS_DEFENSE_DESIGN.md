# Autonomous AI-Driven Defense System - Design Document

> **Sistema de defensa autónomo con LLM para decisiones de seguridad en runtime y trazabilidad completa**

---

## 🎯 Executive Vision

### The Big Picture

```
Traditional Firewall:              Autonomous Defense System:
├─ Static rules                   ├─ LLM-driven decisions
├─ Manual updates                 ├─ Runtime filter updates
├─ Cryptic logs                   ├─ Natural language explanations
├─ Post-incident analysis         ├─ Real-time adaptive response
└─ Human in the loop              └─ Autonomous with oversight

                                  = NEXT GENERATION SECURITY
```

### Core Innovation

**El LLM proporciona dos capacidades críticas:**

1. **"El Filtro Adecuado"** - Decisiones contextuales optimizadas
    - No solo "bloquear IP X"
    - Sino "bloquear rango X-Y por Z tiempo porque [reasoning]"
    - Con protección de servicios críticos
    - Balance automático seguridad/disponibilidad

2. **"Trazabilidad Total"** - Audit trail completo y explicable
    - Cada decisión documentada
    - Razonamiento en lenguaje natural
    - Compliance-ready (SOC2, ISO27001, GDPR)
    - Rollback siempre disponible

---

## 🏗️ System Architecture

### End-to-End Flow

```
┌─────────────────────────────────────────────────────────────┐
│  DETECTION LAYER                                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Sniffer eBPF (Kernel Space)                            │ │
│  │   └─> Captura: 10,000 pkt/s desde 192.168.1.50 → 22   │ │
│  └────────────────────┬───────────────────────────────────┘ │
└───────────────────────┼─────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│  ANALYSIS LAYER                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ ML Detector (ONNX Models)                              │ │
│  │   ├─> Level 1: Binary (BENIGN/ATTACK)                 │ │
│  │   ├─> Level 2: DDoS Classification                    │ │
│  │   ├─> Level 3: Ransomware Detection                   │ │
│  │   └─> Output: {                                       │ │
│  │         type: "ddos",                                 │ │
│  │         confidence: 0.98,                             │ │
│  │         source_ips: ["192.168.1.50-55"],             │ │
│  │         target_port: 22,                              │ │
│  │         packet_count: 10000,                          │ │
│  │         duration: 30s                                 │ │
│  │       }                                               │ │
│  └────────────────────┬───────────────────────────────────┘ │
└───────────────────────┼─────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│  DECISION LAYER (LLM-Powered)                                │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ MCP Server + Claude API                                │ │
│  │                                                        │ │
│  │ Context Builder:                                       │ │
│  │   ├─> Threat details (from ML Detector)              │ │
│  │   ├─> Current filter state (from BPF maps)           │ │
│  │   ├─> Historical patterns (from etcd)                │ │
│  │   ├─> Network topology (critical services)           │ │
│  │   └─> Past decisions & outcomes                      │ │
│  │                                                        │ │
│  │ LLM Analysis:                                         │ │
│  │   "Coordinated DDoS from sequential IPs .50-.55.     │ │
│  │    Blocking individual IPs insufficient - they'll    │ │
│  │    rotate. Block /29 subnet for 2 hours.            │ │
│  │    Preserve SSH from 10.0.2.2 (management).         │ │
│  │    Monitor for escalation to /24."                   │ │
│  │                                                        │ │
│  │ Decision Output: {                                    │ │
│  │   action: "block_ip_range",                          │ │
│  │   targets: ["192.168.1.50-55"],                      │ │
│  │   duration_hours: 2,                                 │ │
│  │   preserve: ["10.0.2.2:22"],                         │ │
│  │   reasoning: "...",                                  │ │
│  │   escalation_plan: "If continues, block /24"        │ │
│  │ }                                                     │ │
│  └────────────────────┬───────────────────────────────────┘ │
└───────────────────────┼─────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│  VALIDATION LAYER (Safety-Critical)                          │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ RuntimeUpdateValidator (Multi-Layer)                   │ │
│  │                                                        │ │
│  │ Layer 1: Format Validation                            │ │
│  │   ├─> IP format valid? ✓                             │ │
│  │   ├─> Duration reasonable? ✓                         │ │
│  │   └─> Action type supported? ✓                       │ │
│  │                                                        │ │
│  │ Layer 2: Critical Service Protection                  │ │
│  │   ├─> Would block SSH management? ✗                  │ │
│  │   ├─> Would block etcd? ✗                            │ │
│  │   ├─> Would block monitoring? ✗                      │ │
│  │   └─> In whitelist? ✗                                │ │
│  │                                                        │ │
│  │ Layer 3: Self-Protection                              │ │
│  │   ├─> Would block sniffer itself? ✗                  │ │
│  │   └─> Would break management access? ✗               │ │
│  │                                                        │ │
│  │ Layer 4: Sanity Checks                                │ │
│  │   ├─> Too broad? (>50% traffic) ✗                    │ │
│  │   ├─> Too long? (>24h) ✗                             │ │
│  │   └─> Rate limit OK? ✓                               │ │
│  │                                                        │ │
│  │ Result: ✅ SAFE TO APPLY                              │ │
│  └────────────────────┬───────────────────────────────────┘ │
└───────────────────────┼─────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│  ENFORCEMENT LAYER                                           │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Runtime Filter Updater                                 │ │
│  │                                                        │ │
│  │ Atomic Update:                                        │ │
│  │   ├─> Snapshot current state                         │ │
│  │   ├─> Apply BPF map update                           │ │
│  │   │    bpf_map_update_elem(                          │ │
│  │   │      blocked_ip_ranges_fd,                       │ │
│  │   │      &range_key,                                 │ │
│  │   │      &range_value,                               │ │
│  │   │      BPF_ANY                                     │ │
│  │   │    )                                             │ │
│  │   ├─> Verify: packet drop rate normalized? ✓         │ │
│  │   └─> Store rollback snapshot                        │ │
│  │                                                        │ │
│  │ Effect: IMMEDIATE (<100ms)                            │ │
│  │   └─> Next packet from 192.168.1.50 → XDP_DROP       │ │
│  └────────────────────┬───────────────────────────────────┘ │
└───────────────────────┼─────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│  AUDIT LAYER (Trazabilidad Total)                           │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Decision Logger + etcd Store                           │ │
│  │                                                        │ │
│  │ Audit Entry: {                                        │ │
│  │   event_id: "evt-ddos-20251026-142345",              │ │
│  │   timestamp: "2025-10-26T14:23:45Z",                 │ │
│  │   trigger: {                                          │ │
│  │     source: "ml_detector",                           │ │
│  │     confidence: 0.98,                                │ │
│  │     threat_type: "ddos"                              │ │
│  │   },                                                  │ │
│  │   llm_decision: {                                     │ │
│  │     model: "claude-sonnet-4-20250514",               │ │
│  │     action: "block_ip_range",                        │ │
│  │     targets: ["192.168.1.50-55"],                    │ │
│  │     duration_hours: 2,                               │ │
│  │     reasoning: "Coordinated DDoS...",                │ │
│  │     alternatives_considered: [...]                   │ │
│  │   },                                                  │ │
│  │   validation: {                                       │ │
│  │     result: "SAFE",                                  │ │
│  │     checks_passed: 12,                               │ │
│  │     checks_failed: 0                                 │ │
│  │   },                                                  │ │
│  │   application: {                                      │ │
│  │     status: "SUCCESS",                               │ │
│  │     latency_ms: 340,                                 │ │
│  │     bpf_map_updated: true                            │ │
│  │   },                                                  │ │
│  │   rollback: {                                         │ │
│  │     available: true,                                 │ │
│  │     snapshot_id: "snap-142345",                      │ │
│  │     expires_at: "2025-10-26T16:23:45Z"              │ │
│  │   },                                                  │ │
│  │   human_override: null                               │ │
│  │ }                                                     │ │
│  │                                                        │ │
│  │ Stored in:                                            │ │
│  │   ├─> etcd: /audit/decisions/evt-ddos-...           │ │
│  │   ├─> PostgreSQL: compliance.audit_log               │ │
│  │   └─> S3: long-term archival                         │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## 💻 Implementation Details

### 1. MCP Server - LLM Decision Engine

**File:** `mcp_server/threat_response.py`

```python
from anthropic import Anthropic
from typing import Dict, List, Optional
import json
import asyncio
from datetime import datetime, timedelta

class ThreatResponseMCP:
    """
    MCP Server that uses Claude for autonomous security decisions.
    
    Key Features:
    - Context-aware threat analysis
    - Multi-factor decision making
    - Explainable recommendations
    - Safety validation integration
    """
    
    def __init__(self, config: Dict):
        self.client = Anthropic(api_key=config['anthropic_api_key'])
        self.model = "claude-sonnet-4-20250514"
        self.validator = SafetyValidator(config)
        self.context_builder = ContextBuilder(config)
        self.audit_logger = AuditLogger(config)
    
    async def analyze_threat(self, threat_event: Dict) -> Dict:
        """
        Main entry point for threat analysis.
        
        Args:
            threat_event: {
                'type': 'ddos' | 'ransomware' | 'port_scan',
                'source_ips': List[str],
                'target_port': int,
                'confidence': float,
                'packet_count': int,
                'duration_seconds': int,
                'features': Dict  # ML model features
            }
        
        Returns:
            {
                'decision': Dict,      # Recommended action
                'reasoning': str,      # Natural language explanation
                'alternatives': List,  # Other options considered
                'risk_assessment': Dict
            }
        """
        
        # Build rich context for LLM
        context = await self.context_builder.build({
            'threat': threat_event,
            'current_filters': await self.get_current_filters(),
            'network_topology': await self.get_network_topology(),
            'recent_history': await self.get_recent_attacks(),
            'traffic_baseline': await self.get_traffic_baseline()
        })
        
        # Construct prompt for Claude
        prompt = self._build_security_prompt(context)
        
        # Get LLM decision
        response = await self._query_claude(prompt)
        
        # Parse and validate
        decision = self._parse_decision(response)
        
        # Safety validation
        validation_result = await self.validator.validate(decision)
        
        if validation_result.status == "DANGEROUS":
            # Log rejection
            await self.audit_logger.log_rejected_decision(
                decision, validation_result.reason
            )
            return {
                'status': 'rejected',
                'reason': validation_result.reason,
                'suggestion': 'Manual review required'
            }
        
        # Log approved decision
        event_id = await self.audit_logger.log_decision(
            threat_event, decision, validation_result
        )
        
        return {
            'status': 'approved',
            'event_id': event_id,
            'decision': decision,
            'validation': validation_result
        }
    
    def _build_security_prompt(self, context: Dict) -> str:
        """
        Construct detailed prompt for Claude with all context.
        """
        return f"""You are an expert cybersecurity analyst making real-time decisions 
for an autonomous defense system.

CURRENT THREAT:
Type: {context['threat']['type'].upper()}
Source IPs: {context['threat']['source_ips']}
Target Port: {context['threat']['target_port']}
Confidence: {context['threat']['confidence']:.2%}
Packet Count: {context['threat']['packet_count']:,}
Duration: {context['threat']['duration_seconds']}s

CURRENT FILTER STATE:
Blocked IPs: {context['current_filters']['blocked_ips']}
Blocked Ports: {context['current_filters']['blocked_ports']}
Active Rules: {len(context['current_filters']['active_rules'])}

NETWORK TOPOLOGY:
Critical Services: {context['network_topology']['critical_services']}
Management Access: {context['network_topology']['management_ips']}
Internal Subnets: {context['network_topology']['internal_subnets']}

RECENT HISTORY (Last 24h):
Similar Attacks: {context['recent_history']['similar_attacks']}
False Positives: {context['recent_history']['false_positives']}
Successful Blocks: {context['recent_history']['successful_blocks']}

TRAFFIC BASELINE:
Normal packet/s: {context['traffic_baseline']['normal_pps']}
Current packet/s: {context['traffic_baseline']['current_pps']}
Anomaly Score: {context['traffic_baseline']['anomaly_score']}

TASK:
Recommend the optimal filtering action to mitigate this threat while:
1. Minimizing false positives (don't block legitimate traffic)
2. Protecting critical services (SSH, etcd, monitoring)
3. Being proportional (don't over-block)
4. Considering attack evolution (they may adapt)

Respond ONLY with valid JSON in this exact format:
{{
  "action": "block_ip" | "block_ip_range" | "block_port" | "rate_limit" | "monitor_only",
  "targets": ["192.168.1.50-55"],
  "duration_hours": 2,
  "priority": "low" | "medium" | "high" | "critical",
  "preserve": ["10.0.2.2:22"],
  "reasoning": "Detailed explanation of why this is optimal",
  "alternatives_considered": [
    {{"action": "...", "pros": "...", "cons": "..."}},
    ...
  ],
  "escalation_plan": "What to do if attack continues or intensifies",
  "expected_impact": {{"blocked_ips": N, "affected_traffic_pct": X}},
  "rollback_trigger": "Conditions under which to auto-rollback"
}}

CRITICAL: Your decision will be automatically applied. Be conservative but effective.
"""
    
    async def _query_claude(self, prompt: str) -> str:
        """Query Claude API with retry logic."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=2000,
                    temperature=0.3,  # Lower temp for consistency
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.content[0].text
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
    
    def _parse_decision(self, response_text: str) -> Dict:
        """Parse and validate LLM response."""
        # Strip markdown code blocks if present
        text = response_text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        
        try:
            decision = json.loads(text.strip())
            
            # Validate required fields
            required = ['action', 'targets', 'duration_hours', 'reasoning']
            for field in required:
                if field not in decision:
                    raise ValueError(f"Missing required field: {field}")
            
            return decision
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON from LLM: {e}")
```

---

### 2. Safety Validator - Multi-Layer Protection

**File:** `include/runtime_update_validator.hpp`

```cpp
#pragma once
#include <string>
#include <vector>
#include <set>
#include <map>
#include "common_types.hpp"

namespace security {

enum class ValidationResult {
    SAFE,           // ✅ Apply immediately
    RISKY,          // ⚠️  Apply with enhanced monitoring
    DANGEROUS,      // ❌ Reject - too risky
    INVALID         // ❌ Reject - malformed
};

struct UpdateRequest {
    enum Type {
        BLOCK_IP,
        BLOCK_IP_RANGE,
        BLOCK_PORT,
        RATE_LIMIT,
        ALLOW_IP,
        MODIFY_DEFAULT_ACTION
    };
    
    Type type;
    std::vector<std::string> targets;  // IPs, IP ranges, ports
    uint32_t duration_seconds;
    std::string reason;
    std::string event_id;
    
    // Optional
    std::vector<std::string> preserve;  // Protected resources
    std::string escalation_plan;
};

struct ValidationReport {
    ValidationResult result;
    std::string reason;
    std::vector<std::string> warnings;
    std::vector<std::string> checks_passed;
    std::vector<std::string> checks_failed;
    
    // Risk metrics
    float estimated_traffic_impact;  // 0.0 - 1.0
    size_t affected_ip_count;
    bool affects_critical_service;
};

class RuntimeUpdateValidator {
public:
    RuntimeUpdateValidator(const std::string& config_path);
    
    ValidationReport validate(const UpdateRequest& request);
    
    // Configuration
    void add_critical_service(const std::string& ip, uint16_t port);
    void add_whitelist_ip(const std::string& ip);
    void set_max_block_duration(uint32_t seconds);
    void set_max_ip_block_percentage(float pct);
    
private:
    // Layer 1: Format Validation
    bool validate_format(const UpdateRequest& req, ValidationReport& report);
    bool is_valid_ip(const std::string& ip);
    bool is_valid_ip_range(const std::string& range);
    bool is_valid_port(const std::string& port);
    
    // Layer 2: Critical Resource Protection
    bool check_critical_services(const UpdateRequest& req, ValidationReport& report);
    bool would_block_critical_service(const UpdateRequest& req);
    bool is_in_whitelist(const std::string& ip);
    
    // Layer 3: Self-Protection
    bool check_self_protection(const UpdateRequest& req, ValidationReport& report);
    bool would_block_management_interface(const UpdateRequest& req);
    bool would_block_sniffer_itself(const UpdateRequest& req);
    
    // Layer 4: Sanity Checks
    bool check_sanity(const UpdateRequest& req, ValidationReport& report);
    bool is_overly_broad(const UpdateRequest& req);
    bool exceeds_duration_limit(const UpdateRequest& req);
    bool exceeds_rate_limit(const UpdateRequest& req);
    
    // Helpers
    size_t estimate_affected_ips(const UpdateRequest& req);
    float estimate_traffic_impact(const UpdateRequest& req);
    
    // Configuration
    struct Config {
        std::set<std::pair<std::string, uint16_t>> critical_services;
        std::set<std::string> whitelist_ips;
        uint32_t max_block_duration_seconds = 24 * 3600;  // 24h
        float max_ip_block_percentage = 0.3;  // 30% of address space
        uint32_t max_updates_per_minute = 10;
        std::string management_ip;
        std::string sniffer_ip;
    } config_;
    
    // Rate limiting
    std::map<std::chrono::system_clock::time_point, size_t> recent_updates_;
};

} // namespace security
```

**Implementation:** `src/security/runtime_update_validator.cpp`

```cpp
#include "runtime_update_validator.hpp"
#include <iostream>
#include <regex>
#include <arpa/inet.h>

namespace security {

RuntimeUpdateValidator::RuntimeUpdateValidator(const std::string& config_path) {
    // Load config from JSON
    // ...
    
    // Default critical services
    config_.critical_services = {
        {"127.0.0.1", 22},      // SSH localhost
        {"10.0.2.2", 22},       // Vagrant host SSH
        {"127.0.0.1", 2379},    // etcd
        {"127.0.0.1", 9090},    // Prometheus
    };
    
    // Default whitelist
    config_.whitelist_ips = {
        "127.0.0.1",
        "10.0.2.2",  // Vagrant host
    };
}

ValidationReport RuntimeUpdateValidator::validate(const UpdateRequest& request) {
    ValidationReport report;
    report.result = ValidationResult::SAFE;
    
    // Layer 1: Format
    if (!validate_format(request, report)) {
        report.result = ValidationResult::INVALID;
        report.reason = "Invalid format";
        return report;
    }
    
    // Layer 2: Critical Services
    if (!check_critical_services(request, report)) {
        report.result = ValidationResult::DANGEROUS;
        report.reason = "Would block critical service";
        return report;
    }
    
    // Layer 3: Self-Protection
    if (!check_self_protection(request, report)) {
        report.result = ValidationResult::DANGEROUS;
        report.reason = "Would block system management";
        return report;
    }
    
    // Layer 4: Sanity
    if (!check_sanity(request, report)) {
        if (report.checks_failed.size() > 2) {
            report.result = ValidationResult::DANGEROUS;
            report.reason = "Failed multiple sanity checks";
        } else {
            report.result = ValidationResult::RISKY;
            report.reason = "Some sanity checks failed - apply with caution";
        }
        return report;
    }
    
    // Calculate risk metrics
    report.affected_ip_count = estimate_affected_ips(request);
    report.estimated_traffic_impact = estimate_traffic_impact(request);
    
    // Final decision
    if (report.estimated_traffic_impact > 0.5) {
        report.result = ValidationResult::RISKY;
        report.warnings.push_back("High traffic impact (>50%)");
    }
    
    return report;
}

bool RuntimeUpdateValidator::check_critical_services(
    const UpdateRequest& req, 
    ValidationReport& report
) {
    for (const auto& target : req.targets) {
        // Check if target would block any critical service
        for (const auto& [ip, port] : config_.critical_services) {
            if (req.type == UpdateRequest::BLOCK_IP || 
                req.type == UpdateRequest::BLOCK_IP_RANGE) {
                
                if (target == ip) {
                    report.checks_failed.push_back(
                        "Would block critical service: " + ip + ":" + std::to_string(port)
                    );
                    report.affects_critical_service = true;
                    return false;
                }
            }
            
            if (req.type == UpdateRequest::BLOCK_PORT) {
                uint16_t target_port = std::stoi(target);
                if (target_port == port) {
                    report.checks_failed.push_back(
                        "Would block critical port: " + std::to_string(port)
                    );
                    return false;
                }
            }
        }
        
        // Check whitelist
        if (is_in_whitelist(target)) {
            report.checks_failed.push_back("Target in whitelist: " + target);
            return false;
        }
    }
    
    report.checks_passed.push_back("No critical services affected");
    return true;
}

bool RuntimeUpdateValidator::check_sanity(
    const UpdateRequest& req,
    ValidationReport& report
) {
    bool all_passed = true;
    
    // Check 1: Duration reasonable?
    if (req.duration_seconds > config_.max_block_duration_seconds) {
        report.checks_failed.push_back(
            "Duration exceeds maximum: " + 
            std::to_string(req.duration_seconds / 3600) + "h"
        );
        all_passed = false;
    } else {
        report.checks_passed.push_back("Duration reasonable");
    }
    
    // Check 2: Not too broad?
    size_t affected_ips = estimate_affected_ips(req);
    // Assuming /24 network = 254 usable IPs
    size_t total_ips = 254;
    float block_pct = static_cast<float>(affected_ips) / total_ips;
    
    if (block_pct > config_.max_ip_block_percentage) {
        report.checks_failed.push_back(
            "Blocks too many IPs: " + std::to_string(int(block_pct * 100)) + "%"
        );
        all_passed = false;
    } else {
        report.checks_passed.push_back("Block scope reasonable");
    }
    
    // Check 3: Rate limit
    if (!exceeds_rate_limit(req)) {
        report.checks_passed.push_back("Within rate limit");
    } else {
        report.checks_failed.push_back("Too many updates recently");
        all_passed = false;
    }
    
    return all_passed;
}

size_t RuntimeUpdateValidator::estimate_affected_ips(const UpdateRequest& req) {
    size_t count = 0;
    
    for (const auto& target : req.targets) {
        if (target.find('-') != std::string::npos) {
            // IP range: 192.168.1.50-55 = 6 IPs
            auto dash_pos = target.find('-');
            int start = std::stoi(target.substr(target.rfind('.') + 1, dash_pos));
            int end = std::stoi(target.substr(dash_pos + 1));
            count += (end - start + 1);
        } else if (target.find('/') != std::string::npos) {
            // CIDR: 192.168.1.0/24 = 256 IPs
            auto slash_pos = target.find('/');
            int prefix = std::stoi(target.substr(slash_pos + 1));
            count += (1 << (32 - prefix));
        } else {
            // Single IP
            count += 1;
        }
    }
    
    return count;
}

} // namespace security
```

---

### 3. Audit Logger - Trazabilidad Completa

**File:** `include/audit_logger.hpp`

```cpp
#pragma once
#include <string>
#include <memory>
#include "common_types.hpp"

namespace security {

struct AuditEntry {
    std::string event_id;
    std::chrono::system_clock::time_point timestamp;
    
    // Trigger
    struct {
        std::string source;  // "ml_detector", "manual", "scheduled"
        float confidence;
        std::string threat_type;
    } trigger;
    
    // LLM Decision
    struct {
        std::string model;
        std::string action;
        std::vector<std::string> targets;
        uint32_t duration_hours;
        std::string reasoning;
        std::vector<std::string> alternatives_considered;
    } llm_decision;
    
    // Validation
    struct {
        std::string result;  // "SAFE", "RISKY", "DANGEROUS"
        size_t checks_passed;
        size_t checks_failed;
        std::vector<std::string> warnings;
    } validation;
    
    // Application
    struct {
        std::string status;  // "SUCCESS", "FAILED", "ROLLED_BACK"
        uint32_t latency_ms;
        bool bpf_map_updated;
        std::string error_message;
    } application;
    
    // Rollback
    struct {
        bool available;
        std::string snapshot_id;
        std::chrono::system_clock::time_point expires_at;
    } rollback;
    
    // Human oversight
    std::optional<std::string> human_override;
    std::optional<std::string> human_comment;
};

class AuditLogger {
public:
    AuditLogger(const std::string& config_path);
    
    // Logging
    std::string log_decision(
        const Dict& threat_event,
        const Dict& llm_decision,
        const ValidationReport& validation
    );
    
    void log_application(
        const std::string& event_id,
        bool success,
        uint32_t latency_ms,
        const std::string& error = ""
    );
    
    void log_rollback(
        const std::string& event_id,
        const std::string& reason
    );
    
    void log_human_override(
        const std::string& event_id,
        const std::string& action,
        const std::string& comment
    );
    
    // Querying
    std::vector<AuditEntry> get_recent(size_t count);
    AuditEntry get_by_id(const std::string& event_id);
    std::vector<AuditEntry> query(const std::string& criteria);
    
    // Reporting
    std::string generate_report(
        const std::string& event_id,
        const std::string& format = "json"  // json, markdown, executive
    );
    
private:
    // Storage backends
    class EtcdStore;
    class PostgreSQLStore;
    class S3Archive;
    
    std::unique_ptr<EtcdStore> etcd_;
    std::unique_ptr<PostgreSQLStore> db_;
    std::unique_ptr<S3Archive> archive_;
    
    std::string generate_event_id();
};

} // namespace security
```

---

## 🎯 Use Cases

### Use Case 1: DDoS Attack Response

**Scenario:** Coordinated DDoS from botnet

```
14:23:30 - ML Detector: DDoS detected
           ├─> Confidence: 98%
           ├─> Sources: 192.168.1.50-55 (6 IPs)
           └─> Target: Port 22 (SSH)

14:23:35 - MCP Server: Context analysis
           ├─> Pattern: Sequential IPs suggest botnet
           ├─> History: No similar attacks in 30 days
           └─> Risk: High - SSH is critical service

14:23:40 - LLM Decision:
           "Block IP range 192.168.1.50-55 for 2 hours.
            Sequential IPs indicate coordinated attack.
            Individual blocks insufficient - botnet will rotate.
            Preserve management SSH from 10.0.2.2.
            Monitor for escalation to broader /24 subnet."

14:23:42 - Validation: ✅ SAFE
           ├─> No critical services blocked
           ├─> Management access preserved
           ├─> Duration reasonable (2h)
           └─> Scope appropriate (6 IPs)

14:23:45 - Applied: XDP_DROP for 192.168.1.50-55
           └─> Attack mitigated in 15 seconds

Result: ✅ Zero downtime, surgical blocking, full audit trail
```

---

### Use Case 2: False Positive Prevention

**Scenario:** Aggressive web scraper triggers alert

```
09:15:00 - ML Detector: Possible DDoS
           ├─> Confidence: 75% (lower than usual)
           ├─> Source: 198.51.100.42 (single IP)
           └─> Pattern: High request rate to port 80

09:15:05 - MCP Server: Context analysis
           ├─> Single IP (not botnet pattern)
           ├─> Known search engine IP range
           ├─> Historical: Seen before, legitimate traffic
           └─> Risk: Low - likely false positive

09:15:10 - LLM Decision:
           "MONITOR ONLY - do not block.
            Single IP with legitimate reverse DNS.
            High request rate but within normal for scraper.
            Falls within known search engine subnet.
            Recommend rate limiting instead of block."

09:15:12 - Validation: ✅ SAFE (monitor action)

09:15:15 - Applied: Rate limit to 100 req/min
           └─> No block, service available

Result: ✅ Avoided false positive, maintained availability
```

---

### Use Case 3: Escalation to Human

**Scenario:** Ambiguous threat requiring judgment

```
16:45:00 - ML Detector: Ransomware indicators
           ├─> Confidence: 82%
           ├─> Source: 10.0.1.100 (internal IP!)
           └─> Pattern: SMB scanning + encryption

16:45:05 - MCP Server: Context analysis
           ├─> INTERNAL IP - this is critical
           ├─> Could be legitimate admin activity
           ├─> Could be compromised internal host
           └─> Risk: Extremely high if wrong decision

16:45:10 - LLM Decision:
           "ESCALATE TO HUMAN - too risky for automation.
            Internal IP makes false positive catastrophic.
            Block would isolate potentially critical system.
            Recommend: Immediate SOC notification + manual review.
            Temporary: Rate limit + enhanced monitoring."

16:45:12 - Validation: ⚠️  RISKY
           └─> Triggered human review requirement

16:45:15 - Action: Alert sent to SOC
           ├─> Enhanced monitoring enabled
           ├─> Rate limit applied
           └─> Awaiting human decision

Result: ✅ Conservative approach, human in loop for edge case
```

---

## 📊 Enterprise Value

### Compliance & Audit

**SOC 2 Type II Compliance:**
```
Auditor Question: "How do you ensure security decisions are traceable?"

System Response:
┌───────────────────────────────────────────────────┐
│ Complete audit trail for every decision:          │
│                                                    │
│ ✅ What was decided (action + targets)            │
│ ✅ Why it was decided (LLM reasoning)             │
│ ✅ When it was decided (timestamp + duration)     │
│ ✅ Who/what decided (ML model + LLM model)        │
│ ✅ How it was validated (safety checks)           │
│ ✅ What was the outcome (success/failure metrics) │
│ ✅ Rollback capability (snapshot + expiration)    │
│                                                    │
│ All stored in:                                     │
│ - etcd (real-time access)                         │
│ - PostgreSQL (structured queries)                 │
│ - S3 (long-term archival, 7 years)               │
└───────────────────────────────────────────────────┘
```

**GDPR - Explainable AI:**
```
Data Subject Request: "Why was my IP blocked?"

System Response (Natural Language):
┌───────────────────────────────────────────────────┐
│ Your IP (192.168.1.50) was temporarily blocked    │
│ on October 26, 2025 at 14:23:45 UTC.             │
│                                                    │
│ REASON:                                            │
│ Our ML detection system identified a coordinated  │
│ DDoS attack pattern from your IP and 5 others    │
│ (.50-.55) targeting our SSH service. The pattern │
│ matched known botnet behavior with 98% confidence.│
│                                                    │
│ DECISION PROCESS:                                  │
│ Our AI security analyst (Claude) recommended      │
│ blocking the IP range for 2 hours to protect     │
│ service availability. This was the most surgical  │
│ response - blocking only the attacking IPs while  │
│ preserving access for all other users.           │
│                                                    │
│ OUTCOME:                                           │
│ Block was automatically lifted after 2 hours.     │
│ No permanent restriction on your IP.              │
│                                                    │
│ APPEAL:                                            │
│ If you believe this was incorrect, contact:       │
│ security@company.com with reference ID:           │
│ evt-ddos-20251026-142345                          │
└───────────────────────────────────────────────────┘
```

---

### Cost-Benefit Analysis

```
Traditional SOC:                 AI-Driven System:
├─ 24/7 human analysts          ├─ Automated 24/7 response
├─ Response time: 15-30 min     ├─> Response time: <1 second
├─ Cost: $500K/year             ├─> Cost: $50K/year (90% savings)
├─ Consistency: Variable        ├─> Consistency: High
├─ Documentation: Manual        ├─> Documentation: Automatic
├─> False positives: 20-30%     ├─> False positives: <5%
└─ Capacity: Limited            └─> Capacity: Unlimited
```

---

## 🚀 Implementation Roadmap

### Phase 1: Foundation (Q4 2025)
```
Week 1-2: Runtime Filter Updates
[ ] Extend BPF maps for IP ranges
[ ] Implement atomic update mechanism
[ ] Add rollback capability
[ ] Testing & validation

Week 3-4: Safety Validator
[ ] Multi-layer validation logic
[ ] Whitelist/blacklist management
[ ] Rate limiting
[ ] Integration tests
```

### Phase 2: MCP Integration (Q1 2026)
```
Week 1-2: MCP Server
[ ] Python MCP server skeleton
[ ] Claude API integration
[ ] Context builder
[ ] Decision parser

Week 3-4: End-to-End
[ ] ML Detector → MCP → Validator → BPF
[ ] Audit logging
[ ] Monitoring dashboard
[ ] Production testing
```

### Phase 3: Advanced Features (Q2 2026)
```
Week 1-2: Learning Loop
[ ] Feedback collection (was decision correct?)
[ ] Context enrichment from outcomes
[ ] Continuous improvement

Week 3-4: Autonomous Mode
[ ] Supervised mode (human approval required)
[ ] Semi-autonomous (auto-apply SAFE decisions)
[ ] Fully autonomous (human oversight only)
[ ] Emergency stop mechanism
```

---

## ⚠️ Safety Mechanisms

### 1. Emergency Stop
```cpp
// Panic button - revert to manual mode
void emergency_stop() {
    autonomous_mode_ = false;
    revert_to_baseline_filters();
    alert_human_operators();
    log_emergency_stop(reason);
}
```

### 2. Automatic Rollback
```cpp
// Monitor impact - auto-rollback if catastrophic
if (legitimate_traffic_drop > 0.9) {
    rollback_last_update();
    disable_autonomous_mode();
    alert_operators("Catastrophic filter applied");
}
```

### 3. Human Override Always Available
```bash
# CLI tool for immediate human control
$ sniffer-admin override --event evt-ddos-xxx --action unblock
✅ Override applied
✅ Autonomous mode paused
✅ Human review required for re-enable
```

---

## 🎯 Success Metrics

**Technical KPIs:**
- Attack mitigation latency: <1 second (from detection to block)
- False positive rate: <5%
- Availability during attack: >99.9%
- Rollback success rate: 100%

**Business KPIs:**
- SOC cost reduction: >80%
- Mean time to respond (MTTR): <1 minute
- Audit compliance: 100%
- Human escalations: <10% of total events

---

## 📚 References

- [Anthropic Claude API](https://docs.anthropic.com/claude/reference)
- [Model Context Protocol (MCP)](https://github.com/anthropics/anthropic-mcp)
- [eBPF Runtime Updates](https://ebpf.io/what-is-ebpf/)
- [Explainable AI Guidelines (GDPR)](https://gdpr-info.eu/)

---

<div align="center">

## 🛡️ The Future of Autonomous Security 🛡️

**AI-Driven • Explainable • Compliant • Effective**

*Design Document v1.0 - October 26, 2025*

**"El filtro adecuado + Trazabilidad total = Nuevo estándar de seguridad"**

</div>