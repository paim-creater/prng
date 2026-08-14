# wolfssl_tempest/ — Tempest v3 as the RNG for wolfSSL via crypto callbacks

Reference integration implementing the path recommended by the
wolfSSL maintainer in [wolfSSL/wolfssl#10802](https://github.com/wolfSSL/wolfssl/issues/10802):
*"use the crypto callbacks to intercept the RNG calls and service with
their preferred option"* — no modification of wolfSSL itself.

## What is verified

| Level | Result |
|---|---|
| **RNG** | `wc_RNG_GenerateBlock` routed through the crypto callback is **bit-exact** with the KAT-verified C reference for the same seed |
| **TLS 1.2 handshake** | full handshake (certificate verification + key exchange) completes with every handshake RNG request serviced by Tempest — **12 requests on the server side, 9 on the client side** |

## Files

| File | Role |
|---|---|
| `tempest_wolfssl_patch.c` | the crypto callback + registration/seed helpers |
| `test_wolfssl_cb.c` | RNG-level KAT verification |
| `tls_handshake.c` | full TLS handshake client/server with RNG-request counter |

## Why this works where other integrations do not

wolfSSL's crypto-callback mechanism is the *designed-for-customers*
extension point: `wc_RNG_GenerateBlock` checks the RNG's `devId`
against the registered device callbacks
(`wc_CryptoCb_RandomBlock`), so an application can opt in to an
external RNG without touching the library — the trust model is
explicit ("the application owns the consequence").

Contrast with replacing wolfSSL's *internal* seed source
(`CUSTOM_RAND_GENERATE_SEED`): that slot is entropy-source semantics
(health tests, prediction resistance) that a deterministic CSPRNG
cannot honestly satisfy. The crypto-callback path sidesteps that: the
application seeds Tempest from real entropy (helper
`tempest_wolfssl_seed_from_wolfssl` uses wolfSSL's own RNG for the
48-byte key/nonce) and then lets Tempest expand it.

## Build & run (WSL, wolfSSL 5.9.1 with --enable-cryptocb)

```bash
# wolfSSL source: apt source wolfssl (Ubuntu) or from wolfSSL GitHub
cd wolfssl-5.9.1 && ./autogen.sh && ./configure --enable-cryptocb \
    --enable-examples --disable-shared && make -j4

# RNG-level test
gcc -I$HOME/wolfssl-5.9.1 -I.. -O2 -o test_wolfssl_cb \
    test_wolfssl_cb.c tempest_wolfssl_patch.c ../code/tempest_v3.c \
    $HOME/wolfssl-5.9.1/src/.libs/libwolfssl.a -lpthread -lm
./test_wolfssl_cb
# expect: RNG through wolfSSL callback bit-exact with C reference: PASS

# TLS handshake test (run from the wolfSSL source root for certs/)
gcc -I$HOME/wolfssl-5.9.1 -I.. -O2 -o tls_handshake \
    tls_handshake.c tempest_wolfssl_patch.c ../code/tempest_v3.c \
    $HOME/wolfssl-5.9.1/src/.libs/libwolfssl.a -lpthread -lm
./tls_handshake server 11111 &  sleep 1; ./tls_handshake client 11111
# expect: handshake OK on both sides, RNG served counters > 0
```

## Security notes

- Seed Tempest with real entropy once per process
  (`tempest_wolfssl_seed_from_wolfssl`); `seed_deterministic` is for
  tests/reproducible simulation only.
- The callback services every RNG request for the registered devId —
  including key generation — so the application is responsible for
  the security of the resulting construction.
- `CRYPTOCB_UNAVAILABLE` is returned for all non-RNG algorithms:
  wolfSSL continues to handle hashes/ciphers/PK internally.
