# tempest-rng.rb — Homebrew formula for Bolt & Tempest PRNG library
# Usage:
#   brew tap paim-creater/prng https://github.com/paim-creater/prng
#   brew install tempest-rng

class TempestRng < Formula
  desc "Tempest v3: cryptographic-grade CSPRNG (17.7 Gbit/s, 2^128 security)"
  homepage "https://github.com/paim-creater/prng"
  url "https://github.com/paim-creater/prng.git",
      tag:      "v1.0.0",
      revision: "HEAD"
  license "MIT"
  head "https://github.com/paim-creater/prng.git", branch: "main"

  depends_on "gcc" => :build

  def install
    system "make", "-C", buildpath, "CC=gcc-14", "PREFIX=#{prefix}", "install"
    lib.install Dir[buildpath/"*.a"]
    include.install Dir[buildpath/"src/*.h"]
  end

  test do
    (testpath/"test.c").write <<~EOS
      #include <stdio.h>
      #include "tempest_v3.h"
      int main() {
          tx4_state s;
          uint64_t key[4] = {1,2,3,4}, nonce[2] = {5,6};
          tx5cmul_init(&s, key, nonce);
          uint64_t r = tx5cmul_next(&s);
          printf("%llx\\n", (unsigned long long)r);
          return 0;
      }
    EOS
    system ENV.cc, "test.c", "-L#{lib}", "-ltempest", "-o", "test"
    system "./test"
  end
end
