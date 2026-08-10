/* test_v3_self.c — 4-cmul Tempest v3 self-test
 * Tests: determinism, bit balance, key sensitivity, throughput */
#include "tempest_v3.h"
#include <stdio.h>
#include <stdlib.h>
#include <windows.h>
static double now_ms(){LARGE_INTEGER f,c;QueryPerformanceFrequency(&f);QueryPerformanceCounter(&c);return (double)c.QuadPart*1000.0/(double)f.QuadPart;}
static int popcnt(uint64_t x){return __builtin_popcountll(x);}
/* Seed-expansion helper (mirrors internal tx5cmul_seed logic) */
static void seed_expand(tempest_state *s, uint64_t seed){
    uint64_t k[4]={
        seed+0x9E3779B97F4A7C15ULL,
        ((seed<<17)|(seed>>47))*0x6A09E667F3BCC909ULL,
        seed^0x3243F6A8885A308DULL,
        ((seed<<32)|(seed>>32))+0xB7E151628AED2A6BULL
    };
    uint64_t n[2]={seed^0x9E3779B97F4A7C15ULL,~seed+0x6A09E667F3BCC908ULL};
    tempest_init(s,k,n);
}
int main(){
    tempest_state s,s2; uint64_t k[4]={1,2,3,4},n[2]={5,6};
    tempest_init(&s,k,n); tempest_init(&s2,k,n);
    int ok=1; for(int i=0;i<500;i++) if(tempest_u64(&s)!=tempest_u64(&s2)){ok=0;break;}
    printf("Determinism: %s\n",ok?"PASS":"FAIL");
    seed_expand(&s,42); int64_t ones=0,N=5000000;
    for(int64_t i=0;i<N/64;i++) ones+=popcnt(tempest_u64(&s));
    double pct=(double)ones/N*100;
    printf("Bit balance: %.2f%% %s\n",pct,(pct>49.5&&pct<50.5)?"PASS":"FAIL");
    uint64_t k2[4]={1,2,3,5}; tempest_init(&s,k,n); tempest_init(&s2,k2,n);
    int d=0; for(int i=0;i<1000;i++) d+=popcnt(tempest_u64(&s)^tempest_u64(&s2));
    double sens=(double)d/64000*100;
    printf("Key sens: %.2f%% %s\n",sens,(sens>40&&sens<60)?"PASS":"FAIL");
    seed_expand(&s,42); volatile uint64_t sink=0;
    double t0=now_ms(); int64_t rds=50000000;
    for(int64_t i=0;i<rds;i++) sink^=tempest_u64(&s);
    double el=now_ms()-t0; double rate=((double)rds*64.0/1e6)/(el/1000.0);
    printf("Throughput: %.0f Mbit/s (%.1f Gbit/s)\n",rate,rate/1000);
    printf("Original: 10109 Mbit/s (10.1 Gbit/s)\n");
    return 0;
}
