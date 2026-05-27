# PCAP Replay Testing - Phase 2 Validation

> **Status:** Documentation complete, implementation pending Phase 2
> **Priority:** After Phase 1 completion (watcher, vector DB, hardening)
> **Purpose:** Validate ML models against real malware traffic

---

## Overview

PCAP replay allows testing the ML Defender pipeline with **real malware traffic** in a safe, controlled, reproducible environment. This is the gold standard for IDS validation.

---

## Security First - Hardening Strategy

**Critical:** The VM must be completely isolated BEFORE any malicious traffic replay.

### 1. VM Hardening (Automatic in Vagrantfile)

```ruby
# Add to Vagrantfile provision (before any PCAP work)
config.vm.provision "shell", name: "pcap-hardening", inline: <<-SHELL
  # 1. Block all outbound traffic except allowed
  iptables -P OUTPUT DROP
  iptables -P FORWARD DROP
  
  # 2. Allow only internal host↔VM communication
  iptables -A OUTPUT -d 10.0.2.2 -j ACCEPT      # Host (NAT)
  iptables -A OUTPUT -d 192.168.56.1 -j ACCEPT  # Host (private)
  iptables -A OUTPUT -o lo -j ACCEPT            # Loopback
  
  # 3. Block DNS to external (no data exfiltration)
  iptables -A OUTPUT -p udp --dport 53 ! -d 10.0.2.2 -j DROP
  iptables -A OUTPUT -p tcp --dport 53 ! -d 10.0.2.2 -j DROP
  
  # 4. Log rejected packets (limited)
  iptables -A OUTPUT -m limit --limit 5/min -j LOG --log-prefix "BLOCKED: "
  
  # 5. Disable IP forwarding
  echo 0 > /proc/sys/net/ipv4/ip_forward
  
  echo "✅ VM hardened for PCAP replay"
SHELL
```

### 2. Mount PCAPs as Read-Only

```ruby
# In Vagrantfile
config.vm.synced_folder "./pcaps", "/opt/pcaps", 
  type: "virtualbox",
  mount_options: ["ro"]  # Read-only!
```

**Why this matters:**
- VM cannot modify or exfiltrate PCAPs
- Malware cannot write back to host
- No accidental corruption of test data

---

## Methodology - Complete Workflow

### Phase 1: Obtain Real Malware PCAPs (On Host)

**Trusted Sources:**

1. **Malware-Traffic-Analysis.net** (BEST)
    - Ransomware: Locky, WannaCry, Ryuk, Conti
    - Banking Trojans: Emotet, Trickbot, Dridex
    - Exploit Kits: RIG, Magnitude
    - URL: https://www.malware-traffic-analysis.net/

2. **StratosphereIPS - CTU-13 Dataset**
    - 13 botnet scenarios (Neris, Rbot, Virut, etc.)
    - Well-labeled, peer-reviewed
    - URL: https://www.stratosphereips.org/datasets-overview

3. **CAIDA DDoS Attack 2007**
    - Real DDoS against DNS root servers
    - URL: https://www.caida.org/catalog/datasets/ddos-20070804_dataset/

4. **SecRepo.com**
    - Various attack types
    - URL: http://www.secrepo.com/

**Download on host (macOS):**
```bash
cd ~/Code/argus/pcaps
wget https://www.malware-traffic-analysis.net/.../attack.pcap.zip
unzip -P infected attack.pcap.zip
```

### Phase 2: Prepare PCAPs for Replay

**Why rewrite IPs:**
- Original PCAPs have arbitrary source/dest IPs
- Need to map to VM's network (10.0.2.0/24, 192.168.100.0/24)
- Firewall can then block the mapped attacker IP

**Install tools (in VM):**
```bash
sudo apt-get install -y tcpreplay tcpdump wireshark-common
```

**Rewrite IPs:**
```bash
# Option A: Simple rewrite (all IPs to VM subnet)
tcprewrite \
  --infile=/opt/pcaps/original.pcap \
  --outfile=/tmp/ready.pcap \
  --pnat=0.0.0.0/0:192.168.100.0/24 \
  --fixcsum

# Option B: Specific attacker IP (for blacklist testing)
tcprewrite \
  --infile=/opt/pcaps/original.pcap \
  --outfile=/tmp/ready.pcap \
  --srcipmap=0.0.0.0/0:192.168.100.50/32 \
  --dstipmap=0.0.0.0/0:10.0.2.15/32 \
  --fixcsum

# Verify result
tcpdump -nr /tmp/ready.pcap -c 20
```

### Phase 3: Execute Replay

**Start ML Defender pipeline:**
```bash
cd /vagrant
make run-lab-dev
```

**In another terminal, start monitoring:**
```bash
# Terminal 2: Watch detector stats
watch -n 1 'grep "attacks=" /vagrant/logs/lab/detector.log | tail -1'

# Terminal 3: Watch IPSet blacklist
watch -n 1 'sudo ipset list ml_defender_blacklist_test'

# Terminal 4: Monitor all logs
tail -f /vagrant/logs/lab/*.log
```

