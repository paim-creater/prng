# demo/ — adoption evidence: Tempest consumed by real libraries

Each demo runs Tempest v3 as the randomness source of a real,
widely-used library through that library's **official extension
point** — no upstream modification. Together they are the
"adoption" evidence for the paper's ecosystem-integration section.

| Demo | Consumes | Via | Run |
|---|---|---|---|
| `sklearn_dp_demo.py` | scikit-learn (real ML pipeline) | NumPy BitGenerator → `np.random.Generator` | `python sklearn_dp_demo.py` |
| `demo_gofakeit.go` | gofakeit (Go fake-data library, 4k+ stars) | `math/rand/v2.Source` | `go build && ./demo_gofakeit` |
| `tempest_ossl_seed.c` | OpenSSL 3.x (TLS/SSH infrastructure) | provider `OSSL_FUNC_rand` (seed-source) | see below |
| `test_ossl_seed.c` | KAT + EVP_RAND API verification of the provider | — | see below |

## scikit-learn (needs `numpy`, `scikit-learn`, built bitgen)

```bash
python setup_bitgen.py build_ext --inplace   # once
python demo/sklearn_dp_demo.py
```

## gofakeit (needs Go; module path uses the local `golang/` port)

```bash
cd demo
GOPROXY=https://goproxy.cn go build -o demo_gofakeit demo_gofakeit.go
./demo_gofakeit
```

## OpenSSL 3.x seed-source provider (needs `libssl-dev`; WSL)

```bash
cd demo
gcc -fPIC -shared -O2 -o tempest_ossl_seed.so tempest_ossl_seed.c ../code/tempest_v3.c
gcc -O2 -o test_ossl_seed test_ossl_seed.c tempest_ossl_seed.c ../code/tempest_v3.c -lcrypto -ldl -pthread
OPENSSL_MODULES=. ./test_ossl_seed
# expect: KAT through EVP_RAND API: 5/5 PASS
```

The provider registers a `seed-source` RAND algorithm (`"tempest"`):
on instantiate it takes 48 bytes of OS entropy (32 key + 16 nonce)
and expands them with Tempest; `generate` emits the Tempest stream as
seed material for the DRBG stack. Semantics and security notes:

- Entropy still comes from the OS (the provider never fabricates
  entropy — a seed source without entropy would be the dead-key class
  the paper's framework detects).
- The provider sits **outside the FIPS boundary**, the official slot
  for third-party seed sources.
- KAT path: `EVP_RAND_instantiate(adin=key||nonce)` reproduces the
  published 5-block KAT byte-exactly through the OpenSSL API.

To make it the active seed source: `RAND_set_seed_source_type(NULL,
"tempest", ...)` in application code, or an `openssl.cnf` `random`
section — see OpenSSL provider documentation.
