# DAY 11 QUICK REFERENCE CARD
**ML Defender v3.3.2 | Dual-NIC Gateway Mode Validation**

---

## 🎯 VALIDATION RESULTS (TL;DR)

```
✅ 791,615 packets replayed at 5 Mbps
✅ 815,499 packets captured (103% rate)
✅ 1,683,126 ML inferences (0 errors)
✅ 22.5 min continuous operation (0 crashes)
✅ Gateway mode: 809,846 events on eth2 (99.3%)
```

---

## 🔧 NETWORK CONFIGURATION

```
Defender VM:
  eth0: 10.0.2.15 (NAT)
  eth1: 192.168.56.20 (WAN, ifindex=3, host-based IDS)
  eth2: 192.168.100.1 (LAN, ifindex=4, gateway mode) ✅

Client VM:
  eth0: 10.0.2.15 (NAT)
  eth1: 192.168.100.50 (Gateway: 192.168.100.1)
```

---

## 📊 KEY METRICS

```
Dataset:         CTU-13 bigFlows.pcap
Size:            355 MB, 791,615 packets
Duration:        568.66 seconds (9.5 min)
Replay Rate:     4.99 Mbps, 1,392 pps
Capture Rate:    103% (815,499 captured)
ML Inferences:   1,683,126 events
Throughput:      617 events/sec sustained
Errors:          0 (deser:0, feat:0, inf:0)
Packet Loss:     0%
Uptime:          100%
```

---

## 🚀 REPRODUCTION COMMANDS

### Terminal 1: ML Detector
```bash
vagrant ssh defender
cd /vagrant/ml-detector/build
./ml-detector -c ../config/ml_detector_config.json
# Wait for: "📥 ZMQ Handler loop started"
```

### Terminal 2: Sniffer
```bash
vagrant ssh defender
cd /vagrant/sniffer/build
sudo ./sniffer -c ../config/sniffer.json 2>&1 | tee /vagrant/logs/lab/sniffer_live.log
# Verify: "✅ Configured eth2 (ifindex=4, mode=gateway)"
```

### Terminal 3: Replay
```bash
# Baseline test (1 Mbps)
vagrant ssh client -c "sudo tcpreplay -i eth1 --mbps=1 /vagrant/datasets/ctu13/smallFlows.pcap"

# Stress test (5 Mbps)
vagrant ssh client -c "sudo tcpreplay -i eth1 --mbps=5 /vagrant/datasets/ctu13/bigFlows.pcap"
```

### Terminal 4: Monitor
```bash
# Sniffer stats
tail -f /vagrant/logs/lab/sniffer_live.log | grep -E "ESTADÍSTICAS|DUAL-NIC"

# ML Detector stats
vagrant ssh defender -c "tail -f /vagrant/ml-detector/build/logs/cpp_ml_detector_tricapa_v1.log | grep 'Stats:'"
```

---

## 🔍 VERIFICATION COMMANDS

### Check Network Config
```bash
# From Defender VM
ip addr show | grep -E "eth[0-9]|inet "
ip route show

# Expected output:
# eth1: 192.168.56.20
# eth2: 192.168.100.1
```

### Verify Interface Config
```bash
# Check sniffer.json
cat /vagrant/sniffer/config/sniffer.json | grep -A 5 '"gateway_interface"'

# Should show:
# "name": "eth2"
```

### Check Capture Stats
```bash
# Sniffer statistics
grep -A 5 "ESTADÍSTICAS" /vagrant/logs/lab/sniffer_live.log | tail -20

# Gateway mode events
grep "ifindex=4 mode=2" /vagrant/logs/lab/sniffer_live.log | wc -l

# ML Detector stats
grep "Stats:" /vagrant/ml-detector/build/logs/cpp_ml_detector_tricapa_v1.log | tail -10
```

---

## 🐛 TROUBLESHOOTING

### Issue: Interface not found
```bash
# Check interface mapping
ip link show | grep -E "^[0-9]+: eth"

# Verify sniffer.json matches actual interfaces
grep '"name": "eth' /vagrant/sniffer/config/sniffer.json
```

