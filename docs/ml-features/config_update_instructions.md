# Configuration Updates for Ransomware Detection

## Files to Update

### 1. sniffer/config/sniffer.json

**Change line 164-168 from:**
```json
"ransomware_feature_group": {
  "count": 83,
  "reference": "config/features/ransomware_83_features.json",
  "description": "Ransomware detection features including connection patterns, data transfer analysis"
},
```

**To:**
```json
"ransomware_feature_group": {
  "count": 20,
  "reference": "config/features/ransomware_20_features.json",
  "description": "Ransomware detection features (20 critical features optimized for RPi)"
},
```

---

### 2. ml-detector/config/ml_detector_config.json

**Change lines 165-173 (level2.ransomware section) from:**
```json
"ransomware": {
  "enabled": false,
  "name": "ransomware_detector",
  "model_file": "level2/ransomware_rf.onnx",
  "features_count": 82,
  "model_type": "RandomForest",
  "description": "Ransomware detection - Random Forest (82 features)",
  "requires_scaling": false,
  "timeout_ms": 10
}
```

**To:**
```json
"ransomware": {
  "enabled": false,
  "name": "ransomware_detector",
  "model_file": "level2/ransomware_rf_20.onnx",
  "features_count": 20,
  "model_type": "RandomForest",
  "description": "Ransomware detection - RandomForest (20 features, RPi optimized)",
  "requires_scaling": false,
  "timeout_ms": 10
}
```

**Note:** Keep `enabled: false` until the model is trained and ready.

---

## Commands to Apply Changes

```bash
cd ~/CLionProjects/argus

# 1. Copy ransomware features JSON to sniffer
mkdir -p sniffer/config/features/
cp ransomware_20_features.json sniffer/config/features/

# 2. Update sniffer.json manually (use your editor)
# Or use sed:
sed -i 's/"count": 83/"count": 20/g' sniffer/config/sniffer.json
sed -i 's/ransomware_83_features.json/ransomware_20_features.json/g' sniffer/config/sniffer.json
sed -i 's/Ransomware detection features including connection patterns, data transfer analysis/Ransomware detection features (20 critical features optimized for RPi)/g' sniffer/config/sniffer.json

# 3. Update ml_detector_config.json manually (use your editor)
# Or use sed:
sed -i 's/"features_count": 82/"features_count": 20/g' ml-detector/config/ml_detector_config.json
sed -i 's/ransomware_rf.onnx/ransomware_rf_20.onnx/g' ml-detector/config/ml_detector_config.json
sed -i 's/Ransomware detection - Random Forest (82 features)/Ransomware detection - RandomForest (20 features, RPi optimized)/g' ml-detector/config/ml_detector_config.json

# 4. Verify changes
echo "=== sniffer.json changes ==="
grep -A 4 "ransomware_feature_group" sniffer/config/sniffer.json

echo ""
echo "=== ml_detector_config.json changes ==="
grep -A 8 '"ransomware":' ml-detector/config/ml_detector_config.json

# 5. Verify file exists
ls -lh sniffer/config/features/ransomware_20_features.json
```

---

## Validation

After applying changes, validate:

```bash
# Check JSON syntax
python3 -m json.tool sniffer/config/sniffer.json > /dev/null && echo "✅ sniffer.json valid"
python3 -m json.tool ml-detector/config/ml_detector_config.json > /dev/null && echo "✅ ml_detector_config.json valid"
python3 -m json.tool sniffer/config/features/ransomware_20_features.json > /dev/null && echo "✅ ransomware_20_features.json valid"

# Check feature count consistency
SNIFFER_COUNT=$(jq '.feature_groups.ransomware_feature_group.count' sniffer/config/sniffer.json)
DETECTOR_COUNT=$(jq '.ml.level2.ransomware.features_count' ml-detector/config/ml_detector_config.json)
FEATURES_COUNT=$(jq '.features | length' sniffer/config/features/ransomware_20_features.json)

echo "Sniffer expects: $SNIFFER_COUNT features"
echo "Detector expects: $DETECTOR_COUNT features"
echo "JSON defines: $FEATURES_COUNT features"

if [ "$SNIFFER_COUNT" -eq "$DETECTOR_COUNT" ] && [ "$SNIFFER_COUNT" -eq "$FEATURES_COUNT" ]; then
    echo "✅ All configs consistent!"
else
    echo "❌ Config mismatch detected!"
fi
```

---

## Git Commit

After validation:

```bash
git add -A
git commit -m "feat: add ransomware detection features (20 critical features for RPi)

- Add ransomware_20_features.json schema with 20 features
- Update sniffer.json: 83 -> 20 features
- Update ml_detector_config.json: 82 -> 20 features
- Features optimized for Raspberry Pi constraints
- Categories: C&C (6), Lateral Movement (4), Exfiltration (4), Behavioral (6)
- Implementation roadmap and design docs included

Next steps:
- Implement feature extraction in sniffer
- Download and prepare training datasets
- Train RandomForest model and export to ONNX
"

git tag -a v3.3.0-ransomware-features -m "Ransomware detection features v1.0"
```

---

## Expected Build Outcome

After these changes:

```bash
make rebuild

# Expected:
# ✅ Builds successfully (no compile errors)
# ✅ Configs load without errors
# ⚠️  Ransomware model NOT active (enabled: false)
# ℹ️  Feature extraction NOT implemented yet (will extract 0 values)
```

**This is normal!** We're just updating the schema first. Implementation comes next.
