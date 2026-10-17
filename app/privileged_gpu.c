// Root service: one fixed sysctl, one local UID, no shell or network listener.
#include <sys/types.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/sysctl.h>
#include <sys/wait.h>
#include <launch.h>
#include <mach-o/dyld.h>
#include <poll.h>
#include <spawn.h>
#include <fcntl.h>
#include <unistd.h>
#include <signal.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <syslog.h>
static uid_t owner_uid=0;
#define TARGET "/Library/PrivilegedHelperTools/local.ia-local.gpu"
#define PLIST "/Library/LaunchDaemons/local.ia-local.gpu.plist"
#define SERVICE "system/local.ia-local.gpu"
#define VERSION 2
static int control(const char *verb,const char *target){
    char *args[]={"/bin/launchctl",(char*)verb,(char*)target,NULL,NULL};
    if(!strcmp(verb,"bootstrap")){args[2]="system";args[3]=(char*)target;}
    char *env[]={"PATH=/usr/bin:/bin:/usr/sbin:/sbin",NULL};pid_t p;
    posix_spawn_file_actions_t a;posix_spawn_file_actions_init(&a);
    posix_spawn_file_actions_addopen(&a,1,"/dev/null",O_WRONLY,0);posix_spawn_file_actions_adddup2(&a,1,2);
    int e=posix_spawn(&p,args[0],&a,NULL,args,env);posix_spawn_file_actions_destroy(&a);int s=0;
    if(e||waitpid(p,&s,0)<0)return 1;return WIFEXITED(s)?WEXITSTATUS(s):1;
}
static int secure_dir(const char *p){struct stat s;if(lstat(p,&s)&&mkdir(p,0755))return -1;if(lstat(p,&s)||!S_ISDIR(s.st_mode)||s.st_uid||s.st_mode&022)return -1;return 0;}
static int install(void){
    if(secure_dir("/Library/PrivilegedHelperTools")||secure_dir("/Library/LaunchDaemons"))return 10;
    char path[4096];uint32_t n=sizeof(path);if(_NSGetExecutablePath(path,&n))return 11;
    int in=open(path,O_RDONLY|O_NOFOLLOW);struct stat st;if(in<0||fstat(in,&st)||!S_ISREG(st.st_mode)||st.st_uid<501)return 12;
    owner_uid=st.st_uid; // Bind this installation to the authenticated helper binary owner.
    char tmp[256];snprintf(tmp,sizeof(tmp),TARGET ".%d.tmp",getpid());
    int out=open(tmp,O_CREAT|O_EXCL|O_WRONLY|O_NOFOLLOW,0700);if(out<0){close(in);return 13;}
    char b[65536];ssize_t r;int bad=0;while((r=read(in,b,sizeof(b)))>0){ssize_t w=0;while(w<r){ssize_t k=write(out,b+w,r-w);if(k<=0){bad=1;break;}w+=k;}if(bad)break;}
    if(r<0||fchown(out,0,0)||fchmod(out,0755)||fsync(out))bad=1;close(in);close(out);
    if(bad){unlink(tmp);return 14;}
    control("bootout",SERVICE);if(rename(tmp,TARGET)){unlink(tmp);return 15;}
    snprintf(tmp,sizeof(tmp),PLIST ".%d.tmp",getpid());out=open(tmp,O_CREAT|O_EXCL|O_WRONLY|O_NOFOLLOW,0600);if(out<0)return 16;
    dprintf(out,"<?xml version=\"1.0\" encoding=\"UTF-8\"?><!DOCTYPE plist PUBLIC \"-//Apple//DTD PLIST 1.0//EN\" \"http://www.apple.com/DTDs/PropertyList-1.0.dtd\"><plist version=\"1.0\"><dict><key>Label</key><string>local.ia-local.gpu</string><key>ProgramArguments</key><array><string>" TARGET "</string><string>serve</string><string>%d</string></array><key>Sockets</key><dict><key>control</key><dict><key>SockFamily</key><string>Unix</string><key>SockType</key><string>stream</string><key>SockPathName</key><string>/var/run/local.ia-local.gpu-%d.sock</string><key>SockPathOwner</key><integer>%d</integer><key>SockPathMode</key><integer>384</integer></dict></dict><key>ProcessType</key><string>Background</string><key>ExitTimeOut</key><integer>5</integer></dict></plist>",owner_uid,owner_uid,owner_uid);
    bad=fchown(out,0,0)||fchmod(out,0644)||fsync(out);close(out);if(bad||rename(tmp,PLIST)){unlink(tmp);return 17;}
    return control("bootstrap",PLIST)?18:0;
}
static void request(int fd){
    uid_t uid;gid_t gid;if(getpeereid(fd,&uid,&gid)||uid!=owner_uid)return;
    struct timeval timeout={3,0};setsockopt(fd,SOL_SOCKET,SO_RCVTIMEO,&timeout,sizeof(timeout));setsockopt(fd,SOL_SOCKET,SO_SNDTIMEO,&timeout,sizeof(timeout));
    char b[65]={0};size_t n=0;while(n<sizeof(b)-1){ssize_t k=read(fd,b+n,1);if(k!=1)return;if(b[n++]=='\n')break;}
    if(!n||b[n-1]!='\n')return;b[n-1]=0;
    uint64_t before=0,after=0,mem=0;size_t size=sizeof(before),ms=sizeof(mem);
    if(sysctlbyname("iogpu.wired_limit_mb",&before,&size,0,0)||(size!=4&&size!=8)||sysctlbyname("hw.memsize",&mem,&ms,0,0)){dprintf(fd,"{\"error\":\"Clave GPU no disponible.\"}\n");return;}
    if(!strcmp(b,"GET")){dprintf(fd,"{\"version\":%d,\"current\":%llu,\"max\":%llu,\"owner\":%d}\n",VERSION,(unsigned long long)before,(unsigned long long)(mem/1048576-2048),owner_uid);return;}
    if(strncmp(b,"SET ",4)||!b[4]){dprintf(fd,"{\"error\":\"Operación no permitida.\"}\n");return;}
    for(size_t i=4;i<n-1;i++)if(b[i]<'0'||b[i]>'9'){dprintf(fd,"{\"error\":\"Valor no válido.\"}\n");return;}
    errno=0;char *end;uint64_t target=strtoull(b+4,&end,10);
    if(errno||*end||(target&&(target<1024||target>mem/1048576-2048))){dprintf(fd,"{\"error\":\"Valor fuera de intervalo.\"}\n");return;}
    if(sysctlbyname("iogpu.wired_limit_mb",NULL,NULL,&target,size)){dprintf(fd,"{\"error\":\"macOS rechazó el cambio.\"}\n");return;}
    size_t as=sizeof(after);if(sysctlbyname("iogpu.wired_limit_mb",&after,&as,0,0)||after!=target){dprintf(fd,"{\"error\":\"Cambio no confirmado.\"}\n");return;}
    syslog(LOG_NOTICE,"IA Local GPU uid=%d previous=%llu applied=%llu",uid,(unsigned long long)before,(unsigned long long)after);
    dprintf(fd,"{\"previous\":%llu,\"applied\":%llu}\n",(unsigned long long)before,(unsigned long long)after);
}
int main(int argc,char **argv){
    if(geteuid()||argc<2||argc>3)return 1;umask(077);signal(SIGPIPE,SIG_IGN);
    if(!strcmp(argv[1],"install")){int r=install();if(r)printf("{\"error\":\"Instalación no completada (código %d).\"}\n",r);else puts("{\"installed\":true}");return r;}
    if(!strcmp(argv[1],"uninstall")){unlink(PLIST);unlink(TARGET);puts("{\"removed\":true}");fflush(stdout);return control("bootout",SERVICE);}
    if(strcmp(argv[1],"serve")||argc!=3)return 2;
    char *end=NULL;unsigned long parsed=strtoul(argv[2],&end,10);if(!end||*end||parsed<501||parsed>INT32_MAX)return 2;owner_uid=(uid_t)parsed;
    int *fds=NULL;size_t count=0;if(launch_activate_socket("control",&fds,&count)||count!=1)return 3;
    struct pollfd p={fds[0],POLLIN,0};while(poll(&p,1,30000)>0){int fd=accept(fds[0],NULL,NULL);if(fd>=0){request(fd);close(fd);}}
    close(fds[0]);free(fds);return 0;
}
