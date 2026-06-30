/* tempest_prng.h — LibTomCrypt PRNG backend for Tempest v3
 *
 * Usage:
 *   #include "tempest_prng.h"
 *   int idx = register_prng(&tempest_prng_desc);
 *   // then use idx with any libtomcrypt PRNG function
 *
 * Requires: LibTomCrypt >= 1.18, Tempest v3 (tempest_v3.h)
 */
#ifndef TEMPEST_PRNG_H
#define TEMPEST_PRNG_H

#include <tomcrypt.h>

#ifdef __cplusplus
extern "C" {
#endif

extern const struct ltc_prng_descriptor tempest_prng_desc;

#ifdef __cplusplus
}
#endif

#endif /* TEMPEST_PRNG_H */
