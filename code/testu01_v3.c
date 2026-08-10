/* testu01_v3.c — Full TestU01 test harness for 4-cmul Tempest v3 */
#include "tempest_v3.h"
#include "unif01.h"
#include "bbattery.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static tx4_state st;
static double gU01(void*p,void*x){(void)p;(void)x;return (double)(uint32_t)(tx5cmul_next(&st)>>32)*2.3283064365386963E-10;}
static unsigned long gBits(void*p,void*x){(void)p;(void)x;return (unsigned long)(uint32_t)(tx5cmul_next(&st)>>32);}
static void gW(void*j){(void)j;printf(" 4-cmul Tempest v3\\n");}
int main(int ac,char**av){
    uint64_t k[4]={1,2,3,4},n[2]={5,6};
    tx5cmul_init(&st,k,n);
    unif01_Gen*g=malloc(sizeof(unif01_Gen));
    g->name="4-cmul Tempest v3";g->GetU01=&gU01;g->GetBits=&gBits;g->Write=&gW;g->param=NULL;g->state=NULL;
    const char*b=ac>1?av[1]:"small";
    if(!strcmp(b,"small")){printf("=== TestU01 SmallCrush ===\n");bbattery_SmallCrush(g);}
    else if(!strcmp(b,"rabbit")){printf("=== TestU01 Rabbit ===\n");bbattery_Rabbit(g,100000000.0);}
    else if(!strcmp(b,"alphabit")){printf("=== TestU01 Alphabit ===\n");bbattery_Alphabit(g,100000000.0,0,32);}
    else if(!strcmp(b,"bigcrush")){printf("=== TestU01 BigCrush ===\n");bbattery_BigCrush(g);}
    else if(!strcmp(b,"crush")){printf("=== TestU01 Crush ===\n");bbattery_Crush(g);}
    else{printf("Usage: %s [small|rabbit|alphabit|bigcrush|crush]\n",av[0]);}
    free(g);return 0;
}
