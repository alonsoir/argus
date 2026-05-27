# 🧪 Testing Scripts

Scripts used for stability testing, stress testing, and performance validation.

## 📁 Contents

### Core Testing Scripts

**`traffic_generator_full.sh`** - Comprehensive traffic generator
- Duration: 6-10 hours
- Phases: Warm-up, normal load, stress, ransomware sim, sustained, cooldown
- Protocols: HTTP, HTTPS, DNS, ICMP, SMB, high-entropy
- Usage: `./traffic_generator_full.sh`

**`start_sniffer_test.sh`** - Start sniffer with monitoring
- Starts sniffer with nohup
- Launches background monitor (every 5 min)
- Captures logs to `/tmp/sniffer_test_output.log`
- Usage: `./start_sniffer_test.sh`

**`analyze_full_test.sh`** - Post-test analysis
- Checks process status
- Extracts metrics
- Validates system health
- Generates summary report
- Usage: `./analyze_full_test.sh`

**`final_check_v2.sh`** - Quick status check
- Real-time process status
- Memory/CPU usage
- Last statistics
- Usage: `./final_check_v2.sh`

---

## 🚀 Quick Start

### 1. Long-Running Stability Test (17h)
```bash
# Terminal 1: Start sniffer
cd /vagrant/sniffer/build
../scripts/testing/start_sniffer_test.sh

# Wait 10 seconds for startup
sleep 10

# Terminal 2: Generate traffic
cd /vagrant/sniffer/scripts/testing
./traffic_generator_full.sh

# Monitor (optional)
tail -f /tmp/sniffer_test_output.log

# After completion (17+ hours)
./analyze_full_test.sh
```

### 2. Quick Check (anytime)
```bash
cd /vagrant/sniffer/scripts/testing
./final_check_v2.sh
```

---

## 📊 Expected Results

After 17h test:
- Packets: 2M+
- Memory: Stable (~4-5 MB)
- CPU: 0-10%
- Crashes: 0
- Status: ✅ Production-ready

---

## 🔧 Customization

### Adjust Traffic Generator Duration

Edit `traffic_generator_full.sh`:
```bash
# Change phase durations
phase_warmup()    # 30 min → your time
phase_normal_load()  # 2h → your time
# etc.
```

### Adjust Monitoring Interval

Edit `start_sniffer_test.sh`:
```bash
sleep 300  # Check every 5 min
# Change to: sleep 60  # Check every 1 min
```

---

## 📝 Notes

- All scripts log to `/tmp/`
- Requires root for sniffer (eBPF)
- Traffic generator runs as regular user
- Stop anytime: `sudo pkill sniffer`

---

**Used in production validation (November 2-3, 2025)**
