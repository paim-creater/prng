cmake_minimum_required(VERSION 3.10)
project(bolt-tempest-prng VERSION 1.0.0 LANGUAGES C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

# Detect platform
if(CMAKE_SYSTEM_PROCESSOR MATCHES "x86_64|AMD64")
    add_compile_options(-march=native)
elseif(CMAKE_SYSTEM_PROCESSOR MATCHES "aarch64|ARM64")
    add_compile_options(-march=native)
endif()

if(NOT MSVC)
    add_compile_options(-O3 -Wall -Wextra)
endif()

# Library targets
add_library(adcbolt STATIC src/adcbolt.c)
target_include_directories(adcbolt PUBLIC src)

add_library(tempest STATIC src/tempest_v3.c)
target_include_directories(tempest PUBLIC src)

# Test programs
add_executable(test_all test_bolt.c test_tempest.c)
target_include_directories(test_all PRIVATE src)
target_link_libraries(test_all adcbolt tempest)

# Benchmark
add_executable(benchmark benchmark.c)
target_include_directories(benchmark PRIVATE src)
target_link_libraries(benchmark adcbolt tempest)

# Install
install(TARGETS adcbolt tempest DESTINATION lib)
install(FILES src/adcbolt.h src/tempest_v3.h src/platform.h DESTINATION include)
