# IA Local

[English](#english) · [Manual español](app/MANUAL_ES.md) · [English guide](app/MANUAL_EN.md)

Un panel para gestionar tu entorno de IA: servidores locales, agentes, modelos y conexiones explícitas a APIs externas. Aprovecha tus instalaciones y conserva sus modelos y conversaciones. Nació para un Mac Apple Silicon; incluye un lanzador portable para Windows y Linux.

![Icono de IA Local](app/icon-192.png)

## Qué incluye

- Control individual y colectivo de servicios y agentes; salud real y procesos identificados.
- Catálogo compartido conservando las ubicaciones originales. Compatibilidad por formato y adaptador, sin conversiones automáticas.
- Comparativa por modelo, motor y contexto, junto a evaluación y optimización secuencial donde existe adaptador.
- Telemetría pasiva, inferencia en curso, última consulta y medias del día, semana, mes y total. Las conexiones directas fuera de la pasarela pueden no observarse.
- Integraciones locales revisadas, escaneo pasivo y asistente opcional mediante OpenCode/Hermes ya instalados. La IA propone configuración; tú revisas y guardas.
- Servidores LAN explícitos y APIs OpenAI, Anthropic, Kimi, DeepSeek, FreeLLMAPI y endpoints personalizados compatibles.
- Panel web HTTPS para la LAN, roles de usuario y segundo factor para administración. Safari/iPad utiliza ese mismo panel.
- Actualizaciones con fuentes oficiales, revisión y recuperación donde existe un adaptador. No garantiza que nunca haya versiones nuevas pendientes.
- Interfaz y ayuda en español e inglés. Instalación limpia, carpetas elegibles y restablecimiento recuperable de usuarios/preferencias.

## Plataformas y estado real

| Plataforma | Interfaz | Alcance |
|---|---|---|
| macOS 14+, Apple Silicon | App Swift/WKWebView y web | Instalador limpio compilado, instalado y probado en un Mac M4 Pro. Adaptadores de las instalaciones existentes; ayudante iogpu limitado y separado. |
| Windows x64 | Lanzador y navegador | Ejecutable generado y probado en Windows CI: instalación elegida, salud y panel Chromium headless. No contiene motores Metal ni ayudante macOS. |
| Linux x86_64 | Lanzador y navegador | Ejecutable generado y probado en Ubuntu 22.04 CI: instalación elegida, salud y panel Chromium headless. Requiere navegador/sesión gráfica para el panel. |

Consulta [VERIFICATION.md](docs/VERIFICATION.md) antes de interpretar una función como probada. Los binarios macOS llevan firma ad hoc, sin notarización Developer ID. Los paquetes Windows/Linux han pasado sus pruebas de sistema en CI; la inferencia GPU necesita el motor y hardware del usuario.

## Descargas

- [macOS Apple Silicon · instalador limpio](downloads/IA-Local-1.2.0-macOS-arm64.zip)
- [Windows x64 · ejecutable con Python incluido](https://github.com/sruizdeaguiar-svg/IA_Local/releases/download/v1.2.0/IA-Local-1.2.0-Windows-x64.zip)
- [Linux x86_64 · ejecutable con Python incluido](https://github.com/sruizdeaguiar-svg/IA_Local/releases/download/v1.2.0/IA-Local-1.2.0-Linux-x86_64.zip)
- [Windows · instalador desde código, requiere Python 3.12+](downloads/IA-Local-1.2.0-Windows-source.zip)
- [Linux · instalador desde código, requiere Python 3.12+](downloads/IA-Local-1.2.0-Linux-source.zip)

Los paquetes `source` son ediciones de código con entorno Python propio; no son ejecutables nativos ya probados. Sus instaladores descargan dependencias desde PyPI. Los ejecutables nativos incluyen Python y pasan [pruebas en sus respectivos sistemas](https://github.com/sruizdeaguiar-svg/IA_Local/actions/runs/39062732232). La [publicación 1.2.0](https://github.com/sruizdeaguiar-svg/IA_Local/releases/tag/v1.2.0) incluye las sumas SHA-256. Windows no tiene firma Authenticode.

## Instalación limpia en macOS

Descarga el archivo de `downloads/`, verifica su SHA-256, descomprime **Instalar IA Local.app** y ábrelo. Selecciona carpeta de aplicación y datos. No sustituye una aplicación existente ni una carpeta de datos con contenido. El paquete incluye Python y las dependencias del gestor; no incluye motores ni pesos.

Al abrirlo no hay instalaciones vinculadas, usuarios, claves ni catálogo personal. En **Integraciones**, escanea, vincula los adaptadores realmente encontrados o revisa una definición nueva. En **Configuración**, añade carpetas de modelos y busca modelos nuevos. Arrancar todos prepara los motores; no carga todos sus modelos a la vez. Cargar un modelo libera primero los pesos locales gestionados anteriores.

[Windows y Linux: instalación y compilación](docs/PORTABLE.md).

## Compatibilidad

La instalación macOS de referencia integra Strata Metal, llama.cpp, Mirai Uzu, Apple Foundation Models, oMLX, LM Studio, MLX-LM, Unsloth, EXO, vLLM Metal, OpenCode, Hermes y FreeLLMAPI, **solo si existen realmente**. Los adaptadores nativos conservan rutas configurables de esa instalación y no son instaladores universales. Windows/Linux admiten definiciones HTTP revisadas y conexiones LAN/API explícitas; añadir un nombre no crea una API de carga o actualización inexistente.

Los GGUF divididos se agrupan desde la primera parte completa; modelos MLX y Safetensors se distinguen. Un modelo listado, un proceso o un puerto abierto no prueban inferencia ni residencia. Los ajustes automáticos no miden calidad y los errores de memoria no producen velocidades válidas. Las pruebas sintéticas/funcionales registran condiciones y conservan resultados fallidos separados.

## Privacidad y límites

Los motores locales permanecen en loopback. El acceso LAN es optativo, autenticado y HTTPS; no abras sus puertos en Internet. Nube requiere selección explícita y puede tener coste. No hay sustitución automática de modelos locales por nube. Las claves se guardan en el directorio privado del usuario, no en este repositorio. No se incluyen cuentas, conversaciones ni modelos personales.

El ayudante GPU es exclusivo de macOS y solo ajusta `iogpu.wired_limit_mb`. Requiere autorización inicial del sistema. Aumentar ese techo no crea memoria física. [Modelo de seguridad](docs/SECURITY.md).

## Desarrollo y contribución

[Arquitectura](docs/ARCHITECTURE.md) · [Desarrollo y pruebas](docs/DEVELOPMENT.md) · [Referencia del código](docs/CODE_REFERENCE.md) · [Contribuir](CONTRIBUTING.md)

Licencia [Apache-2.0](LICENSE). Los motores, Python y las dependencias conservan sus propias licencias: [terceros](docs/THIRD_PARTY.md).

## English

IA Local manages existing local AI services, HTTP agents, models and explicit LAN/cloud API connections through one shared panel. It preserves existing programs, model locations and conversations. The macOS application has a clean graphical installer and a separate fixed-purpose GPU helper. Windows/Linux portable launchers reuse the backend and browser UI; Apple-only adapters are unavailable there. See the platform table and [verification report](docs/VERIFICATION.md) for actual runtime evidence and outstanding checks.

Select a model and engine, confirm context, then load. Start all never loads every local model simultaneously or enables cloud connections. Passive request statistics are separate from active benchmarks. Compatible engines are tested sequentially with recorded versions/parameters; failed trials are not performance results. Reviewed integrations, model folders, external providers, bilingual help and a reversible full reset are available under Settings.

Installers contain no personal credentials, users, model weights or conversations. Inference stays on loopback unless you explicitly enable the authenticated private-LAN gateway. Cloud usage is opt-in and may incur charges. Read the [English guide](app/MANUAL_EN.md), [portable instructions](docs/PORTABLE.md) and [security model](docs/SECURITY.md).
