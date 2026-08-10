#!/usr/bin/env python3
"""
Tempest v3 FPGA Demo Script
Reads random bits from FPGA board via serial port,
displays throughput and runs NIST SP 800-22 tests.

Usage:
  python tempest_demo.py [--port COM3] [--baud 115200]

Requires: pyserial, numpy, scipy
"""

import sys
import time
import struct
import argparse
import threading
from collections import deque

import numpy as np

try:
    import serial
except ImportError:
    print("Please install pyserial: pip install pyserial")
    sys.exit(1)


class TempestDemo:
    """Real-time Tempest v3 FPGA demo interface."""

    def __init__(self, port: str = "/dev/ttyUSB0", baud: int = 115200):
        self.port = port
        self.baud = baud
        self.ser = None
        self.running = False

        # Statistics
        self.bytes_received = 0
        self.start_time = None
        self.throughput_history = deque(maxlen=100)  # last 100 samples

        # NIST test data buffer
        self.test_buffer = bytearray()

    def connect(self) -> bool:
        """Connect to FPGA board via serial."""
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=1)
            print(f"[OK] Connected to {self.port} at {self.baud} baud")
            return True
        except Exception as e:
            print(f"[ERR] Could not connect: {e}")
            print("Make sure the FPGA board is connected and the")
            print("serial port is correct.")
            return False

    def disconnect(self):
        if self.ser and self.ser.is_open:
            self.ser.close()

    def read_data(self, num_bytes: int = 16) -> bytes:
        """Read random bytes from FPGA."""
        if not self.ser or not self.ser.is_open:
            return b""
        return self.ser.read(num_bytes)

    def display_stats(self):
        """Display current throughput statistics."""
        elapsed = time.time() - self.start_time if self.start_time else 1
        bits = self.bytes_received * 8
        throughput = bits / elapsed / 1e6  # Mbit/s

        print(f"\r[Tempest v3 FPGA] "
              f"Received: {self.bytes_received / 1024:.1f} KB | "
              f"Throughput: {throughput:.2f} Mbit/s | "
              f"Running NIST: {'✓' if len(self.test_buffer) >= 125000 else '...'}"
              f"     ", end="", flush=True)

        return throughput

    def run_nist_test(self):
        """Run NIST SP 800-22 frequency test on collected data."""
        if len(self.test_buffer) < 125000:  # need at least 1M bits
            return None

        print("\n[Testing] Running NIST SP 800-22 frequency test...")
        data = np.frombuffer(self.test_buffer[:125000], dtype=np.uint8)
        bits = np.unpackbits(data)

        # Frequency (monobit) test
        n = len(bits)
        s = abs(np.sum(2 * bits.astype(np.int8) - 1)) / np.sqrt(n)
        p_value = 1 - self._erfc(s / np.sqrt(2))

        print(f"[NIST] Frequency test: p-value = {p_value:.6f}")
        print(f"[NIST] {'PASS' if p_value > 0.01 else 'FAIL'} (threshold: 0.01)")

        # Runs test
        runs = np.sum(bits[1:] != bits[:-1]) + 1
        pi = np.mean(bits)
        denom = 2 * np.sqrt(n) * pi * (1 - pi)
        if denom == 0:
            return p_value, 0
        v = abs(runs - 2 * n * pi * (1 - pi)) / denom
        p_run = 1 - self._erfc(v / np.sqrt(2))

        print(f"[NIST] Runs test: p-value = {p_run:.6f}")
        print(f"[NIST] {'PASS' if p_run > 0.01 else 'FAIL'} (threshold: 0.01)")

        return p_value, p_run

    @staticmethod
    def _erfc(x):
        """Complementary error function."""
        from scipy.special import erfc
        return erfc(x)

    def run(self, num_samples: int = 1024):
        """Main demo loop."""
        if not self.connect():
            return

        print(f"\n{'=' * 60}")
        print(f"  Tempest v3 Hardware PRNG Demonstration")
        print(f"  Reading {num_samples} × 128-bit blocks from FPGA")
        print(f"{'=' * 60}\n")

        self.running = True
        self.start_time = time.time()
        display_interval = 0.5  # update display every 0.5s
        last_display = time.time()
        nist_pending = False

        try:
            for i in range(num_samples):
                data = self.read_data(16)  # 128 bits
                if not data:
                    time.sleep(0.01)
                    continue

                self.bytes_received += len(data)
                self.test_buffer.extend(data)

                # Display as hex
                hex_str = data.hex()
                print(f"[{i+1:4d}] {hex_str}")

                # Update stats periodically
                now = time.time()
                if now - last_display > display_interval:
                    tp = self.display_stats()
                    last_display = now

                # Run NIST test when enough data collected
                if len(self.test_buffer) >= 125000 and not nist_pending:
                    nist_pending = True
                    self.run_nist_test()
                    nist_pending = False

            print(f"\n\n{'=' * 60}")
            print(f"  Demo Complete")
            print(f"  Total: {self.bytes_received / 1024:.1f} KB")
            print(f"  Time:  {time.time() - self.start_time:.1f}s")
            print(f"{'=' * 60}")

        except KeyboardInterrupt:
            print("\n\nDemo interrupted by user.")
        finally:
            self.disconnect()


def main():
    parser = argparse.ArgumentParser(
        description="Tempest v3 FPGA Hardware PRNG Demo")
    parser.add_argument("--port", default="/dev/ttyUSB0",
                        help="Serial port (default: /dev/ttyUSB0)")
    parser.add_argument("--baud", type=int, default=115200,
                        help="Baud rate (default: 115200)")
    parser.add_argument("--samples", type=int, default=1024,
                        help="Number of 128-bit blocks to read")
    args = parser.parse_args()

    demo = TempestDemo(port=args.port, baud=args.baud)
    demo.run(num_samples=args.samples)


if __name__ == "__main__":
    main()
