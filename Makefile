CC = gcc
CFLAGS = -O3 -march=native -flto -Wall -Wextra -Wpedantic -fstack-protector-strong -D_FORTIFY_SOURCE=2 -I.

.PHONY: all test clean bench

all: test

test: test_bolt test_tempest
	@echo ""
	@echo "========== ADC-Bolt =========="
	@./test_bolt
	@echo ""
	@echo "====== 4-cmul Tempest v3 ====="
	@./test_tempest

test_bolt: test_bolt.c src/adcbolt.c src/adcbolt.h
	$(CC) $(CFLAGS) -o test_bolt test_bolt.c src/adcbolt.c

test_tempest: test_tempest.c src/tempest_v3.c src/tempest_v3.h
	$(CC) $(CFLAGS) -o test_tempest test_tempest.c src/tempest_v3.c

benchmark: benchmark.c src/adcbolt.c src/tempest_v3.c src/adcbolt.h src/tempest_v3.h
	$(CC) $(CFLAGS) -o benchmark benchmark.c src/adcbolt.c src/tempest_v3.c

bench: benchmark
	./benchmark

clean:
	rm -f test_bolt test_tempest benchmark test_bolt.exe test_tempest.exe benchmark.exe
