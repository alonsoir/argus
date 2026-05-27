# crypto-transport/tests/CMakeLists.txt

# Find Google Test (optional, fallback to manual compilation)
find_package(GTest QUIET)

if(NOT GTest_FOUND)
    message(STATUS "GTest not found, using manual test compilation")
endif()

# Helper macro to add a test executable
macro(add_crypto_transport_test test_name)
    add_executable(${test_name} ${test_name}.cpp)

    target_link_libraries(${test_name}
            PRIVATE
            crypto_transport
    )

    target_include_directories(${test_name}
            PRIVATE
            ${CMAKE_SOURCE_DIR}/include
    )

    if(GTest_FOUND)
        target_link_libraries(${test_name} PRIVATE GTest::GTest GTest::Main)
    endif()

    add_test(NAME ${test_name} COMMAND ${test_name})
endmacro()

# Add individual test executables
add_crypto_transport_test(test_crypto)
add_crypto_transport_test(test_compression)
add_crypto_transport_test(test_integration)

# test_crypto_transport — requiere libseed_client (ADR-013 PHASE 2)
find_library(LIBSEED_CLIENT_LIB NAMES seed_client HINTS /usr/local/lib REQUIRED)
find_path(LIBSEED_CLIENT_INC seed_client/seed_client.hpp HINTS /usr/local/include REQUIRED)
add_executable(test_crypto_transport test_crypto_transport.cpp)
target_include_directories(test_crypto_transport PRIVATE ${CMAKE_SOURCE_DIR}/include ${LIBSEED_CLIENT_INC})
target_link_libraries(test_crypto_transport PRIVATE crypto_transport ${LIBSEED_CLIENT_LIB} GTest::GTest GTest::Main sodium)
add_test(NAME test_crypto_transport COMMAND test_crypto_transport)

# test_integ_contexts — TEST-INTEG-1/2/3 (gate arXiv, DAY 99)
add_executable(test_integ_contexts test_integ_contexts.cpp)
target_include_directories(test_integ_contexts PRIVATE ${CMAKE_SOURCE_DIR}/include ${LIBSEED_CLIENT_INC})
target_link_libraries(test_integ_contexts PRIVATE crypto_transport ${LIBSEED_CLIENT_LIB} GTest::GTest GTest::Main sodium lz4)
add_test(NAME test_integ_contexts COMMAND test_integ_contexts)

# Summary
message(STATUS "========================================")
message(STATUS "crypto-transport Tests Configuration")
message(STATUS "========================================")
if(GTest_FOUND)
    message(STATUS "Test framework: Google Test")
else()
    message(STATUS "Test framework: Manual (no GTest)")
endif()
message(STATUS "Tests: test_crypto, test_compression, test_integration, test_crypto_transport")
message(STATUS "========================================")