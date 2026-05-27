# ML Defender - Gateway Mode Testing Guide

**Last Updated**: December 6, 2025  
**Version**: Day 10 - Multi-VM Laboratory  
**Status**: Ready for Gateway Validation

---

## 🎯 Overview

This guide covers **gateway mode testing** for ML Defender using a multi-VM laboratory setup. This configuration validates that the dual-NIC architecture can capture **transit traffic** (packets not destined to the defender host itself) in addition to host-based IDS functionality.

### Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  ML Defender Multi-VM Laboratory                                │
│                                                                  │
│  ┌─────────────────────┐         ┌──────────────────────────┐   │
│  │  DEFENDER VM        │         │  CLIENT VM               │   │
│  │  192.168.100.1      │◄────────│  192.168.100.50          │   │
│  │                     │   LAN   │                          │   │
│  │  • eBPF/XDP Sniffer │  eth3   │  • Traffic generator     │   │
│  │  • ML Detector      │         │  • Attack simulation     │   │
│  │  • Firewall Agent   │         │  • MAWI replay           │   │
│  │  • RAG Security     │         │                          │   │
│  └─────────────────────┘         └──────────────────────────┘   │
│                                                                  │
│  Traffic Flow:                                                   │
│  Client → eth3 (defender) → ML → Firewall → RAG → LLM Response │
└──────────────────────────────────────────────────────────────────┘
```

### Key Concepts

- **Host-Based Mode** (eth1): Captures packets destined TO the defender
    - Source: Attacks from macOS host
    - XDP ifindex: 3
    - Use case: Traditional IDS

- **Gateway Mode** (eth3): Captures packets THROUGH the defender
    - Source: Traffic from client VM
    - XDP ifindex: 5
    - Use case: Network gateway / firewall appliance

---

## 📦 Quick Start (15 Minutes)

### 1. Use Multi-VM Vagrantfile

```bash
cd /vagrant

# Option A: Replace current Vagrantfile
mv Vagrantfile Vagrantfile.backup.single-vm.single-vm
cp Vagrantfile.multi-vm Vagrantfile

# Option B: Use multi-vm directly
# vagrant up --vagrantfile=Vagrantfile.multi-vm
```

### 2. Start Both VMs

```bash
# Start defender + client
vagrant up defender client

# Or sequentially
vagrant up defender
vagrant up client

# Verify status
vagrant status
```

**Expected**:
- `defender` running (8GB RAM, 6 CPUs)
- `client` running (1GB RAM, 2 CPUs)

### 3. Start Gateway Testing

**Terminal 1 - Defender**:
```bash
vagrant ssh defender
/vagrant/scripts/gateway/defender/start_gateway_test.sh
```

**Expected output**:
```
✅ Sniffer started successfully (PID: XXXX)
╔════════════════════════════════════════════════════════════╗
║  Gateway Mode ACTIVE                                       ║
╚════════════════════════════════════════════════════════════╝
```

**Terminal 2 - Client**:
```bash
vagrant ssh client
/vagrant/scripts/gateway/client/generate_traffic.sh
# Select: 5) Mixed Traffic
```

**Terminal 3 - Defender** (validation):
```bash
vagrant ssh defender
/vagrant/scripts/gateway/defender/validate_gateway.sh
```

**Success**: `✅ ✅ ✅ GATEWAY MODE VALIDATED ✅ ✅ ✅`

---

## 🛠️ Usage Modes

### Mode 1: Development (Defender Only)

**Use case**: Feature development without gateway testing

```bash
# Start only defender
vagrant up defender

# Client VM not needed
# autostart: false in Vagrantfile
```

**Features**:
- Full ML pipeline
- Host-based IDS only (eth1)
- Faster startup

### Mode 2: Gateway Testing (Both VMs)

**Use case**: Validate dual-NIC gateway mode (Day 10 objective)

```bash
# Start both VMs
vagrant up defender client

# Or enable autostart in Vagrantfile
# config.vm.define "client", autostart: true
```

**Features**:
- Dual-NIC operation
- Host-based + gateway modes simultaneously
- Real traffic validation

### Mode 3: Full Pipeline Demo

**Use case**: Complete system demonstration with RAG

```bash
# Ensure both VMs running
vagrant up

# Start full pipeline on defender
vagrant ssh defender
run-lab  # Alias for full pipeline

# Generate diverse traffic from client
vagrant ssh client
/vagrant/scripts/gateway/client/chaos_monkey.sh 5
```

**Demo flow**:
1. Traffic flows from client → defender gateway
2. ML classifies packets
3. Firewall blocks malicious IPs
4. RAG ingests events to vector DB
5. Query: "¿Qué ha ocurrido en la casa en las últimas 24h?"

---

## 📜 Scripts Reference

### Defender Scripts

Located in: `/vagrant/scripts/gateway/defender/`

#### `start_gateway_test.sh`
Starts sniffer with dual-NIC configuration.

```bash
./start_gateway_test.sh
```

**What it does**:
- Kills previous sniffer instances
- Verifies interfaces (eth1, eth3)
- Starts sniffer with gateway config
- Shows initial log output

#### `validate_gateway.sh`
Validates that gateway mode is capturing traffic.

```bash
./validate_gateway.sh
```

**Exit codes**:
- `0`: Gateway mode validated (ifindex=5 events found)
- `1`: Gateway mode not validated (no ifindex=5 events)

**Expected output**:
```
✅ ✅ ✅ GATEWAY MODE VALIDATED ✅ ✅ ✅
   X events captured on eth3 (gateway mode)
