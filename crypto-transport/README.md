# crypto-transport

**Single Responsibility:** Encryption, decryption, compression, and decompression for secure data transport.

## Design Philosophy

This library follows **Via Appia Quality** principles:
- Single Responsibility Principle (SRP)
- Transport-agnostic (no HTTP, ZMQ, or protocol knowledge)
- Minimal API surface (4 core functions)
- No coupling to etcd-client or any component
- Built to last decades

## Purpose

Provides cryptographic and compression primitives for ML Defender components:
- **etcd-client**: Encrypt/compress JSON configs for HTTP transport to etcd-server
- **sniffer**: Encrypt/compress payloads before ZMQ send
- **ml-detector**: Decrypt/decompress on receive, encrypt/compress on send
- **firewall-acl-agent**: Decrypt/decompress ZMQ payloads
- **rag-agent**: Encrypt/compress/decrypt/decompress as needed

## Architecture
```
crypto-transport (independent library)
├── ChaCha20-Poly1305 encryption (libsodium)
├── LZ4 compression
└── Binary-safe API (std::vector<uint8_t>)

Components obtain encryption seed from etcd-server via etcd-client.
crypto-transport has NO knowledge of how keys are distributed.
```

## API

### Core Functions
```cpp
namespace crypto_transport {
    // Encrypt data with ChaCha20-Poly1305
    std::vector<uint8_t> encrypt(const std::vector<uint8_t>& data, 
                                  const std::vector<uint8_t>& key);
    
    // Decrypt data with ChaCha20-Poly1305
    std::vector<uint8_t> decrypt(const std::vector<uint8_t>& data, 
                                  const std::vector<uint8_t>& key);
    
    // Compress data with LZ4
    std::vector<uint8_t> compress(const std::vector<uint8_t>& data);
    
    // Decompress data with LZ4
    std::vector<uint8_t> decompress(const std::vector<uint8_t>& data, 
                                     size_t original_size);
}
```

### Helper Functions
```cpp
namespace crypto_transport {
    // Convert hex string to bytes
    std::vector<uint8_t> hex_to_bytes(const std::string& hex);
    
    // Convert bytes to hex string
    std::string bytes_to_hex(const std::vector<uint8_t>& bytes);
    
    // Get required encryption key size
    size_t get_key_size();
}
```

## Dependencies

- **libsodium** (>= 1.0.18): ChaCha20-Poly1305 encryption
- **liblz4** (>= 1.9.0): LZ4 compression
- **C++20**: Modern C++ features

## Build
```bash
mkdir build && cd build
cmake ..
make -j$(nproc)
sudo make install
```

## Test
```bash
cd build
ctest --output-on-failure
```

## Usage Example
```cpp
#include <crypto_transport/crypto.hpp>
#include <crypto_transport/compression.hpp>

// Get key from etcd-server (32 bytes for ChaCha20)
std::vector<uint8_t> key = crypto_transport::hex_to_bytes(key_from_server);

// Prepare data
std::string json_data = "{\"foo\": \"bar\"}";
std::vector<uint8_t> data(json_data.begin(), json_data.end());

// Compress then encrypt
auto compressed = crypto_transport::compress(data);
auto encrypted = crypto_transport::encrypt(compressed, key);

// Send via ZMQ/HTTP/etc (transport-agnostic)

// Decrypt then decompress
auto decrypted = crypto_transport::decrypt(encrypted, key);
auto decompressed = crypto_transport::decompress(decrypted, data.size());
```

## License

Part of ML Defender (aegisIDS) - Open Source Network Intrusion Detection System