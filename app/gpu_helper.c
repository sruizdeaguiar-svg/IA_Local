#include <sys/types.h>
#include <sys/sysctl.h>
#include <unistd.h>
#include <stdint.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
// One-shot privileged helper. No shell, paths, commands, or arbitrary sysctl keys accepted.
int main(int argc,char **argv) {
    if(argc!=2 || geteuid()!=0){puts("{\"error\":\"Se necesita autorización de macOS.\"}");return 1;}
    char *end=0;errno=0;long long proposed=strtoll(argv[1],&end,10);
    uint64_t memory=0;size_t length=sizeof(memory);
    if(sysctlbyname("hw.memsize",&memory,&length,0,0)!=0)return 2;
    if(errno || !end || *end || proposed<0 || (proposed!=0 && (proposed<1024 || proposed>(long long)(memory/1048576)-2048))){puts("{\"error\":\"Valor fuera del intervalo permitido.\"}");return 3;}
    uint64_t before=0,after=0;size_t size=sizeof(before);
    const char *key="iogpu.wired_limit_mb";
    if(sysctlbyname(key,&before,&size,0,0)!=0 || (size!=4 && size!=8)){puts("{\"error\":\"La clave no está disponible en este sistema.\"}");return 4;}
    uint64_t target=(uint64_t)proposed;
    if(sysctlbyname(key,0,0,&target,size)!=0){puts("{\"error\":\"macOS rechazó el cambio.\"}");return 5;}
    size_t actual_size=sizeof(after);
    if(sysctlbyname(key,&after,&actual_size,0,0)!=0 || after!=target){puts("{\"error\":\"No se confirmó el valor aplicado.\"}");return 6;}
    printf("{\"previous\":%llu,\"applied\":%llu}\n",(unsigned long long)before,(unsigned long long)after);return 0;
}