### Issue: No events captured
```bash
# Check XDP attachment
ip link show eth2 | grep xdpgeneric

# Verify ring buffer
sudo bpftool prog show

# Check sniffer logs
tail -100 /vagrant/logs/lab/sniffer_live.log | grep -E "ERROR|WARNING"
```

### Issue: ML Detector not receiving
```bash
# Test ZMQ connectivity
vagrant ssh defender
cd /vagrant/ml-detector/build
./ml-detector -c ../config/ml_detector_config.json

# Should show: "📥 ZMQ Handler loop started"
# If not, check: netstat -tuln | grep 5571
```

---

## 📈 PERFORMANCE EXPECTATIONS

### XDP Generic (VirtualBox)
```
Throughput:      ~5 Mbps, 1,400 pps
Capture Rate:    100-110% (bidirectional)
Event Rate:      500-700 events/sec
Latency:         <1 ms inference
```

### Flow Table Limits
```
Default:         10,000 flows
bigFlows.pcap:   40,467 flows
Recommendation:  50,000 flows for large datasets
```

---

## 🔧 CONFIGURATION FILES

### Key Files Modified (Day 11)
```
Vagrantfile:                    eth3 → eth2, removed Grok optimizations
sniffer/config/sniffer.json:    v3.3.1 → v3.3.2, gateway_interface="eth2"
```

### Important Paths
```
Sniffer binary:     /vagrant/sniffer/build/sniffer
ML Detector binary: /vagrant/ml-detector/build/ml-detector
Sniffer logs:       /vagrant/logs/lab/sniffer_live.log
ML Detector logs:   /vagrant/ml-detector/build/logs/cpp_ml_detector_tricapa_v1.log
Datasets:           /vagrant/datasets/ctu13/*.pcap
```

---

## ✅ VALIDATION CHECKLIST

```
□ Network config correct (eth1=WAN, eth2=Gateway)
□ Sniffer starts without errors
□ ML Detector connects to ZMQ
□ XDP attached to both interfaces
□ Gateway mode shows ifindex=4
□ Capture rate >90%
□ No packet loss
□ Zero processing errors
□ No crashes during stress test
□ Statistics match expectations
```

---

## 📝 COMMON GREP PATTERNS

```bash
# Sniffer statistics
grep -A 5 "ESTADÍSTICAS" logs/lab/sniffer_live.log

# Gateway mode events
grep "ifindex=4 mode=2" logs/lab/sniffer_live.log

# ML Detector stats
grep "Stats:" logs/ml-detector/*.log

# Interface config
grep "eth[0-9]" logs/lab/sniffer_live.log | grep "ifindex"

# Errors only
grep -E "ERROR|CRITICAL" logs/lab/sniffer_live.log

# Warnings only
grep "WARNING" logs/lab/sniffer_live.log
```

---

## 🎯 SUCCESS CRITERIA (Quick Check)

```
✅ Capture Rate:     >80% (achieved: 103%)
✅ Gateway Events:   >50% (achieved: 99.3%)
✅ Processing Rate:  >500 evt/s (achieved: 617 evt/s)
✅ Errors:           <1% (achieved: 0%)
✅ Uptime:           >10 min (achieved: 22.5 min)
✅ Packet Loss:      <5% (achieved: 0%)
```

---

## 🚀 DEPLOYMENT READINESS

| Component | Status |
|-----------|--------|
| Infrastructure | ✅ Production-ready |
| Performance | ✅ 5 Mbps validated |
| Stability | ✅ 22.5 min uptime |
| Documentation | ✅ Complete |
| Testing | ✅ Stress tested |

**Next:** CTU-13 malware detection experiments 🔬

---

**Quick Help:**
- Full report: `VALIDATION_DAY11.md`
- Journal entry: `DAY11_JOURNAL_ENTRY.md`
- Executive summary: `DAY11_EXECUTIVE_SUMMARY.md`

**Generated:** 2025-12-07 | ML Defender v3.3.2