cmake_minimum_required(VERSION 3.10)
project(bolt-tempest-prng VERSION 1.0.0 LANGUAGES C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

# Compiler flags
if(NOT MSVC)
    add_compile_options(-O3 -Wall -Wextra -Wpedantic)
    set(ARCH_FLAGS "-march=native" CACHE STRING "Architecture-specific flags (e.g. -mavx512f)")
    if(CMAKE_SYSTEM_PROCESSOR MATCHES "x86_64|AMD64|aarch64|ARM64|riscv64|RISCV_64")
        add_compile_options(${ARCH_FLAGS})
    endif()
endif()

# Library targets
add_library(adcbolt STATIC code/adcbolt.c)
target_include_directories(adcbolt PUBLIC code)

add_library(tempest STATIC code/tempest_v3.c)
target_include_directories(tempest PUBLIC code)

# Test programs
add_executable(test_bolt tests/test_bolt.c)
target_include_directories(test_bolt PRIVATE code)
target_link_libraries(test_bolt adcbolt)

add_executable(test_tempest tests/test_tempest.c)
target_include_directories(test_tempest PRIVATE code)
target_link_libraries(test_tempest tempest)

# Custom target to run all tests
add_custom_target(test_all
    COMMAND test_bolt
    COMMAND test_tempest
    DEPENDS test_bolt test_tempest
)

# SIMD benchmark (AVX-512 required)
if(CMAKE_SYSTEM_PROCESSOR MATCHES "x86_64|AMD64")
    add_executable(bench_simd code/bench_simd.c code/tempest_simd.c)
    target_include_directories(bench_simd PRIVATE code)
    target_compile_options(bench_simd PRIVATE -mavx512f)
    target_link_libraries(bench_simd m)
endif()

# Install
install(TARGETS adcbolt tempest DESTINATION lib)
install(FILES code/adcbolt.h code/tempest_v3.h code/platform.h include/prng_single_header.h DESTINATION include)
install(TARGETS bench_simd DESTINATION bin OPTIONAL)
