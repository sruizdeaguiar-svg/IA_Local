# Desarrollo / Development

## Source layout

The public repository keeps application source under `app/`, documentation under `docs/` and generated downloads under `downloads/`. The original local development directory may have a different layout. Runtime state is always outside the source tree.

## Tests

Use Python 3.12+ on a supported platform and install `app/requirements.txt` into a development virtual environment:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r app/requirements.txt
.venv/bin/python -m unittest discover -s app/tests -p 'test_*.py'
node app/tests/test_comparison_ui.js
node app/tests/test_controls_i18n.js
```

All Python test modules establish a temporary `IA_LOCAL_HOME` **before importing application modules**. Never import a production-bound core before setting test isolation. Tests mock engine actions unless an explicit manual integration run is being performed. A legacy Strata shortcut test is optional when its separate source tree is absent.

## Build clean installer

Requirements: macOS 14+, Apple Silicon, Xcode command-line compilers and a relocatable CPython 3.12 runtime. A conventional Homebrew/framework Python virtualenv is not a relocatable runtime.

1. Obtain a CPython install-only distribution from [python-build-standalone](https://github.com/astral-sh/python-build-standalone) and preserve its licenses. Verify its upstream checksum.
2. Install the pinned runtime requirements into its `lib/python3.12/site-packages` using that runtime's pip (bootstrap pip through its official mechanism if absent).
3. Run:

```sh
python3 app/build_release.py --runtime /absolute/path/to/python --out /private/tmp/IA-Local-release
```

Build on an APFS volume. AppleDouble `._*` files on external filesystems can interfere with signing. The builder excludes caches/tests and copies a fixed list of backend/assets; it retains required NumPy typing modules. Keep runtime license notices. The generated archive contains `Instalar IA Local.app`, not a copy of your configured app.

The installer uses normal user privileges and will not overwrite an existing app or non-empty data directory. Its payload includes a Python runtime. The GPU helper is installed separately through macOS authorization. One supervisor instance uses port 8040; a second clean installation does not take over the first. `IA_LOCAL_PORT` is an internal QA/development override; change all client references consistently when using it.

## Add a local adapter

The reviewed JSON schema is implemented in `integrations.validate`. Minimum fields: `id` beginning `custom-`, `name`, `kind`, an absolute executable, unique `port`, `args` array with `{host}` and `{port}`, health route, start mode and declared formats. Model mode can substitute `{model}`, `{model_id}` and `{context}`. Unsupported format/architecture declarations must fail functional checks rather than be treated as universal compatibility. Idle services that need a proprietary model-load API require a dedicated adapter; the generic adapter does not invent one.

## Change backend jobs or UI

Add actions to `supervisor.job`, then to the correct LAN allowlist. Administrative credential/configuration changes also belong in `SENSITIVE`. Update shared UI availability rules and both language dictionaries. Keep extensive diagnostics under Activity, not in an unbounded status notification. Add tests for state transitions and failure/rollback behavior, not mirrors of implementation lines.

## Official protocol references

- [OpenAI Chat Completions](https://developers.openai.com/api/reference/resources/chat)
- [Anthropic Messages and streaming](https://platform.claude.com/docs/en/build-with-claude/streaming)
- [Kimi/Moonshot provider configuration](https://github.com/MoonshotAI/kimi-code/blob/main/docs/en/configuration/providers.md)
- [DeepSeek API](https://api-docs.deepseek.com/)
- [FreeLLMAPI](https://github.com/tashfeenahmed/freellmapi)

The adapters implement a documented subset. No account entitlement, balance, model availability or provider uptime is guaranteed by a successful inventory response.

## Windows/Linux builds

Install `app/requirements-portable.txt`, run the same isolated tests, then run `python app/build_portable.py --out dist/portable` on the target OS. The workflow `.github/workflows/portable.yml` builds Windows x64 and Linux x86_64, runs tests and smoke-tests the actual frozen executable with an empty temporary profile before uploading artifacts. CI source/binary smoke tests do not prove GPU drivers, every engine or a physical iPad. See PORTABLE.md.

`tests/test_portable.py` starts a real isolated HTTP supervisor and verifies one-use owner URLs, cookies, Host/Origin, CSRF, settings, reset and recovery. `tests/test_process_lifecycle.py` starts real synthetic parent/child processes and confirms owned descendant cleanup while preserving an unrelated process. Both require loopback sockets and same-user process visibility; do not run them in a sandbox that forbids those primitives.

## Portable E2E and packaging reference

CI uses Playwright 1.64.0 and Chromium headless against the actual frozen executable on each target OS. `browser_packaged.py` checks owner session, real telemetry state, settings/help translation, every tab, unsupported Mac controls, reviewed synthetic-agent registration/start/stop and reset/recovery. `packaged_session.py` captures only processes belonging to its random temporary data root, including one-file bootloader children. These browser checks use synthetic fixtures, not a real language-model inference benchmark.

Windows credential privacy is verified through actual NTFS DACL/SID entries using the Windows API, rather than assuming POSIX chmod bits. SQLite backup/restore closes both connections explicitly so Windows file locks do not linger. Persisted text is UTF-8 independent of the user's locale.

Official reference: [PyInstaller independent child instances and external loaders](https://pyinstaller.org/en/stable/common-issues-and-pitfalls.html), [Playwright Python](https://playwright.dev/python/docs/intro).
