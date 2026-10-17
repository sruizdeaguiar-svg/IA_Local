IA Local reúne servidores de IA, agentes y modelos en un panel común para escritorio y navegador. Incluye configuración e idioma ES/EN, integraciones revisadas, catálogo sin duplicar pesos, evaluación secuencial, métricas de inferencia, conexiones LAN/API explícitas y restablecimiento recuperable.

- **macOS Apple Silicon:** instalador limpio con icono, selección de carpetas y Python incluido. Compilado e instalado en el Mac de referencia; firma ad hoc, sin notarización Developer ID.
- **Windows x64 y Linux x86_64:** ejecutables con Python incluido, generados en sus respectivos sistemas. Pruebas de núcleo, salud real del ejecutable, importaciones tardías y panel Chromium headless antes de publicar. Instalación por usuario, sin elevación ni motores/modelos incluidos.
- **Seguridad:** procesos e hijos identificados, puertos separados, loopback, acceso LAN HTTPS con roles/segundo factor, claves fuera del navegador y del repositorio. Windows usa DACL privada y el ajuste iogpu permanece exclusivo de macOS.

Las pruebas de interfaz usan un agente HTTP sintético; no sustituyen pruebas de inferencia con cada GPU, motor o modelo. Windows/Linux no incorporan adaptadores nativos de Apple ni drivers CUDA/ROCm. iPad utiliza el panel web; esta versión no es una app iPadOS nativa. Las APIs externas requieren claves y permisos propios; nube nunca se activa como alternativa automática.

Descarga el paquete de tu sistema y verifica SHA256SUMS.txt. Los binarios Windows son unsigned y los macOS no están notarizados. Conserva las protecciones del sistema y verifica la procedencia. Consulta los manuales ES/EN, el informe de verificación y las licencias de terceros del repositorio.

English: one shared local-AI control panel, clean installers, Spanish/English guides, reviewed integrations, explicit LAN/cloud connections and recoverable settings. Native Windows/Linux packages are built and tested on their target OS with isolated HTTP/browser fixtures. No model weights, engines, credentials or GPU drivers are bundled. Apple-only features remain macOS-only. See the repository's verification/security documentation for scope and limits. Apache-2.0.
