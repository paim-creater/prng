# tempest-rng.rb — Homebrew formula for Bolt & Tempest PRNG library
# Usage:
#   brew tap paim-creater/prng https://github.com/paim-creater/prng
#   brew install tempest-rng

class TempestRng < Formula
  desc "Tempest v3: cryptographic-grade CSPRNG (19.7 Gbit/s, 2^128 ZFC-provable deg)"
  homepage "https://github.com/paim-creater/prng"
  url "https://github.com/paim-creater/prng.git",
      tag:      "v1.0.0",
      revision: "HEAD"
  license "MIT"
  head "https://github.com/paim-creater/prng.git", branch: "main"

  depends_on "cmake" => :build
  depends_on "gcc" => :build

  def install
    system "cmake", "-S", buildpath, "-B", "build",
           "-DCMAKE_INSTALL_PREFIX=#{prefix}",
           "-DCMAKE_C_COMPILER=gcc"
    system "cmake", "--build", "build"
    system "cmake", "--install", "build"
  end

  test do
    (testpath/"test.c").write <<~EOS
      #include <stdio.h>
      #include "tempest_v3.h"
      int main() {
          tempest_state s;
          uint64_t key[4] = {1,2,3,4}, nonce[2] = {5,6};
          tempest_init(&s, key, nonce);
          uint64_t r = tempest_u64(&s);
          printf("%llx\n", (unsigned long long)r);
          return 0;
      }
    EOS
    system ENV.cc, "test.c", "-I#{include}", "-L#{lib}", "-ltempest", "-o", "test"
    system "./test"
  end
end
