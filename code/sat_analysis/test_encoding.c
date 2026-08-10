#include <stdio.h>
#include <stdint.h>

static uint64_t rotl(uint64_t x, int r) { return (x<<r)|(x>>(64-r)); }
int main() {
    uint64_t t = 1;
    t ^= rotl(t,31)&rotl(t,53);
    t ^= rotl(t,17)&rotl(t,43);
    t ^= rotl(t,7)&rotl(t,23);
    t ^= rotl(t,5)&rotl(t,19);
    printf("andmix4(1) = %016llx\n", (unsigned long long)t);
    return 0;
}
