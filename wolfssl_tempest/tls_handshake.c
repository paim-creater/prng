/* tls_handshake.c — full TLS handshake whose RNG is serviced by
 * Tempest through the wolfSSL crypto-callback mechanism.
 *
 * Usage: tls_handshake [server|client] [port]
 *   server: listens, accepts one connection, echoes a line
 *   client: connects, sends "ping", prints "pong"
 *
 * The TLS context is bound to DEV_ID via wolfSSL_CTX_SetDevId, so
 * every RNG request during the handshake (key generation, nonces,
 * TLS randomness) is routed to the Tempest callback registered on
 * that device id.
 *
 * Build (WSL, wolfSSL 5.9.1 built with --enable-cryptocb, run from
 * the wolfSSL source root so certs/ resolves):
 *   gcc -I$HOME/wolfssl-5.9.1 -I.. -O2 -o tls_handshake \
 *       tls_handshake.c tempest_wolfssl_patch.c ../code/tempest_v3.c \
 *       $HOME/wolfssl-5.9.1/src/.libs/libwolfssl.a -lpthread -lm
 *   ./tls_handshake server 11111 &  sleep 1; ./tls_handshake client 11111
 */
#include <wolfssl/options.h>
#include <wolfssl/ssl.h>
#include <wolfssl/wolfcrypt/cryptocb.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>

int tempest_wolfssl_register(int devId);
void tempest_wolfssl_unregister(int devId);
void tempest_wolfssl_seed_deterministic(uint64_t seed);
int  tempest_wolfssl_seed_from_wolfssl(void);
int  tempest_wolfssl_crypto_cb(int devId, wc_CryptoInfo* info, void* ctx);

#define DEV_ID 1234
#define PORT_DEFAULT 11111
#define CERTS_DIR "certs"

static int rng_served = 0;

/* Counts how many RNG requests Tempest serviced (asserts the
 * handshake randomness actually flowed through the callback). */
static int TempestCryptoCbCount(int devId, wc_CryptoInfo* info, void* ctx)
{
    if (info->algo_type == WC_ALGO_TYPE_RNG) {
        /* delegate to the reference callback in tempest_wolfssl_patch.c */
        rng_served++;
        return tempest_wolfssl_crypto_cb(devId, info, ctx);
    }
    return CRYPTOCB_UNAVAILABLE;
}

static int run_server(int port)
{
    int listen_fd, conn_fd;
    struct sockaddr_in addr;
    char buf[64];
    int ret;
    WOLFSSL_CTX* ctx;
    WOLFSSL* ssl;

    listen_fd = socket(AF_INET, SOCK_STREAM, 0);
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    addr.sin_port = htons(port);
    bind(listen_fd, (struct sockaddr*)&addr, sizeof(addr));
    listen(listen_fd, 1);
    conn_fd = accept(listen_fd, NULL, NULL);

    ctx = wolfSSL_CTX_new(wolfTLSv1_2_server_method());
    wolfSSL_CTX_use_certificate_file(ctx, CERTS_DIR "/server-cert.pem",
                                     WOLFSSL_FILETYPE_PEM);
    wolfSSL_CTX_use_PrivateKey_file(ctx, CERTS_DIR "/server-key.pem",
                                    WOLFSSL_FILETYPE_PEM);
    wolfSSL_CTX_SetDevId(ctx, DEV_ID);   /* handshake RNG -> Tempest */

    ssl = wolfSSL_new(ctx);
    wolfSSL_set_fd(ssl, conn_fd);
    ret = wolfSSL_accept(ssl);
    if (ret != WOLFSSL_SUCCESS) {
        printf("server: handshake FAILED (%d)\n", wolfSSL_get_error(ssl, ret));
        return 1;
    }
    wolfSSL_read(ssl, buf, sizeof(buf) - 1);
    buf[sizeof(buf) - 1] = '\0';
    wolfSSL_write(ssl, "pong", 4);
    printf("server: handshake OK, RNG requests serviced by Tempest: %d\n",
           rng_served);

    wolfSSL_free(ssl);
    wolfSSL_CTX_free(ctx);
    close(conn_fd);
    close(listen_fd);
    return 0;
}

static int run_client(int port)
{
    int sock_fd;
    struct sockaddr_in addr;
    char buf[16];
    int ret;
    WOLFSSL_CTX* ctx;
    WOLFSSL* ssl;

    sock_fd = socket(AF_INET, SOCK_STREAM, 0);
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    addr.sin_port = htons(port);
    if (connect(sock_fd, (struct sockaddr*)&addr, sizeof(addr)) != 0) {
        printf("client: connect failed\n");
        return 1;
    }

    ctx = wolfSSL_CTX_new(wolfTLSv1_2_client_method());
    wolfSSL_CTX_load_verify_locations(ctx, CERTS_DIR "/ca-cert.pem", NULL);
    wolfSSL_CTX_SetDevId(ctx, DEV_ID);   /* handshake RNG -> Tempest */

    ssl = wolfSSL_new(ctx);
    wolfSSL_set_fd(ssl, sock_fd);
    ret = wolfSSL_connect(ssl);
    if (ret != WOLFSSL_SUCCESS) {
        printf("client: handshake FAILED (%d)\n", wolfSSL_get_error(ssl, ret));
        return 1;
    }
    wolfSSL_write(ssl, "ping", 4);
    wolfSSL_read(ssl, buf, sizeof(buf));
    printf("client: handshake OK, server replied: %s, RNG served: %d\n",
           buf, rng_served);

    wolfSSL_free(ssl);
    wolfSSL_CTX_free(ctx);
    close(sock_fd);
    return 0;
}

int main(int argc, char** argv)
{
    int port = PORT_DEFAULT;
    int ret;

    if (argc < 2) {
        fprintf(stderr, "usage: %s [server|client] [port]\n", argv[0]);
        return 1;
    }
    if (argc > 2)
        port = atoi(argv[2]);

    ret = wolfSSL_Init();
    if (ret != WOLFSSL_SUCCESS)
        return 1;

    /* Register the counting wrapper on DEV_ID, seeding from wolfSSL's
     * own entropy-based RNG (production pattern). */
    ret = wc_CryptoCb_RegisterDevice(DEV_ID, TempestCryptoCbCount, NULL);
    if (ret != 0) {
        fprintf(stderr, "register failed: %d\n", ret);
        return 1;
    }
    ret = tempest_wolfssl_seed_from_wolfssl();
    if (ret != 0) {
        fprintf(stderr, "seeding failed: %d\n", ret);
        return 1;
    }

    if (strcmp(argv[1], "server") == 0)
        return run_server(port);
    return run_client(port);
}
