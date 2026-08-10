/* testu01_adcbolt.c — TestU01 harness for ADC-Bolt (all 5 levels) */
#include "bolt_v3.h"
#include "unif01.h"
#include "bbattery.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static bolt3_state st;

static double gU01(void *p, void *x) {
    (void)p; (void)x;
    return (double)(uint32_t)(adcbolt_next(&st) >> 32) * 2.3283064365386963E-10;
}

static unsigned long gBits(void *p, void *x) {
    (void)p; (void)x;
    return (unsigned long)(uint32_t)(adcbolt_next(&st) >> 32);
}

static void gW(void *j) {
    (void)j;
    printf(" ADC-Bolt\n");
}

int main(int ac, char **av) {
    adcbolt_seed(&st, 42);
    unif01_Gen *g = malloc(sizeof(unif01_Gen));
    g->name = "ADC-Bolt";
    g->GetU01 = &gU01;
    g->GetBits = &gBits;
    g->Write = &gW;
    g->param = NULL;
    g->state = NULL;

    const char *b = ac > 1 ? av[1] : "small";

    if (!strcmp(b, "small")) {
        printf("=== ADC-Bolt SmallCrush ===\n");
        bbattery_SmallCrush(g);
    } else if (!strcmp(b, "rabbit")) {
        printf("=== ADC-Bolt Rabbit ===\n");
        bbattery_Rabbit(g, 100000000.0);
    } else if (!strcmp(b, "alphabit")) {
        printf("=== ADC-Bolt Alphabit ===\n");
        bbattery_Alphabit(g, 100000000.0, 0, 32);
    } else if (!strcmp(b, "crush")) {
        printf("=== ADC-Bolt Crush ===\n");
        bbattery_Crush(g);
    } else if (!strcmp(b, "bigcrush")) {
        printf("=== ADC-Bolt BigCrush ===\n");
        bbattery_BigCrush(g);
    } else {
        printf("Usage: %s [small|rabbit|alphabit|crush|bigcrush]\n", av[0]);
    }

    free(g);
    return 0;
}
