cmake_minimum_required(VERSION 3.16)
project(test_alert_client CXX)

set(CMAKE_CXX_STANDARD 20)

find_package(PkgConfig REQUIRED)
find_package(OpenSSL REQUIRED)

# nlohmann/json
find_package(nlohmann_json REQUIRED)

# GTest
find_package(GTest REQUIRED)

add_executable(test_alert_client
    tests/test_alert_client.cpp
)

target_include_directories(test_alert_client PRIVATE
    include
    /usr/local/include   # httplib.h
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
