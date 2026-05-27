# Dual-NIC Testing Plan - Day 8

**Date:** 2025-12-02  
**Status:** 🟡 Ready to Test  
**Goal:** Validate dual-NIC deployment with real traffic

---

## ⚠️ Configuration Issues Identified (2025-12-01)

### Current Problems

1. **Vagrantfile:** Only has 1 NIC configured
    - eth0: 192.168.56.20 (host-only adapter)
    - **Missing:** eth1 (internal network for gateway testing)

2. **sniffer.json:** Incorrect deployment config
    - Currently: `eth1` in `"dual"` mode (nonsense - single interface can't be dual)
    - Should be: `eth0` (host-based) + `eth1` (gateway)

3. **Testing Limitations:**
    - Cannot test gateway mode without second NIC
    - PCAP replay to 192.168.56.20 doesn't work (XDP only captures traffic destined to host)

---

## 🛠️ Required Changes

### 1. Vagrantfile Modifications

**Add Second NIC:**
```ruby
Vagrant.configure("2") do |config|
  config.vm.box = "ubuntu/jammy64"
  
  # Existing NIC (WAN/Host-Only)
  config.vm.network "private_network", ip: "192.168.56.20"
  
  # NEW: Internal network for gateway testing (LAN)
  config.vm.network "private_network", 
    ip: "192.168.100.1",
    virtualbox__intnet: "ml_defender_lan"
  
  config.vm.provider "virtualbox" do |vb|
    vb.memory = "8192"
    vb.cpus = 8
    
    # Enable promiscuous mode for gateway capture
    vb.customize ["modifyvm", :id, "--nicpromisc2", "allow-all"]
    vb.customize ["modifyvm", :id, "--nicpromisc3", "allow-all"]
  end
end
```

**After Change:**
- eth0: Loopback/NAT (default)
- eth1: 192.168.56.20 (WAN-facing, OSX bridge100)
- eth2: 192.168.100.1 (LAN-facing, internal network)

### 2. sniffer.json Configuration

**Correct Dual-Mode Config:**
```json
{
  "deployment": {
    "mode": "dual",
    "host_interface": "eth1",
    "gateway_interface": "eth2",
    "network_settings": {
      "enable_ip_forwarding": true,
      "enable_nat": false,
      "lan_subnet": "192.168.100.0/24"
    },
    "performance": {
      "expected_throughput_gbps": 1.0,
      "max_packets_per_second": 1000000
    }
  },
  "profiles": {
    "dual_nic": {
      "worker_threads": 8,
      "cpu_affinity_enabled": false,
      "ring_buffer_pages": 512
    }
  }
}
```

---

## 🧪 Testing Strategy

### Test 1: Host-Based Mode (eth1)

**Scenario:** Direct attacks from OSX → VM
```bash
# From OSX:
sudo nmap -sS -p 1-1000 192.168.56.20
sudo hping3 -S -p 80 --flood -c 5000 192.168.56.20

# Expected:
# - ML Defender captures on eth1
# - interface_mode = 1 (host-based)
# - is_wan_facing = true
# - Detections logged
```

### Test 2: Gateway Mode (eth2) - Option A: Second VM

**Scenario:** Create second VM behind ML Defender gateway
```ruby
# In Vagrantfile, add:
config.vm.define "victim" do |victim|
  victim.vm.box = "ubuntu/jammy64"
  victim.vm.network "private_network",
    ip: "192.168.100.10",
    virtualbox__intnet: "ml_defender_lan"
  victim.vm.provider "virtualbox" do |vb|
    vb.memory = "2048"
    vb.cpus = 2
  end
end
```

**Test:**
```bash
# From OSX → Attack victim through gateway
# ML Defender (192.168.100.1) acts as router
# Traffic flows: OSX → eth1 → ML Defender → eth2 → Victim

# Configure routing on victim:
ip route add default via 192.168.100.1

# Attack from OSX:
nmap -sS 192.168.100.10

# Expected:
# - ML Defender captures on eth2
# - interface_mode = 2 (gateway)
# - is_wan_facing = false
```

### Test 3: PCAP Replay via eth2

**Scenario:** Use tcpreplay to inject MAWI traffic into LAN
```bash
# On ML Defender VM:
cd /vagrant/datasets/mawi

# Replay traffic to internal network
sudo tcpreplay -i eth2 --topspeed 202501010000.pcap

# Expected:
# - ML Defender captures on eth2
# - interface_mode = 2 (gateway)
# - High packet rate testing
```

### Test 4: Simultaneous Dual-Mode

**Scenario:** Attack VM on eth1 WHILE replaying traffic on eth2
```bash
# Terminal 1 (OSX):
sudo hping3 -S -p 22 --flood 192.168.56.20

# Terminal 2 (VM):
sudo tcpreplay -i eth2 --topspeed mawi.pcap

# Expected:
# - Both interfaces capture simultaneously
# - Events tagged with correct interface_mode
# - Zero packet drops
# - CPU usage monitored
```

---

## 📊 Validation Checklist

### Configuration
- [ ] Vagrantfile has 2 private networks
- [ ] sniffer.json deployment.mode = "dual"
- [ ] eth1 configured as host_interface
- [ ] eth2 configured as gateway_interface
- [ ] Promiscuous mode enabled on both NICs

### Pipeline Startup
- [ ] Sniffer loads interface_configs map
- [ ] DualNICManager logs show both interfaces
- [ ] No "interface_configs map not found" warnings
- [ ] XDP programs attached to eth1 and eth2

### Host-Based Mode (eth1)
- [ ] OSX → VM attacks captured
- [ ] interface_mode = 1 in events
- [ ] is_wan_facing = true
- [ ] source_interface = "eth1"
- [ ] Detections trigger correctly

### Gateway Mode (eth2)
- [ ] Transit traffic captured (OSX → Victim or PCAP replay)
- [ ] interface_mode = 2 in events
- [ ] is_wan_facing = false
- [ ] source_interface = "eth2"
- [ ] Detections trigger on replayed attacks

### Performance
- [ ] Zero ring buffer drops
- [ ] CPU usage < 30%
- [ ] Detection latency < 10 μs
- [ ] No crashes after 1+ hour stress test

### Metadata Validation
- [ ] Protobuf events contain all 4 new fields
- [ ] Detector logs show interface context
- [ ] Firewall receives interface metadata
- [ ] End-to-end metadata flow verified

---

## 🐛 Expected Issues & Mitigations

### Issue 1: eth2 doesn't capture transit traffic
**Cause:** IP forwarding disabled or routing table issues  
**Mitigation:**
```bash
sudo sysctl -w net.ipv4.ip_forward=1
ip route show  # Verify routing table
```

### Issue 2: PCAP replay packets dropped
**Cause:** tcpreplay too fast, ring buffer overflow  
**Mitigation:**
```bash
# Use --mbps to throttle:
sudo tcpreplay -i eth2 --mbps 100 mawi.pcap
```

### Issue 3: Dual mode shows only one interface
**Cause:** XDP program not attaching to both interfaces  
**Mitigation:**
```bash
# Check XDP attachment:
ip link show eth1 | grep xdp
ip link show eth2 | grep xdp

# Check BPF map population:
sudo bpftool map dump name interface_configs
```

---

## 📈 Success Criteria

- ✅ Both interfaces capture traffic simultaneously
- ✅ interface_mode correctly distinguishes host vs gateway
- ✅ PCAP replay works through eth2
- ✅ Zero packet drops under 100K pps load
- ✅ Metadata visible in detector logs
- ✅ System stable for 2+ hours continuous testing

---

## 📝 Next Steps After Testing

1. **Document Results** → Update README with benchmark data
2. **Performance Tuning** → If drops occur, tune worker_threads
3. **Academic Paper** → Draft methodology section with test results
4. **Production Hardening** → Add systemd services, log rotation
5. **Real Malware Testing** → PCAP datasets from Stratosphere, CICIDS

---

**Prepared:** 2025-12-01  
**Tester:** Alonso  
**Expected Duration:** 2-3 hours  
**Status:** Ready to begin 🚀