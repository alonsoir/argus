# 🛡️ Firewall ACL Agent

Dynamic firewall rule management based on ML Defender detections.

## Features

- ⚡ **Real-time ACL updates** from ML detections
- 🕒 **Temporal rules** - Auto-expire after configurable duration
- 🚦 **Rate limiting** - Per-IP packet/connection limits
- ✅ **Whitelist/Blacklist** - Permanent allow/deny lists
- 🔄 **Graceful rollback** - Restore iptables on exit
- 📊 **Monitoring** - Stats and metrics export

## Architecture
```
┌──────────────┐
│ ml-detector  │
│   (port 5572)│
└──────┬───────┘
       │ ZMQ PUB (attacks)
       ▼
┌────────────────────────┐
│ Firewall ACL Agent     │
│                        │
│  ┌─────────────────┐  │
│  │ ZMQ Subscriber  │  │
│  └────────┬────────┘  │
│           │            │
│           ▼            │
│  ┌─────────────────┐  │
│  │ Rule Generator  │  │
│  └────────┬────────┘  │
│           │            │
│           ▼            │
│  ┌─────────────────┐  │
│  │ ACL Manager     │  │
│  │ (iptables)      │  │
│  └─────────────────┘  │
└────────────────────────┘
```

## Build
```bash
make
```

## Run
```bash
sudo make run
```

## Configuration

Edit `config/firewall.json` - see examples in config directory.

## Status

🚧 **Phase 1 Day 6-7** - Active development
