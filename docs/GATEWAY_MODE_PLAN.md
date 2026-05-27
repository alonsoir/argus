# Gateway Mode Implementation Plan

## 🎯 Objective

Transform ML Defender from a **host-based IDS** into a **dual-mode system** supporting both host-based and gateway deployments.

## 📐 Architecture Overview

### Current State (Host-Based IDS)
```
Traffic Flow:
  Packet → eth1 → XDP hook → Destination check:
    - dst_ip == VM_ip?  → PROCESS & PASS
    - dst_ip != VM_ip?  → DROP (ignored)

Result: Only captures traffic TO/FROM this host
```

### Target State (Gateway Mode)
```
Traffic Flow:
  Packet → eth1 → XDP hook → Mode check:
    - mode == GATEWAY?  → PROCESS ALL & FORWARD
    - mode == HOST?     → PROCESS LOCAL ONLY & PASS

Result: Captures ALL traffic passing through the system
```

## 🔧 Technical Changes Required

### 1. XDP/eBPF Modifications

**File:** `sniffer/src/kernel/sniffer.bpf.c`

**Current Logic:**
```c
SEC("xdp")
int xdp_packet_filter(struct xdp_md *ctx) {
    // Implicitly filters for local traffic only
    process_packet(ctx);
    return XDP_PASS;
}
```

**New Logic:**
```c
// BPF map for deployment mode
struct {
    __uint(type, BPF_MAP_TYPE_ARRAY);
    __uint(max_entries, 1);
    __type(key, __u32);
    __type(value, __u32);
} deployment_mode_map SEC(".maps");

#define MODE_HOST    0
#define MODE_GATEWAY 1
#define MODE_MONITOR 2

SEC("xdp")
int xdp_packet_filter(struct xdp_md *ctx) {
    __u32 key = 0;
    __u32 *mode = bpf_map_lookup_elem(&deployment_mode_map, &key);
    
    if (!mode) {
        return XDP_PASS;  // Fallback: pass all
    }
    
    // Process packet for ML analysis
    process_packet(ctx);
    
    // Action based on deployment mode
    switch (*mode) {
        case MODE_GATEWAY:
            // Gateway: Process ALL packets, forward to stack
            return XDP_PASS;
        
        case MODE_HOST:
            // Host: Process only local traffic
            if (is_local_traffic(ctx)) {
                return XDP_PASS;
            }
            return XDP_PASS;  // Still pass non-local (just don't process)
        
        case MODE_MONITOR:
            // Monitor: Process ALL, but never block
            return XDP_PASS;
        
        default:
            return XDP_PASS;
    }
}

static __always_inline bool is_local_traffic(struct xdp_md *ctx) {
    // Check if packet is destined to/from this host
    // Implementation: Compare dst_ip with interface IP
    return true;  // Placeholder
}
```

### 2. Configuration Changes

**File:** `sniffer/config/sniffer.json`

**Add deployment_mode section:**
```json
{
  "profile": "lab",
  "deployment": {
    "mode": "gateway",  // "host" | "gateway" | "monitor"
    "description": "Gateway mode for network-wide protection"
  },
  "capture_interface": "eth1",
  "gateway_settings": {
    "enable_ip_forwarding": true,
    "bridge_interface": "eth1",
    "forward_action": "drop_malicious",  // "drop_malicious" | "alert_only"
    "iptables_chain": "FORWARD"  // "INPUT" for host, "FORWARD" for gateway
  }
}
```

### 3. IP Forwarding Support

**File:** `sniffer/scripts/setup_gateway.sh`
```bash
#!/bin/bash
# Setup gateway mode for ML Defender

set -e

echo "🌐 Configuring ML Defender Gateway Mode..."

# Enable IP forwarding
echo "1. Enabling IP forwarding..."
sudo sysctl -w net.ipv4.ip_forward=1
sudo sysctl -w net.ipv6.conf.all.forwarding=1

# Make persistent
echo "net.ipv4.ip_forward=1" | sudo tee -a /etc/sysctl.conf
echo "net.ipv6.conf.all.forwarding=1" | sudo tee -a /etc/sysctl.conf

# Configure NAT (if needed)
echo "2. Configuring NAT..."
sudo iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE

# Allow forwarding from eth1 to eth0
echo "3. Configuring forwarding rules..."
sudo iptables -A FORWARD -i eth1 -o eth0 -j ACCEPT
sudo iptables -A FORWARD -i eth0 -o eth1 -m state --state RELATED,ESTABLISHED -j ACCEPT

# ML Defender will insert rules at position 1 for DROP malicious
echo "4. Gateway configured successfully ✅"
echo ""
echo "ML Defender will now:"
echo "  - Process ALL traffic passing through"
echo "  - Drop malicious traffic in FORWARD chain"
echo "  - Forward benign traffic normally"
```