**Replay the PCAP:**
```bash
# Basic replay (original speed)
sudo tcpreplay --intf1=eth0 /tmp/ready.pcap

# Faster (2x speed, for stress testing)
sudo tcpreplay --intf1=eth0 --multiplier=2 /tmp/ready.pcap

# Controlled rate (100 Mbps)
sudo tcpreplay --intf1=eth0 --mbps=100 /tmp/ready.pcap

# Controlled PPS (1000 packets/sec)
sudo tcpreplay --intf1=eth0 --pps=1000 /tmp/ready.pcap

# Loop 10 times (stress test)
sudo tcpreplay --intf1=eth0 --loop=10 /tmp/ready.pcap

# With stats every second
sudo tcpreplay --intf1=eth0 --stats=1 /tmp/ready.pcap
```

**Why control speed:**
- Too fast → artificial volume spikes (false positives)
- Too slow → takes forever
- Realistic rate (100-1000 pps) → best for model validation

### Phase 4: Validate Results

**Check if models detected attacks:**
```bash
# 1. Check attack counter
grep "attacks=" /vagrant/logs/lab/detector.log | tail -5

# 2. Check specific detections
grep -E "DDOS|RANSOMWARE|SUSPICIOUS" /vagrant/logs/lab/detector.log

# 3. Check firewall blocked IPs
sudo ipset list ml_defender_blacklist_test

# 4. Check IPTables counters
sudo iptables -L INPUT -n -v --line-numbers | grep ml_defender

# 5. Get final stats
echo "=== DETECTOR ==="
grep "Stats:" /vagrant/logs/lab/detector.log | tail -1

echo "=== FIREWALL ==="
grep "METRICS" /vagrant/logs/lab/firewall.log | tail -1

echo "=== SNIFFER ==="
grep "Paquetes procesados" /vagrant/logs/lab/sniffer.log | tail -1
```

---

## Automated Testing Script

**Location:** `/vagrant/scripts/testing/pcap_replay_test.sh`

```bash
#!/bin/bash
set -euo pipefail

PCAP_DIR="/opt/pcaps"
PCAP_FILE="${1:-}"
SPEED="${2:-1}"

if [[ -z "$PCAP_FILE" ]]; then
    echo "Usage: $0 <pcap_file> [speed_multiplier]"
    echo "Example: $0 malware.pcap 2"
    exit 1
fi

if [[ ! -f "$PCAP_DIR/$PCAP_FILE" ]]; then
    echo "❌ Error: PCAP not found: $PCAP_DIR/$PCAP_FILE"
    exit 1
fi

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  ML Defender - PCAP Replay Test                           ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "📂 PCAP: $PCAP_FILE"
echo "⚡ Speed: ${SPEED}x"
echo "🔒 Hardened: $(iptables -L OUTPUT -n | grep -c DROP || echo 'NO')"
echo ""

# Baseline stats
BASELINE_ATTACKS=$(grep "attacks=" /vagrant/logs/lab/detector.log 2>/dev/null | tail -1 | grep -oP 'attacks=\K\d+' || echo 0)
BASELINE_PROCESSED=$(grep "processed=" /vagrant/logs/lab/detector.log 2>/dev/null | tail -1 | grep -oP 'processed=\K\d+' || echo 0)

echo "📊 Baseline: attacks=$BASELINE_ATTACKS, processed=$BASELINE_PROCESSED"
echo ""
echo "⏳ Starting replay in 3 seconds..."
sleep 3

# Execute replay
echo "🚀 Replaying PCAP..."
sudo tcpreplay \
    --intf1=eth0 \
    --multiplier="$SPEED" \
    --stats=1 \
    "$PCAP_DIR/$PCAP_FILE"

echo ""
echo "⏳ Waiting 5 seconds for ML processing..."
sleep 5

# Final stats
FINAL_ATTACKS=$(grep "attacks=" /vagrant/logs/lab/detector.log 2>/dev/null | tail -1 | grep -oP 'attacks=\K\d+' || echo 0)
FINAL_PROCESSED=$(grep "processed=" /vagrant/logs/lab/detector.log 2>/dev/null | tail -1 | grep -oP 'processed=\K\d+' || echo 0)

NEW_ATTACKS=$((FINAL_ATTACKS - BASELINE_ATTACKS))
NEW_PROCESSED=$((FINAL_PROCESSED - BASELINE_PROCESSED))

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  RESULTS                                                   ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo "📊 Events processed: $NEW_PROCESSED"
echo "🚨 Attacks detected: $NEW_ATTACKS"
echo ""

if [[ $NEW_ATTACKS -gt 0 ]]; then
    echo "🎯 ATTACKS DETECTED! Checking blocked IPs..."
    echo ""
    sudo ipset list ml_defender_blacklist_test
    echo ""
    echo "✅ Test PASSED - System detected and blocked attacks!"
else
    echo "ℹ️  No attacks detected."
    echo ""
    echo "Possible reasons:"
    echo "  1. PCAP doesn't match model training patterns"
    echo "  2. Models correctly classified as benign (no false positive)"
    echo "  3. Thresholds too high (check sniffer.json)"
    echo "  4. Feature extraction mismatch"
fi

echo ""
echo "💡 For debugging:"
echo "   tail -50 /vagrant/logs/lab/detector.log"
echo "   grep 'level1_confidence' /vagrant/logs/lab/detector.log"
echo ""
```

