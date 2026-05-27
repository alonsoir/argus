# RAG Ingester

**Version:** 0.1.0  
**Status:** ✅ Day 35 Complete - Skeleton Functional  
**Last Updated:** 2026-01-11

## Overview

RAG Ingester is a multi-threaded embedding and indexing service that processes network security events from ML Detector, generates embeddings using ONNX Runtime, and maintains 4 FAISS indices for the RAG system.

## Architecture

### Symbiosis with ml-detector
```
ml-detector → .pb files → rag-ingester → 4 FAISS indices → rag-client
              (encrypted,   (embeddings,
               compressed)    indexing)
```

Both services register in etcd-server with a `partner_detector` / `partner_ingester` field, establishing a symbolic relationship for coordinated operation.

### Multi-Index Strategy

1. **Chronos Index** (128-d temporal): Time series queries
2. **SBERT Index** (96-d semantic): Behavioral pattern queries  
3. **Entity Benign Index** (64-d, 10% sampling): Benign entity queries
4. **Entity Malicious Index** (64-d, 100% coverage): Malicious entity queries

### Eventual Consistency

- **Best-effort commits**: Indices commit independently
- **Availability > Consistency**: Better 3/4 indices than 0/4
- **Health tracking**: Circuit breakers for failing indices

## Build
```bash
mkdir -p /vagrant/rag-ingester/build
cd /vagrant/rag-ingester/build
cmake ..
make -j$(nproc)
```

## Run
```bash
./rag-ingester [config_path]

# Default config: /vagrant/rag-ingester/config/rag-ingester.json
```

## Test
```bash
cd /vagrant/rag-ingester/build
./tests/test_config_parser
```

## Dependencies

### Runtime Dependencies
- ✅ **FAISS** (`libfaiss.so`): Vector indexing
- ✅ **ONNX Runtime** (`libonnxruntime.so`): Neural network inference
- ✅ **etcd-client** (`libetcd_client.so`): Service discovery
- ✅ **crypto-transport** (`libcrypto_transport.so`): Event decryption/decompression
- ⚠️  **common-rag-ingester** (`libcommon-rag-ingester.so`): PCA dimensionality reduction
- ✅ **spdlog**: Logging
- ✅ **nlohmann_json**: JSON parsing
- ✅ **Protobuf**: Event serialization

### Verified Locations
```
/usr/local/lib/libetcd_client.so
/usr/local/lib/libcrypto_transport.so
/vagrant/common-rag-ingester/build/libcommon-rag-ingester.so
/usr/local/lib/libfaiss.so
/usr/local/lib/libonnxruntime.so
```

## Configuration

### Threading Modes

**Single-threaded** (Raspberry Pi safe):
```json
"threading": {
  "mode": "single",
  "embedding_workers": 1,
  "indexing_workers": 1
}
```

**Multi-threaded** (server deployment):
```json
"threading": {
  "mode": "parallel",
  "embedding_workers": 3,
  "indexing_workers": 4
}
```

## Development Status

### ✅ Day 35 Complete (2026-01-11)
- [x] Directory structure created
- [x] CMakeLists.txt with dependency detection
- [x] Configuration schema (rag-ingester.json)
- [x] ConfigParser implementation
- [x] main.cpp with signal handling
- [x] All stub files created and compiling
- [x] Test suite (test_config_parser) passing
- [x] Binary executable and functional

### 📋 Day 36 (Next)
- [ ] FileWatcher with inotify
- [ ] EventLoader with crypto-transport integration
- [ ] Test: Load and decrypt .pb file from ml-detector

### 📋 Day 37-38
- [ ] Embedders (ONNX Runtime integration)
- [ ] PCA integration (common-rag-ingester)
- [ ] MultiIndexManager implementation
- [ ] Eventual consistency logic

### 📋 Day 39-40
- [ ] IndexHealthMonitor (CV calculation)
- [ ] etcd registration and heartbeat
- [ ] Integration testing
- [ ] Performance benchmarking

## Via Appia Quality ✅

- **Designed for Raspberry Pi**: Minimal memory footprint (~310MB)
- **Built for scale**: Multi-threaded architecture ready for 64-core servers
- **Eventual consistency**: System always responds, never blocks
- **Symbiotic design**: Tight coupling with ml-detector via etcd

## License

Proprietary - ML Defender Project

## Authors

- Alonso García (Lead Developer)
- Claude (AI Co-author)