### 4. Firewall Integration Changes

**File:** `firewall-acl-agent/config/firewall.json`

**Update for gateway mode:**
```json
{
  "deployment": {
    "mode": "gateway"  // "host" | "gateway"
  },
  "iptables": {
    "chain": "FORWARD",  // "INPUT" for host, "FORWARD" for gateway
    "blacklist_ipset": "ml_defender_blacklist_test",
    "whitelist_ipset": "ml_defender_whitelist",
    "action": "DROP"  // DROP for gateway, REJECT for host
  }
}
```

**File:** `firewall-acl-agent/src/iptables_manager.cpp`

**Update rule generation:**
```cpp
void IPTablesManager::setup_rules() {
    std::string chain = config_.deployment.mode == "gateway" ? "FORWARD" : "INPUT";
    
    // Whitelist rule (position 1)
    std::string cmd_whitelist = "iptables -I " + chain + " 1 "
        "-m set --match-set " + config_.iptables.whitelist_ipset + " src "
        "-j ACCEPT "
        "-m comment --comment 'ML Defender Whitelist'";
    
    // Blacklist rule (position 2)
    std::string cmd_blacklist = "iptables -I " + chain + " 2 "
        "-m set --match-set " + config_.iptables.blacklist_ipset + " src "
        "-j " + config_.iptables.action + " "
        "-m comment --comment 'ML Defender Blacklist'";
    
    execute_command(cmd_whitelist);
    execute_command(cmd_blacklist);
}
```

## 📊 Testing Plan

### Phase 1: Local Testing (VM as Gateway)

**Setup:**
```bash
# Configure VM as gateway
cd /vagrant/sniffer/scripts
./setup_gateway.sh

# Verify IP forwarding
sysctl net.ipv4.ip_forward  # Should be 1

# Check NAT rules
sudo iptables -t nat -L -n -v
```

**Test 1: MAWI Dataset Replay**
```bash
# Replay MAWI traffic THROUGH the VM
sudo tcpreplay --intf1=eth1 --pps=100 /vagrant/mawi/mawi-vm-ready.pcap

# Monitor capture
tail -f /vagrant/logs/lab/detector.log | grep "received="

# Expected: Detector sees ALL replayed packets (not just local)
```

**Test 2: Synthetic Traffic Through Gateway**
```bash
# From Mac, send traffic to external IP (8.8.8.8)
# Route through VM as gateway

ping -c 100 8.8.8.8

# Monitor
tail -f /vagrant/logs/lab/sniffer.log | grep "procesados"

# Expected: Sniffer captures ping traffic (even though dst != VM)
```

### Phase 2: Real Malware Validation

**Dataset:** CTU-13 Botnet Traffic
```bash
# Download CTU-13 scenario 1
wget https://mcfp.felk.cvut.cz/publicDatasets/CTU-13-Dataset/CTU-13/1/capture20110810.pcap.gz
gunzip capture20110810.pcap.gz

# Rewrite IPs for VM network
tcprewrite --infile=capture20110810.pcap \
           --outfile=ctu13-ready.pcap \
           --pnat=0.0.0.0/0:192.168.56.0/24

# Replay through gateway
sudo tcpreplay --intf1=eth1 ctu13-ready.pcap

# Analyze detections
grep "attacks=" /vagrant/logs/lab/detector.log | tail -20
sudo ipset list ml_defender_blacklist_test
```

### Phase 3: Performance Benchmarking

**Metrics to Measure:**
- Throughput (pps) in gateway mode
- Latency added by XDP processing
- CPU usage under high traffic
- Memory consumption with 100K+ flows
- Packet drop rate (if any)

**Tools:**
- `iperf3` for bandwidth testing
- `tcpreplay` with `--pps` for controlled rates
- `top` / `htop` for resource monitoring
- Custom monitoring scripts