```

#### `gateway_dashboard.sh`
Real-time monitoring dashboard.

```bash
./gateway_dashboard.sh
# Press Ctrl+C to exit
```

**Displays**:
- Interface statistics (packets, events, drops)
- Sniffer CPU/memory usage
- Gateway validation status
- Live updates every 2 seconds

### Client Scripts

Located in: `/vagrant/scripts/gateway/client/`

#### `generate_traffic.sh`
Interactive traffic generator.

```bash
./generate_traffic.sh
```

**Options**:
1. HTTP/HTTPS Traffic (10 requests)
2. ICMP Traffic (25 pings)
3. Port Scan (nmap to defender)
4. Performance Test (iperf3)
5. Mixed Traffic (comprehensive)
6. Connectivity Validation
7. Chaos Monkey (stress test)

#### `chaos_monkey.sh [instances]`
High-volume stress testing (Grok4 edition).

```bash
./chaos_monkey.sh 5  # Launch 5 parallel instances
```

**Traffic mix**:
- HTTP/HTTPS to various endpoints
- ICMP pings
- DNS queries
- Continuous generation (Ctrl+C to stop)

**Use case**: Performance benchmarking, stress testing

#### `auto_validate.sh`
End-to-end automated validation.

```bash
./auto_validate.sh
```

**Phases**:
1. Connectivity validation
2. Traffic generation
3. Validation instructions for defender

---

## 🧪 Validation Workflow

### Step-by-Step Guide

**Phase 0: Pre-flight** (5 min)
```bash
# Verify both VMs are running
vagrant status

# Should show:
# defender   running (virtualbox)
# client     running (virtualbox)
```

**Phase 1: Start Sniffer** (3 min)
```bash
vagrant ssh defender
/vagrant/scripts/gateway/defender/start_gateway_test.sh

# Verify XDP attachment
sudo bpftool net show
# Expected: eth1(3) generic, eth3(5) generic
```

**Phase 2: Generate Traffic** (2 min)
```bash
vagrant ssh client
/vagrant/scripts/gateway/client/generate_traffic.sh
# Select: 5) Mixed Traffic
```

**Phase 3: Validate** (1 min)
```bash
vagrant ssh defender
/vagrant/scripts/gateway/defender/validate_gateway.sh

# Expected: ✅ ✅ ✅ GATEWAY MODE VALIDATED ✅ ✅ ✅
```

**Phase 4: Monitor** (optional)
```bash
vagrant ssh defender
/vagrant/scripts/gateway/defender/gateway_dashboard.sh
```

---

## 🔍 Troubleshooting

### Problem 1: Client cannot ping gateway

**Symptoms**:
```bash
vagrant ssh client
ping 192.168.100.1
# Request timeout
```

**Diagnosis**:
```bash
# On defender
sudo tcpdump -i eth3 -n icmp
# Do you see ICMP requests?

# On client
ip route show default
# Should show: via 192.168.100.1 dev eth1
```

**Fixes**:
```bash
# On defender
sudo ip link set eth3 up
sudo ip link set eth3 promisc on

# On client
sudo ip route add default via 192.168.100.1 dev eth1
```

### Problem 2: Gateway works but XDP doesn't capture

**Symptoms**:
```bash
# Connectivity OK
ping 192.168.100.1  # Works

# But validation fails
./validate_gateway.sh
# ❌ GATEWAY MODE NOT VALIDATED (0 events)
```

**Diagnosis**:
```bash
# Verify XDP attachment
sudo bpftool net show
# Must show: eth3(5) generic id XX

# Verify BPF map
sudo bpftool map dump name iface_configs
# key=5 must exist with mode=2, is_wan=0
```

**Fixes**:
```bash
# Restart sniffer
sudo pkill sniffer
/vagrant/scripts/gateway/defender/start_gateway_test.sh

# Check logs for errors
tail -100 /tmp/sniffer_output.log
```

### Problem 3: Wrong source IP in routing (Qwen edge case)

**Symptoms**:
```bash
# On client
ip route get 8.8.8.8 from 192.168.100.50
# Shows: src 192.168.100.1  ← WRONG (should be 192.168.56.20)
```

**Diagnosis**:
```bash
# On defender, check rp_filter
sysctl net.ipv4.conf.all.rp_filter
sysctl net.ipv4.conf.eth1.rp_filter
sysctl net.ipv4.conf.eth3.rp_filter
# All should be 0
```

**Fix**:
```bash
# On defender
sudo sysctl -w net.ipv4.conf.all.rp_filter=0
sudo sysctl -w net.ipv4.conf.eth1.rp_filter=0
sudo sysctl -w net.ipv4.conf.eth3.rp_filter=0
```

### Problem 4: No traffic in logs

**Symptoms**:
```bash
tail -f /tmp/sniffer_output.log
# No events appearing
```

**Diagnosis**:
```bash
# Check if sniffer is running
ps aux | grep sniffer

