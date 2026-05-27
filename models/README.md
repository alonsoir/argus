# ML Models - Confidential

**DO NOT COMMIT MODELS TO GIT**

Models are industrial secrets and should never be pushed to the repository.

## Local Setup

1. Models are stored locally in:
   - `models/production/` - Production models
   - `models/experimental/` - Experimental models
   - `models/archive/` - Archived versions

2. To obtain models:
   - Contact ML team lead
   - Access internal model registry
   - Or train locally using training scripts

## Model Inventory

### Level 1 (Attack Detection)
- `rf_production_sniffer_compatible.joblib` - 23 features
- `rf_production_sniffer_compatible_scaler.joblib`

### Level 2 (Specialized)
- `ddos_random_forest.joblib` - 82 features
- `ransomware_random_forest.joblib` - 82 features

### Level 3 (Normal Traffic)
- `internal_normal_detector.joblib` - 4 features

## Feature Mapping

See `sniffer_feature_mapping.txt` for the exact order of features expected by models.

## Security

- Models contain proprietary algorithms and training data
- Trained on confidential datasets
- Part of company IP - keep secure
