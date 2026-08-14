CC = gcc
CFLAGS = -O3 -march=native -flto -Wall -Wextra -Wpedantic -fstack-protector-strong -D_FORTIFY_SOURCE=2 -Icode -Iinclude

.PHONY: all test clean bench kat

all: test

kat: code/kat_check_main.c code/tempest_v3.c code/kat_tempest.h
	$(CC) $(CFLAGS) -o code/kat_check code/kat_check_main.c code/tempest_v3.c
	./code/kat_check

test: test_bolt test_tempest
	@echo ""
	@echo "========== ADC-Bolt =========="
	@./tests/test_bolt
	@echo ""
	@echo "========== Tempest v3 (Algorithm 1) ======"
	@./tests/test_tempest

test_bolt: tests/test_bolt.c code/adcbolt.c code/adcbolt.h
	$(CC) $(CFLAGS) -o tests/test_bolt tests/test_bolt.c code/adcbolt.c

test_tempest: tests/test_tempest.c code/tempest_v3.c code/tempest_v3.h
	$(CC) $(CFLAGS) -o tests/test_tempest tests/test_tempest.c code/tempest_v3.c

benchmark: code/benchmark.c code/adcbolt.c code/tempest_v3.c code/adcbolt.h code/tempest_v3.h
	$(CC) $(CFLAGS) -o code/benchmark code/benchmark.c code/adcbolt.c code/tempest_v3.c

bench: benchmark
	./code/benchmark

bench_simd: code/bench_simd.c code/tempest_simd.c code/tempest_simd.h
	$(CC) $(CFLAGS) -mavx512f -o code/bench_simd code/bench_simd.c code/tempest_simd.c -lm

clean:
	rm -f tests/test_bolt tests/test_tempest code/benchmark code/bench_simd tests/test_bolt.exe tests/test_tempest.exe code/benchmark.exe code/bench_simd.exe