# Check XDP attachment
sudo bpftool net show

# Monitor raw packets on eth3
sudo tcpdump -i eth3 -c 10
```

**Fix**:
```bash
# Recompile sniffer if needed
cd /vagrant/sniffer
make clean && make

# Restart with verbose logging
cd build
sudo ./sniffer -c /vagrant/scripts/gateway/shared/config_gateway.json -v
```

---

## 📊 Performance Benchmarks

### Metrics to Collect

| Metric | Target | Method |
|--------|--------|--------|
| Gateway events (ifindex=5) | >1,000 | `validate_gateway.sh` |
| Throughput | >100 Mbps | `iperf3 -c 192.168.100.1` |
| Latency p50 | <100 μs | Parse sniffer logs |
| Latency p95 | <200 μs | Parse sniffer logs |
| Latency p99 | <500 μs | Parse sniffer logs |
| CPU usage | <50% | `gateway_dashboard.sh` |
| Kernel drops | 0 | `/sys/class/net/eth3/statistics/rx_dropped` |

### Benchmark Commands

```bash
# Throughput test (requires iperf3 server on defender)
vagrant ssh defender
iperf3 -s &

vagrant ssh client
iperf3 -c 192.168.100.1 -t 30

# Stress test with chaos monkey
vagrant ssh client
/vagrant/scripts/gateway/client/chaos_monkey.sh 5
# Run for 5 minutes, monitor dashboard

# Collect metrics
vagrant ssh defender
/vagrant/scripts/gateway/defender/gateway_dashboard.sh
```

---

## 📝 Configuration Files

### Vagrantfile.multi-vm

**Location**: `/vagrant/Vagrantfile.multi-vm`

**Key settings**:
- `defender`: 8GB RAM, 6 CPUs, full ML pipeline
- `client`: 1GB RAM, 2 CPUs, traffic generator only
- `autostart: false` for client (enable for testing)

**Networks**:
- eth1 (defender): 192.168.56.20 (host-only)
- eth3 (defender): 192.168.100.1 (internal network "ml_defender_gateway_lan")
- eth1 (client): 192.168.100.50 (same internal network)

### config_gateway.json

**Location**: `/vagrant/scripts/gateway/shared/config_gateway.json`

**Key parameters**:
```json
{
  "mode": "dual_nic",
  "interfaces": [
    {
      "name": "eth1",
      "mode": "host_based",
      "wan_facing": true
    },
    {
      "name": "eth3",
      "mode": "gateway",
      "wan_facing": false
    }
  ]
}
```

---

## 🎓 Best Practices

### Development Workflow

1. **Single VM for development**
    - Use `vagrant up defender` only
    - Faster iteration cycles
    - Full pipeline available

2. **Multi-VM for gateway testing**
    - Use `vagrant up defender client`
    - Validate gateway mode periodically
    - Before releases/milestones

3. **Scripts for automation**
    - Don't start components manually
    - Use provided scripts
    - Consistent, repeatable results

### Testing Strategy

**Unit Tests** → **Integration Tests** → **Gateway Validation** → **Production**

- Unit: Mock/stubs, fast feedback
- Integration: Single VM, host-based mode
- Gateway: Multi-VM, transit traffic
- Production: Physical hardware, native XDP

### Documentation

- Log all validation attempts
- Screenshot dashboard with ifindex=5 events
- Document performance metrics
- Share findings in postmortems

---

## 🚀 Next Steps

### After Successful Validation

**Day 10 Complete**: ✅ Gateway mode validated

**Next objectives**:
1. MAWI dataset processing in gateway mode
2. Performance benchmarking (chaos monkey)
3. Comparative analysis (host-based vs gateway)
4. Integration with full ML pipeline
5. RAG ingestion of gateway events
6. Natural language queries over gateway traffic

### Future Enhancements

- **Multiple clients**: Simulate multi-host LAN
- **Attack scenarios**: Coordinated attack simulation
- **Performance tuning**: XDP native on physical hardware
- **Monitoring**: Grafana dashboards for metrics
- **Automation**: CI/CD integration for gateway testing

---

## 🙏 Credits

**Multi-Agent Collaboration**:
- **Grok4** (xAI): XDP Generic expertise, chaos_monkey.sh, is_wan validation
- **DeepSeek** (DeepSeek-V3): Vagrantfile automation, metrics template
- **Qwen** (Alibaba): rp_filter edge case, routing verification
- **Claude** (Anthropic): Implementation, integration, synthesis

**Philosophy**: Via Appia Quality - Built to last, documented honestly, learned systematically

---

**Last Updated**: December 6, 2025  
**Version**: 1.0 - Day 10 Multi-VM Gateway Laboratory  
**Status**: Ready for Validation 🚀