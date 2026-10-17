# Manual de IA Local

## Primer inicio y configuración

Abre IA Local y espera a «Supervisor conectado». En Configuración elige idioma, apariencia, frecuencia de telemetría, escaneo y actualizaciones. Guardar aplica preferencias compartidas a escritorio y web. La instalación limpia empieza sin cuentas, claves, modelos registrados ni acceso LAN. Si falta un motor, utiliza Integraciones; la app no descarga pesos automáticamente.

## Control y estados

Cada tarjeta distingue proceso, salud y modelo. Arrancar prepara el servicio; Cargar seleccionado puede reservar memoria e inferir una comprobación. Detener solo finaliza el proceso identificado y gestionado. Arrancar todos deja en espera los motores que requieren pesos. Recuperar memoria descarga modelos locales y libera sus motores; los agentes y las cachés de macOS pueden seguir usando RAM. Los botones solo se habilitan cuando existe una operación válida.

## Modelos y contexto

Autoriza la carpeta del SSD desde el Mac y pulsa Buscar modelos nuevos. GGUF, MLX y otros formatos conservan sus ubicaciones; no hay conversiones universales. Elige modelo, motor compatible y contexto; Guarda contexto antes de cargar. La tabla se actualiza al cambiar la selección. Un modelo listado no demuestra que esté cargado. Los formatos declarados para integraciones nuevas necesitan una prueba real. Los modelos remotos se identifican por su servidor y no se descargan al Mac.

## Hermes y OpenCode

Arranca el agente y usa Abrir web cuando su interfaz esté disponible. Carga primero un modelo y pulsa Usar modelo activo en su tarjeta o en ambos. Se transfieren servidor, modelo y contexto para nuevas sesiones y se guardan copias. Hermes exige 64000 tokens como mínimo. OpenAI y otros proveedores existentes se conservan; la pasarela local no activa proveedores de nube. Las pruebas de asistentes usan perfiles aislados y no modifican los tuyos.

## Añadir instalaciones con IA

En Integraciones pulsa Escanear instalaciones o activa el escaneo automático. Detectado no equivale a compatible ni arrancado. Selecciona Configurar o introduce nombre, tipo, ejecutable y puerto libre. Prepara una plantilla, carga un modelo local y elige OpenCode o Hermes para proponer argumentos a partir de --help. Revisa el JSON y guarda expresamente. Nunca se ejecuta una orden propuesta por el modelo sin esa revisión. Un agente solo de terminal necesita un adaptador HTTP; la IA no crea compatibilidad inexistente.

## Servidores en otros ordenadores de la LAN

Añade nombre, URL privada terminada en /v1, contexto confirmado y clave opcional. Solo se aceptan IP de redes privadas conectadas al Mac; una nueva red puede exigir editar la dirección. Se rechazan Internet y redirecciones. HTTPS exige certificado válido; HTTP con clave requiere aceptación explícita. Guardar no conecta. Conectar consulta /models y añade el inventario; selecciona un modelo y prueba respuesta y streaming. Desconectar impide su uso desde IA Local y conserva el proceso remoto. No administra por SSH, ni garantiza descarga remota de pesos o actualización del otro ordenador.

## Evaluación y optimización

La telemetría es pasiva; Evaluar consume recursos. Cierra otras cargas antes de probar. Llama usa calentamiento, pp512/tg128 y tres repeticiones; los demás motores usan aritmética, español, streaming y generaciones sintéticas. Evaluar todos recorre motores compatibles secuencialmente y libera memoria local. Optimizar todos busca parámetros solo donde hay adaptador; el resto se evalúa sin ajuste. Compara solo mismo modelo, cuantización, contexto, versión y método. Errores de memoria no son velocidades válidas. Velocidad no mide calidad. En LAN la latencia incluye red y no se conoce la memoria física remota.

## Estadísticas

