# IA Local · Windows / Linux

ES: gestor por usuario para servidores de IA, agentes HTTP, modelos y conexiones explícitas LAN/nube. Usa el mismo panel que macOS. No incluye motores, pesos ni configuración personal. EN: per-user AI manager sharing the macOS panel; no engines, model weights or personal configuration bundled.

Native executable builds and installed-panel checks passed on Windows x64 and Ubuntu 22.04 x86_64: [CI evidence](https://github.com/sruizdeaguiar-svg/IA_Local/actions/runs/39062732232). These are isolated HTTP/browser fixtures, not GPU model inference.

## Source editions / Ediciones de código

`IA-Local-1.2.0-Windows-source.zip` and `IA-Local-1.2.0-Linux-source.zip` are clean source installers, not EXE/native binaries. They require Python 3.12+ already installed and Internet access to install Python dependencies from official PyPI into their own virtualenv. No engine or model is downloaded. Windows: run `./Instalar.ps1 -Destination "D:\Apps\IA Local" -DataDirectory "D:\IA Local Data"`. Linux: `sh instalar.sh "$HOME/.local/opt/ia-local" "$HOME/.local/share/IA-Local"`. The scripts preserve existing directories and create a per-user shortcut. The separate native executable/installer/browser workflow is verified on target-OS CI; the complete source-edition dependency-download installation has not been separately run.

## Windows 11 x64

Descomprime el ZIP y abre **IA-Local.exe**, o instala sin administrador:

```powershell
.\Install.ps1 -Destination "$env:LOCALAPPDATA\Programs\IA Local" -DesktopShortcut
# Optional selected data directory:
.\Install.ps1 -Destination "D:\Apps\IA Local" -DataDirectory "D:\IA Local Data" -DesktopShortcut
```

El ejecutable no está firmado con Authenticode. No desactives protecciones del sistema; verifica la procedencia y el SHA-256 antes de utilizarlo. English: unsigned executable; verify origin and SHA-256. Default data: `%LOCALAPPDATA%\IA-Local`, protected with a per-user NTFS ACL. Use NTFS storage supporting ACLs for credentials.

## Linux x86_64

Descomprime, permite la ejecución e instala en tu usuario o una carpeta elegida:

```sh
chmod +x IA-Local
sh install.sh "$HOME/.local/opt/ia-local"
"$HOME/.local/opt/ia-local/IA-Local" --data "$HOME/.local/share/IA-Local"
```

Default data: `${XDG_DATA_HOME:-~/.local/share}/IA-Local`, mode 0700. A desktop entry is created under `~/.local/share/applications`. Build on Ubuntu 22.04 or newer; an older glibc system may need a local build. A default browser and graphical session are required for the panel. The supervisor can run headlessly with `--serve`.

## First run / Primer inicio

The launcher starts only its loopback supervisor on 127.0.0.1:8040 and opens a one-use owner session in your default browser. Do not copy/share that private URL. Closing a tab does not terminate running inference; use Stop all, then exit the supervisor when uninstalling. Running the launcher again opens a fresh owner session. A conflicting port is preserved; choose `--port 18040` for a separate profile with a separate `--data` directory.

1. **Settings / Configuración:** language, model directories, telemetry and scans.
2. **Integrations / Integraciones:** passive discovery, review executable/arguments/unique port, then save explicitly. Detection never executes discovered software. Terminal-only agents need an HTTP adapter.
3. **Models / Modelos:** scan the selected folders, select a compatible engine, context and load. No automatic conversion. Generic adapters declare compatibility; verify actual inference before trusting it.
4. **Evaluation / Evaluación:** functional tests and controlled sequential comparisons. GPU/engine-specific tuning requires its dedicated adapter. Unknown adapters are evaluated without claiming automatic tuning.
5. **External APIs / APIs externas:** keys remain private, cloud use is explicit. LAN servers are linked by private address, never installed or stopped remotely.

macOS-only bundled adapters (Strata Metal, MLX, Mirai Uzu, Foundation Models and this Mac's specialized paths) are unavailable. Portable versions manage reviewed generic local adapters and remote/external APIs. The iogpu limit, macOS privilege helper and removable-volume authorization button are disabled. CPU/RAM are measured with psutil. NVIDIA GPU telemetry is available when nvidia-smi is installed; absent counters remain unknown. CUDA/ROCm drivers and engine compatibility belong to their respective installations. No parity claim is made for Apple-only features.

## Build / Compilar

On the actual target OS, with Python 3.12 and Node.js for UI tests:

```sh
python -m venv .venv
# Activate the environment using your platform's normal command.
python -m pip install -r app/requirements-portable.txt
python -m unittest discover -s app/tests -p 'test_*.py'
node app/tests/test_comparison_ui.js
node app/tests/test_controls_i18n.js
python app/build_portable.py --out dist/portable
```

The included workflow builds separate Windows/Linux executable archives. A successful Python build on macOS does not prove Windows/Linux runtime functionality. See VERIFICATION.md for actually tested platforms. PyInstaller packages Python/dependency code; retain their notices and licenses.

## Uninstall / Desinstalar

Stop only this profile's managed services in the panel. Stop its supervisor using the exact PID/command matching its data directory (not by a generic process name). Remove the chosen application folder and its own shortcut. Data is separate; preserve it unless you explicitly intend a reset/deletion. The launcher does not uninstall engine programs or remove models, agent conversations or other profiles.
