// W=4 RX-differential spectrum WITH K constants (full quadratic shadow)
#include <stdio.h>
#include <string.h>
#include <math.h>

#define W 4
#define MASK ((1u<<W)-1)
static unsigned rot(unsigned x, int r) { r &= (W-1); return ((x<<r)|(x>>(W-r)))&MASK; }

static const unsigned KU=0x9, KV=0xA, KW=0x7, KZ=0xC;  /* low 4 bits of K_U..K_Z */

static void F(unsigned s[4], unsigned out[4]) {
    unsigned u=s[0], v=s[1], w=s[2], z=s[3];
    unsigned a_u = u ^ rot(v,1) ^ rot(w,1) ^ (rot(v,1) & rot(z,1)) ^ KU;
    unsigned a_v = v ^ rot(w,3) ^ rot(z,3) ^ (rot(w,3) & rot(u,1)) ^ KV;
    unsigned a_w = w ^ rot(z,1) ^ rot(u,3) ^ (rot(u,1) & rot(v,3)) ^ KW;
    unsigned a_z = z ^ rot(u,1) ^ rot(v,3) ^ (rot(v,3) & rot(w,1)) ^ KZ;
    a_u = a_u ^ (rot(z,3) & rot(w,1));   /* A(lin) */
    a_z = a_z ^ (rot(u,1) & rot(z,1));   /* A(lin) */
    out[0] = a_u ^ rot(a_v,3) ^ rot(a_w,1);
    out[1] = a_v ^ rot(a_w,1) ^ rot(a_z,3);
    out[2] = a_w ^ rot(a_z,1) ^ rot(a_u,1);
    out[3] = a_z ^ rot(a_u,3) ^ rot(a_v,1);
}

static unsigned short Ftab[65536][4];
static void g_stats(unsigned delta[4], double *maxp, double *nzcount) {
    static long cnt[65536];
    memset(cnt, 0, sizeof(cnt));
    unsigned i;
    for (i = 0; i < 65536; i++) {
        unsigned u = i&MASK, v=(i>>4)&MASK, w=(i>>8)&MASK, z=(i>>12)&MASK;
        unsigned ru=rot(u,1), rv=rot(v,1), rw=rot(w,1), rz=rot(z,1);
        unsigned xi = (ru^delta[0]) | ((rv^delta[1])<<4) | ((rw^delta[2])<<8) | ((rz^delta[3])<<12);
        unsigned f0=Ftab[i][0], f1=Ftab[i][1], f2=Ftab[i][2], f3=Ftab[i][3];
        unsigned g0=Ftab[xi][0]^rot(f0,1), g1=Ftab[xi][1]^rot(f1,1), g2=Ftab[xi][2]^rot(f2,1), g3=Ftab[xi][3]^rot(f3,1);
        cnt[g0 | (g1<<4) | (g2<<8) | (g3<<12)]++;
    }
    double mx=0; long nz=0;
    for (i=0;i<65536;i++) if (cnt[i]) { nz++; if (cnt[i]>mx) mx=cnt[i]; }
    *maxp = mx/65536.0; *nzcount = nz;
}

int main(void) {
    unsigned i, u, v, w, z;
    for (i=0;i<65536;i++) {
        unsigned s[4] = { i&MASK, (i>>4)&MASK, (i>>8)&MASK, (i>>12)&MASK };
        unsigned o[4]; F(s,o);
        Ftab[i][0]=o[0]; Ftab[i][1]=o[1]; Ftab[i][2]=o[2]; Ftab[i][3]=o[3];
    }
    double best=0, worst=1;
    unsigned bd[4]={0}, wd[4]={0};
    double hist[20]; memset(hist,0,sizeof(hist));
    long total=0, ones=0;
    for (u=0;u<16;u++) for (v=0;v<16;v++) for (w=0;w<16;w++) for (z=0;z<16;z++) {
        if (!u&&!v&&!w&&!z) continue;
        unsigned d[4]={u,v,w,z};
        double mx, nz; g_stats(d,&mx,&nz);
        total++;
        if (mx>best){best=mx; bd[0]=u;bd[1]=v;bd[2]=w;bd[3]=z;}
        if (mx<worst){worst=mx; wd[0]=u;wd[1]=v;wd[2]=w;wd[3]=z;}
        double e=-log(mx)/log(2.0); int ei=(int)(e+0.5);
        if (ei>=0&&ei<20) hist[ei]++;
        if (mx>=0.5) ones++;
    }
    printf("W=4 RX spectrum WITH K constants: %ld deltas, %ld with RX-DP >= 1/2\n", total, ones);
    printf("max RX-DP: 2^-%.1f at delta=(%u,%u,%u,%u)\n", -log(best)/log(2.0), bd[0],bd[1],bd[2],bd[3]);
    printf("min RX-DP: 2^-%.1f at delta=(%u,%u,%u,%u)\n", -log(worst)/log(2.0), wd[0],wd[1],wd[2],wd[3]);
    for (i=0;i<20;i++) if (hist[i]) printf("  2^-%u: %ld\n", i, (long)hist[i]);
    return 0;
}