Control muestra CPU, GPU, RAM, generación en curso, última inferencia y medias del día, semana, mes y total. Tokens y fragmentos de streaming no son equivalentes. Los campos sin medición quedan vacíos; no se inventan cifras. La pasarela observa sus propias consultas y conserva métricas agregadas. Las conexiones directas pueden quedar fuera; la cobertura se indica en pantalla.

## Límite GPU y permisos

Lee el valor actual antes de cambiarlo. Descarga modelos, selecciona el límite y aplica. El ayudante se instala una vez con autorización de macOS y solo permite leer o ajustar iogpu.wired_limit_mb. Restaurar usa el valor anterior verificado. Aumentar el techo no crea RAM; puede dejar poco margen al sistema. Desde web se exige administración y segundo factor, sin enviar la contraseña de macOS. El instalador limpio no instala el ayudante automáticamente.

## Acceso web, usuarios y seguridad

En Red y usuarios crea una cuenta y activa LAN. Instala y verifica el certificado público en cada dispositivo. Configura segundo factor en el Mac para operaciones administrativas remotas. Administración gestiona usuarios e instalaciones; Control gestiona servicios y conversaciones; Lectura consulta el panel. Las claves remotas permanecen en archivos privados 0600 dentro del directorio 0700; no se exportan. No publiques los puertos en Internet. Escritorio y web comparten el mismo panel; iPad usa Safari.

## Actualizaciones y recuperación

Consulta versiones oficiales, revisa alcance y pulsa Actualizar con el componente detenido. Se guarda copia antes de cambios compatibles con recuperación. Recuperar versión restaura la copia disponible. Un fallo de red deja el estado desconocido. No existe garantía de estar siempre actualizado. Integraciones nuevas y servidores remotos requieren su propio adaptador de actualización; no se ejecutan instaladores inventados por IA.

## Instalación limpia y solución de problemas

Instalar IA Local permite elegir carpeta de aplicación y de datos o usar las de tu usuario. El paquete no incluye claves, usuarios, modelos ni conversaciones. Detecta requisitos de Python y muestra los que falten antes de instalar. Solo una instancia del supervisor puede usar el puerto 8040; no sustituye otra instalación activa. Si un servicio falla, abre Actividad y revisa su registro acotado. Puerto ocupado conserva el proceso ajeno. Modelo sin respuesta requiere revisar formato, arquitectura, contexto y memoria. Los textos de registros y respuestas se conservan en su idioma original.

## APIs externas y FreeLLMAPI

En APIs externas elige OpenAI, Anthropic, Kimi, DeepSeek, FreeLLMAPI o Personalizado. Indica protocolo, URL, puerto exclusivo del adaptador, contexto confirmado, IDs opcionales y tu clave. Guardar deja la conexión desactivada. Conectar consulta modelos; si el proveedor no ofrece inventario, declara los IDs y verifica una generación. Importar FreeLLMAPI reutiliza su clave local sin mostrarla y conserva los perfiles actuales. Debes arrancar su servicio y configurar las claves de nube en su propio panel. Los protocolos OpenAI Chat Completions y Anthropic Messages son distintos; el adaptador no implementa todas sus extensiones. Las conversaciones y archivos que envíes pueden salir del Mac y generar costes. Arrancar todos y el asistente local no activan nube. Para evaluar o transferir un modelo externo debes seleccionarlo expresamente. Las cuentas sin saldo o permisos pueden listar modelos y fallar al generar.

## Restablecer y recuperar

En Configuración, Restablecer aplicación completa requiere escribir RESTABLECER. Se guarda una copia privada, se desvinculan instalaciones y se reinician usuarios y preferencias. Programas, modelos y conversaciones se conservan. Recuperar último restablecimiento restaura la configuración con servicios y LAN detenidos. Resincroniza agentes si utilizaban el token anterior.

## Windows y Linux

El lanzador portable abre el panel en el navegador. Añade ejecutables en Integraciones y carpetas de modelos en Configuración. No incluye motores ni modelos. Los adaptadores macOS y el ajuste iogpu no están disponibles en estos sistemas.
