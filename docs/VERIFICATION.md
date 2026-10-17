# Verificación / Verification · 1.2.0

Evidence recorded on 2026-10-17. The reference machine is a Mac mini M4 Pro, 24 GiB unified memory. Raw private logs, keys, conversations and personalized runtime state are excluded from this repository.

## Automated

- 48 isolated Python tests: account/TOTP replay, aggregation denominators, comparison validity, streaming fragmentation, evaluation/optimization sequences, cancellation, port conflicts, update rollback, agent profile preservation, integration schema, private LAN targets, external protocol conversion, full reset/recovery, real portable HTTP session and owned parent/child process teardown.
- Shared UI Node checks: state-dependent controls, navigation/ES-EN names, model/context comparison refresh, sequential evaluation/optimization, bounded notifications and complete detail.
- Python compile and extracted shared JavaScript syntax validation.
- Temporary test profiles are created before importing core. Real process tests use synthetic processes; an unrelated process must survive teardown.

## Real flows checked on macOS

- Native clean graphical installer: selected non-default app/data folders, no overwrite of existing installation, empty accounts/catalogue, bundled Python dependencies including GGUF/NumPy typing, connected supervisor and proper bundled icon metadata.
- Native clean profile: empty-state controls, full reset confirmation and recovery buttons; private backup created and recovery leaves services/LAN stopped.
- Portable browser shell on macOS: real owner-session page, actual live CPU/RAM, settings saved, English navigation and English help. HTTP tests verify one-use URLs, scoped cookies, Host/Origin and CSRF rejection. This is evidence of the browser shell on macOS, not a Windows/Linux binary test.
- Main installation: OpenCode and Hermes each completed two real stop/start cycles and health checks. Original configuration file hashes matched afterward; both were returned to their prior stopped state. The transient Hermes launcher/exec false-exit was fixed and regression tested.
- Existing FreeLLMAPI client key imported privately; local authenticated model inventory succeeded. Provider remains disconnected in IA Local. No billable generation test was made.
- A reviewed custom llama.cpp integration used a unique loopback port, loaded a real small Qwen model and returned 323 for 17×19. It was stopped/removed and the prior model/service state restored.
- Explicit LAN integration reached an authenticated private-interface proxy on the same Mac and completed real model inference; it was disconnected and removed. No second physical computer was used.
- Real OpenCode AI configuration proposal completed using an isolated local profile. Hermes was invoked through an isolated profile; invalid model-generated configuration was rejected. A valid Hermes-generated integration proposal is not claimed.
- The existing native/HTTPS application has prior functional evidence for streaming, model/context selection, shared evaluation controls, remote agent interfaces, GPU helper read/apply/restore and administrator second-factor paths. Not every engine/model/driver combination was rerun for this release.

## Still requires target-platform or account evidence

- Windows and Linux executable compilation/runtime, package installation and browser use on those operating systems remain pending until their CI/manual checks finish. The included workflow builds/tests both and smoke-tests actual frozen binaries. Do not relabel pending checks as passed from source tests on macOS.
- No physical iPad was available for this release's final checks. Shared web behavior and responsive layout do not prove an installed iPad PWA flow.
- No external OpenAI/Anthropic/Kimi/DeepSeek account generation or billing entitlement verified here. Protocol tests are isolated synthetic tests; a successful model inventory does not prove generation availability.
- NVIDIA/ROCm GPU behavior and every generic engine adapter require their actual hardware/runtime. Missing telemetry remains unknown. macOS iogpu does not exist on portable platforms.
- Mac binaries are ad-hoc signed, not notarized. Windows artifacts are unsigned. An independent security review and production signing remain desirable before broad distribution.

No universal model compatibility, automatic quality optimization, permanently up-to-date guarantee or Internet hosting claim is made.