**Usage:**
```bash
chmod +x /vagrant/scripts/testing/pcap_replay_test.sh
/vagrant/scripts/testing/pcap_replay_test.sh ransomware.pcap 1
```

---

## Interpretation Guide

### Expected Outcomes

**If attacks detected (attacks > 0):**
✅ Models are working correctly
✅ Firewall blocked attacker IPs
✅ IPSet shows blocked entries
✅ IPTables DROP counter increased

**If NO attacks detected (attacks = 0):**

Could mean:
1. **Models too strict** (good for production, bad for testing)
    - Solution: Lower thresholds in `sniffer.json`
    - Try: DDoS 0.70, Ransomware 0.75 (from 0.85, 0.90)

2. **PCAP doesn't match training data**
    - Models trained on specific patterns
    - PCAP may use different attack vector
    - Solution: Try different PCAP source

3. **Feature extraction issue**
    - Check sniffer logs for feature values
    - Compare with training data ranges
    - May need feature normalization

4. **Models are actually correct**
    - Some "malware PCAPs" are just C2 beacons
    - Low-volume, low-impact traffic
    - Not every malware PCAP triggers DDoS/Ransomware patterns

### Debugging Commands

```bash
# See confidence scores
grep "confidence" /vagrant/logs/lab/detector.log | tail -20

# Check feature values
tail -100 /vagrant/logs/lab/sniffer.log | grep "Features:"

# See what was classified
grep "threat_category" /vagrant/logs/lab/detector.log | tail -20

# IPTables dropped packets
sudo iptables -L INPUT -n -v | grep DROP
```

---

## Safety Checklist

Before ANY PCAP replay:

- [ ] VM is hardened (iptables OUTPUT DROP in place)
- [ ] PCAPs mounted as read-only
- [ ] No internet access from VM (test: `ping 8.8.8.8` should fail)
- [ ] Firewall logs are capturing events
- [ ] Backup of current config exists
- [ ] Know how to kill the lab: `make kill-lab`

---

## ChatGPT Insights Integration

**Key points from ChatGPT discussion:**

1. ✅ **Harden FIRST, replay SECOND** - Never reverse this order
2. ✅ **Download on host** - VM should never touch internet for PCAPs
3. ✅ **Read-only mount** - Prevents malware from modifying test data
4. ✅ **Controlled replay rate** - Avoid artificial volume spikes
5. ✅ **This is the industry standard** - Used by Blue Teams, IDS vendors, CI/CD pipelines

**What NOT to do:**
- ❌ Don't run actual malware executables
- ❌ Don't give VM internet access during replay
- ❌ Don't replay without hardening
- ❌ Don't trust "cleaned" PCAPs without verification

---

## Recommended Testing Sequence

### Phase 2.1: Initial Validation (Week 1)
1. Single Locky ransomware PCAP (well-documented)
2. Single Emotet banking trojan PCAP
3. Verify models detect both

### Phase 2.2: Comprehensive Testing (Week 2)
4. CTU-13 botnet scenarios (all 13)
5. Various DDoS types (SYN flood, UDP flood, etc.)
6. Mixed traffic (benign + malicious)

### Phase 2.3: Stress Testing (Week 3)
7. Loop replay (10x)
8. High-speed replay (10x multiplier)
9. Concurrent attacks
10. Long-running stability (24h with replays)

---

## Success Metrics

**Model Validation:**
- Detection Rate > 90% on known malware
- False Positive Rate < 5% on benign traffic
- Latency < 100μs maintained under load

**System Validation:**
- No crashes during replay
- Memory stable (<150MB)
- All blocked IPs in blacklist
- IPTables counters match detections

---

## Future Enhancements

1. **Automated PCAP library** - Download/catalog common attacks
2. **Confidence threshold tuning** - Automatically find optimal values
3. **A/B testing** - Compare model versions
4. **Continuous validation** - CI/CD integration
5. **Synthetic PCAP generation** - Create custom attack scenarios

---

## References

- Malware-Traffic-Analysis.net - Brad Duncan's excellent resources
- StratosphereIPS - Academic-quality datasets
- tcpreplay documentation - https://tcpreplay.appneta.com/
- ChatGPT validation discussion (Nov 28, 2025)

---

**Status:** Ready to implement in Phase 2
**Estimated effort:** 2-3 days (after watcher system complete)
**Priority:** Medium (validation, not blocker)

---

*Via Appia Quality: Test with real threats, not assumptions.*