## 📈 Performance Targets
```
Metric                    Host-Based    Gateway Target
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Throughput                36 pps        10,000+ pps
Detection Latency         <1.06μs       <1.06μs (same)
CPU Usage (idle)          <1%           <5%
CPU Usage (load)          30%           <60%
Memory (detector)         148MB         <200MB
Flow Table                10K flows     100K flows
Packet Loss               0%            <0.1%
```

## 🚧 Implementation Phases

### Phase 1: XDP Modifications (2 hours)
- [ ] Add BPF map for deployment mode
- [ ] Implement mode-aware packet filtering
- [ ] Add is_local_traffic() helper
- [ ] Update userspace loader to set mode
- [ ] Compile and test basic functionality

### Phase 2: Configuration & Scripts (1 hour)
- [ ] Update sniffer.json schema
- [ ] Create setup_gateway.sh script
- [ ] Update firewall.json for gateway mode
- [ ] Update iptables_manager.cpp
- [ ] Document configuration options

### Phase 3: Testing & Validation (2 hours)
- [ ] Local VM gateway setup
- [ ] MAWI dataset replay test
- [ ] Synthetic traffic test
- [ ] Performance benchmarking
- [ ] Memory and stability testing

### Phase 4: Real Malware Testing (3 hours)
- [ ] Download CTU-13 dataset
- [ ] Prepare PCAP files
- [ ] Replay and analyze detections
- [ ] Threshold tuning with evidence
- [ ] Document findings

### Phase 5: Documentation (1 hour)
- [ ] Update README.md
- [ ] Create DEPLOYMENT_MODES.md
- [ ] Write gateway setup guide
- [ ] Performance benchmarks
- [ ] Troubleshooting guide

**Total Estimated Time:** 9 hours

## 📝 Success Criteria

✅ **Functional:**
- [ ] XDP processes ALL packets in gateway mode
- [ ] IP forwarding works correctly
- [ ] Firewall blocks malicious traffic in FORWARD chain
- [ ] Benign traffic passes through normally

✅ **Performance:**
- [ ] Throughput ≥ 10,000 pps
- [ ] Detection latency < 1.06μs (maintained)
- [ ] CPU usage < 60% under load
- [ ] No packet loss (<0.1%)

✅ **Validation:**
- [ ] MAWI dataset fully captured
- [ ] CTU-13 malware detected
- [ ] Real attacks blocked in FORWARD chain
- [ ] Zero false positives maintained

✅ **Documentation:**
- [ ] Deployment guide complete
- [ ] Configuration examples provided
- [ ] Performance benchmarks published
- [ ] Troubleshooting documented

## 🔄 Rollback Plan

If gateway mode causes issues:

1. **Immediate rollback:**
```bash
   # Switch back to host mode
   vim /vagrant/sniffer/config/sniffer.json
   # Change: "mode": "host"
   
   # Restart sniffer
   make kill-sniffer
   make run-sniffer
```

2. **Git rollback:**
```bash
   git checkout main
   git branch -D feature/gateway-mode-xdp
```

3. **System cleanup:**
```bash
   # Disable IP forwarding
   sudo sysctl -w net.ipv4.ip_forward=0
   
   # Remove NAT rules
   sudo iptables -t nat -F
   sudo iptables -F FORWARD
```

## 📚 References

- **XDP Documentation:** https://www.kernel.org/doc/html/latest/networking/af_xdp.html
- **eBPF Examples:** https://github.com/xdp-project/xdp-tutorial
- **IP Forwarding:** https://www.kernel.org/doc/Documentation/networking/ip-sysctl.txt
- **CTU-13 Dataset:** https://www.stratosphereips.org/datasets-ctu13
- **MAWI Archive:** http://mawi.wide.ad.jp/mawi/

## 🎯 Next Steps

1. **Branch Creation:**
```bash
   git checkout -b feature/gateway-mode-xdp
   git push -u origin feature/gateway-mode-xdp
```

2. **Start Implementation:**
   - Begin with Phase 1 (XDP modifications)
   - Commit frequently with descriptive messages
   - Test each change before moving to next phase

3. **Collaboration:**
   - Document discoveries in this file
   - Update plan as needed
   - Tag milestones (v0.8.0-gateway-alpha, etc.)

---

**Via Appia Quality:** Simple, robust, designed to last.

**Philosophy:** Gateway mode is not a workaround - it's the natural evolution of a host-based IDS into a network-wide protection system.
