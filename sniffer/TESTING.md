
### Using Provided Scripts

**All testing scripts are available in `scripts/testing/`:**
```bash
# Complete 17h test
cd scripts/testing
./start_sniffer_test.sh
./traffic_generator_full.sh
# ... wait 17h ...
./analyze_full_test.sh

# Quick status check
./final_check_v2.sh
```

See `scripts/testing/README.md` for detailed usage.
