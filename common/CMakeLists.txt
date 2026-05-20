cmake_minimum_required(VERSION 3.16)
project(vault_client CXX)
set(CMAKE_CXX_STANDARD 20)

find_package(PkgConfig REQUIRED)
pkg_check_modules(JSONCPP REQUIRED jsoncpp)
find_package(OpenSSL REQUIRED)
find_package(nlohmann_json REQUIRED)
find_package(GTest REQUIRED)

# ── libcrypto_provider (vault-client shared library) ─────────────────────────

add_library(crypto_provider SHARED
    crypto_provider.cpp
    vault_provider.cpp
    vault_client.cpp
    vault_transport.cpp
    vault_types.h
    autonomy_publisher.cpp
    cache_manager.cpp
    crypto_deriver.cpp
    etcd_registrar.cpp
    EtcdServiceRegistry.cpp
    seed_file_provider.cpp
)

target_include_directories(crypto_provider PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
    /usr/local/include
    /usr/local/include/seed_client
    ${JSONCPP_INCLUDE_DIRS}
)

target_link_libraries(crypto_provider PRIVATE
    OpenSSL::SSL
    OpenSSL::Crypto
    /usr/local/lib/libseed_client.so
    /usr/local/lib/libcrypto_transport.so
    zmq
    pthread
    ${JSONCPP_LIBRARIES}
    curl
)

set_target_properties(crypto_provider PROPERTIES
    VERSION 1.0.0
    SOVERSION 1
    OUTPUT_NAME crypto_provider
)

# Install library
install(TARGETS crypto_provider
    LIBRARY DESTINATION lib
)

# Install headers as vault_client/
install(FILES
    crypto_provider.h
    autonomy_publisher.h
    autonomy_state_writer.h
    crypto_autonomy.h
    vault_client.h
    vault_provider.h
    vault_transport.h
    vault_types.h
    cache_manager.h
    crypto_deriver.h
    etcd_registrar.h
    EtcdServiceRegistry.h
    seed_file_provider.h
    DESTINATION include/vault_client
)

# ── test_alert_client ─────────────────────────────────────────────────────────

add_executable(test_alert_client
    tests/test_alert_client.cpp
)

target_include_directories(test_alert_client PRIVATE
    include
    /usr/local/include
)

target_link_libraries(test_alert_client PRIVATE
    GTest::GTest
    GTest::Main
    nlohmann_json::nlohmann_json
    OpenSSL::SSL
    OpenSSL::Crypto
    pthread
)

enable_testing()
add_test(NAME test_alert_client COMMAND test_alert_client)
