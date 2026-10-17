#include <Security/Authorization.h>
#include <Security/AuthorizationTags.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
// Authorization is requested for every application/restore operation; no password is read by this app.
// macOS still supplies this one-shot API. Kept separate for migration to SMAppService.
char *ia_authorized_gpu(const char *helper,int mb) {
    AuthorizationRef auth=0;OSStatus s=AuthorizationCreate(NULL,kAuthorizationEmptyEnvironment,kAuthorizationFlagDefaults,&auth);
    if(s!=errAuthorizationSuccess)return strdup("{\"error\":\"No se pudo iniciar la autorización.\"}");
    AuthorizationItem item={kAuthorizationRightExecute,0,NULL,0};AuthorizationRights rights={1,&item};
    s=AuthorizationCopyRights(auth,&rights,kAuthorizationEmptyEnvironment,kAuthorizationFlagInteractionAllowed|kAuthorizationFlagExtendRights,NULL);
    if(s!=errAuthorizationSuccess){AuthorizationFree(auth,kAuthorizationFlagDestroyRights);return strdup("{\"error\":\"Autorización cancelada o denegada; no se cambió el límite.\"}");}
    char value[32];snprintf(value,sizeof(value),"%d",mb);char *args[]={value,NULL};FILE *pipe=NULL;
    s=AuthorizationExecuteWithPrivileges(auth,helper,kAuthorizationFlagDefaults,args,&pipe);
    char buffer[1024]={0};
    if(s==errAuthorizationSuccess && pipe){fgets(buffer,sizeof(buffer),pipe);fclose(pipe);}
    AuthorizationFree(auth,kAuthorizationFlagDestroyRights);
    return strdup(buffer[0]?buffer:"{\"error\":\"macOS no pudo ejecutar el helper autorizado.\"}");
}
// Only the app's bundled, fixed-purpose installer is passed by native Swift.
char *ia_authorized_install(const char *helper) {
    AuthorizationRef auth=0;OSStatus s=AuthorizationCreate(NULL,kAuthorizationEmptyEnvironment,kAuthorizationFlagDefaults,&auth);
    if(s!=errAuthorizationSuccess)return strdup("{\"error\":\"No se pudo iniciar la autorización.\"}");
    AuthorizationItem item={kAuthorizationRightExecute,0,NULL,0};AuthorizationRights rights={1,&item};
    s=AuthorizationCopyRights(auth,&rights,kAuthorizationEmptyEnvironment,kAuthorizationFlagInteractionAllowed|kAuthorizationFlagExtendRights,NULL);
    FILE *pipe=NULL;char buffer[1024]={0};char *args[]={"install",NULL};
    if(s==errAuthorizationSuccess)s=AuthorizationExecuteWithPrivileges(auth,helper,kAuthorizationFlagDefaults,args,&pipe);
    if(s==errAuthorizationSuccess&&pipe){fgets(buffer,sizeof(buffer),pipe);fclose(pipe);}
    AuthorizationFree(auth,kAuthorizationFlagDestroyRights);
    return strdup(buffer[0]?buffer:"{\"error\":\"Instalación cancelada o no autorizada.\"}");
}
