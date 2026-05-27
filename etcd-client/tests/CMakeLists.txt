# etcd-client/tests/CMakeLists.txt
cmake_minimum_required(VERSION 3.16)

# ============================================================================
# DEPENDENCIES
# ============================================================================

# Find crypto-transport library
find_library(CRYPTO_TRANSPORT_LIB crypto_transport PATHS /usr/local/lib REQUIRED)

# Find OpenSSL (for HMAC tests)
find_package(OpenSSL REQUIRED)

# ============================================================================
# EXISTING TESTS (crypto-transport standalone)
# ============================================================================

# Test: Compression
add_executable(test_compression test_compression.cpp)
target_link_libraries(test_compression
        PRIVATE
        ${CRYPTO_TRANSPORT_LIB}
)
target_include_directories(test_compression
        PRIVATE
        /usr/local/include
)

# Test: Encryption
add_executable(test_encryption test_encryption.cpp)
target_link_libraries(test_encryption
        PRIVATE
        ${CRYPTO_TRANSPORT_LIB}
)
target_include_directories(test_encryption
        PRIVATE
        /usr/local/include
)

# Test: Complete Pipeline (Compression + Encryption)
add_executable(test_pipeline test_pipeline.cpp)
target_link_libraries(test_pipeline
        PRIVATE
        ${CRYPTO_TRANSPORT_LIB}
)
target_include_directories(test_pipeline
        PRIVATE
        /usr/local/include
)

# Test: Integration test (uses etcd_client library)
add_executable(test_put_config_integration test_put_config_integration.cpp)
target_link_libraries(test_put_config_integration
        PRIVATE
        etcd_client
)
target_include_directories(test_put_config_integration
        PRIVATE
        ${CMAKE_SOURCE_DIR}/include
)

# ============================================================================
# NEW TESTS (Day 53 - HMAC Utilities)
# ============================================================================

# Test: HMAC Client Unit Tests
add_executable(test_hmac_client test_hmac_client.cpp)
target_link_libraries(test_hmac_client
        PRIVATE
        etcd_client
        OpenSSL::SSL
        OpenSSL::Crypto
)
target_include_directories(test_hmac_client
        PRIVATE
        ${CMAKE_SOURCE_DIR}/include
)

# Test: HMAC Integration Tests (requires etcd-server running)
add_executable(test_hmac_integration_client test_hmac_integration_client.cpp)
target_link_libraries(test_hmac_integration_client
        PRIVATE
        etcd_client
        OpenSSL::SSL
        OpenSSL::Crypto
)
target_include_directories(test_hmac_integration_client
        PRIVATE
        ${CMAKE_SOURCE_DIR}/include
)

# Test: HMAC Grace Period (Day 57 - HMAC key rotation with grace period)
# NOTE: This test uses GTest which we don't have installed. Disabled for now.
# TODO: Rewrite without GTest or install GTest properly
# add_executable(test_etcd_client_hmac_grace_period test_etcd_client_hmac_grace_period.cpp)
# target_link_libraries(test_etcd_client_hmac_grace_period
#         PRIVATE
#         etcd_client
#         OpenSSL::SSL
#         OpenSSL::Crypto
# )
# target_include_directories(test_etcd_client_hmac_grace_period
#         PRIVATE
#         ${CMAKE_SOURCE_DIR}/include
# )

# ============================================================================
# CTEST REGISTRATION
# ============================================================================

# Add tests to CTest
add_test(NAME compression COMMAND test_compression)
add_test(NAME encryption COMMAND test_encryption)
add_test(NAME pipeline COMMAND test_pipeline)
add_test(NAME hmac_client COMMAND test_hmac_client)
# add_test(NAME hmac_grace_period COMMAND test_etcd_client_hmac_grace_period)  # Disabled - requires GTest

# Note: test_hmac_integration_client requires etcd-server running,
# so we don't add it to CTest by default. Run manually:
#   ./test_hmac_integration_client

# Test: Service Discovery (Day 59 - Service Discovery Paths)
add_executable(test_service_discovery test_service_discovery.cpp)
target_link_libraries(test_service_discovery
        PRIVATE
        etcd_client
        OpenSSL::SSL
        OpenSSL::Crypto
)
target_include_directories(test_service_discovery
        PRIVATE
        ${CMAKE_SOURCE_DIR}/include
)

# ============================================================================
# BUILD SUMMARY
# ============================================================================

message(STATUS "========================================")
message(STATUS "etcd-client Tests Configuration")
message(STATUS "========================================")
message(STATUS "Tests configured:")
message(STATUS "  - test_compression (crypto-transport)")
message(STATUS "  - test_encryption (crypto-transport)")
message(STATUS "  - test_pipeline (crypto-transport)")
message(STATUS "  - test_put_config_integration (etcd_client)")
message(STATUS "  - test_hmac_client (Day 53 - HMAC unit tests)")
message(STATUS "  - test_hmac_integration_client (Day 53 - requires etcd-server)")
message(STATUS "  - test_service_discovery (Day 59 - requires etcd-server)")
message(STATUS "  ⚠️  test_etcd_client_hmac_grace_period (DISABLED - requires GTest)")
message(STATUS "========================================")
message(STATUS "OpenSSL: ${OPENSSL_VERSION}")
message(STATUS "========================================")