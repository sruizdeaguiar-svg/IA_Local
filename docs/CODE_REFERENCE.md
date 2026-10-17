# Referencia del código / Code reference

This index covers every Python module-level function/class and class method in the distribution. It is generated from the public source, never from a personal runtime. Read each module contract below with the lifecycle/security rules in ARCHITECTURE.md and SECURITY.md. Source links point to the implementation.

## Operational contracts

- `start/stop/load/unload_all`: check unique reserved ports, preserve unknown listeners, serialize model lifecycle, distinguish waiting from health. Stop uses exact identities and managed descendant identities; no generic port/name kills.
- `discover/models/get_model`: scan explicit roots, read metadata, retain original paths, group complete GGUF shards and declare engine compatibility. Inventory is not a load check.
- `job/forward_chat`: asynchronous bounded operation states; lifecycle lock around selected models, streamed errors are failures, aggregate request timings without storing conversations.
- `benchmark/functional/optimize*`: record model, context, method, version and parameters. Sequential engine runs preserve partial failure/cancellation and release managed local weights. Optimization is engine-specific, not quality scoring.
- `configure_agents/configure_active_agents`: validate active engine health/context before selecting a profile; snapshot original files and preserve other providers and conversations.
- `register/validate/launch` in integrations: explicit executable/argument-array/schema review, unique port, declared formats and verified loopback. Passive discovery never runs candidates.
- `propose/parse` in integration_assistant: isolated selected local CLI, untrusted executable help, tools/cloud fallback disabled, reviewable invalid output cannot register.
- LAN `connect/disconnect`: inventory and local linkage only. No remote SSH, OS teardown, implicit model copying or universal load/update API.
- External `upstream/Proxy`: private keys, explicit cloud choice, pinned public HTTPS and checked hostname, exact managed local FreeLLMAPI exception, supported protocol subset and failure reporting.
- `save_user/totp_check/security_local/Gateway`: account roles, password hashing, replay-protected second factor, cookies, CSRF and exact Origin/Host. Native owner administration is separate from LAN authentication.
- `snapshot/detach/restore`: allowlisted private consistent backups, typed reset, unchanged owned process scope, token rotation, integrity checking and recovery with LAN/services stopped.
- `prepare/main/handler_class`: empty per-user portable profile, OS-specific data protection, own supervisor, one-use browser launch capability, scoped session and no bearer in JS.
- `policy/update/rollback*`: fixed official channels and allowlisted update adapters with backups; unknown integrations have no invented updater.
- `build/install`: source allowlist, no personal runtime state; no existing app/data overwrite; platform-specific compilers and honest signing limits.

## Symbols by module

### process_runtime.py

Keep a frozen app's private loader paths out of external engine processes.

PyInstaller changes library search paths for its bundled dependencies. External
engines must use their own libraries. On Windows, serialize the short-lived
SetDllDirectory override while creating a child, then restore the app's path.

| Symbol / signature | Source |
|---|---|
| `environment(env=None)` | [implementation](../app/process_runtime.py#L10) |
| `external_loader()` | [implementation](../app/process_runtime.py#L22) |
| `popen(*args, **kwargs)` | [implementation](../app/process_runtime.py#L32) |
| `run(*args, **kwargs)` | [implementation](../app/process_runtime.py#L36) |

### core.py

Core lifecycle and inventory. Models stay in their original locations. Process identities, unique ports and a profile-scoped lock protect lifecycle operations; individual engine branches implement only verified native APIs.

| Symbol / signature | Source |
|---|---|
| `own_process(p)` | [implementation](../app/core.py#L28) |
| `executable_path(name)` | [implementation](../app/core.py#L31) |
| `validate_ports(ports=None)` | [implementation](../app/core.py#L35) |
| `listener_pids(port)` | [implementation](../app/core.py#L43) |
| `expected_listener(service, pid)` | [implementation](../app/core.py#L51) |
| `check_service_ports(service)` | [implementation](../app/core.py#L65) |
| `init()` | [implementation](../app/core.py#L78) |
| `db()` | [implementation](../app/core.py#L96) |
| `event(kind, data)` | [implementation](../app/core.py#L101) |
| `read(p, default=None)` | [implementation](../app/core.py#L103) |
| `write(p, d)` | [implementation](../app/core.py#L106) |
| `run(args, timeout=60, env=None)` | [implementation](../app/core.py#L108) |
| `NoRedirect` | [implementation](../app/core.py#L113) |
| `NoRedirect.redirect_request(self, *args, **kwargs)` | [implementation](../app/core.py#L114) |
| `http(base, path, body=None, timeout=2, headers=None, text=False)` | [implementation](../app/core.py#L116) |
| `probe(s, path='/v1/models')` | [implementation](../app/core.py#L121) |
| `port_open(port)` | [implementation](../app/core.py#L139) |
| `registered(label)` | [implementation](../app/core.py#L141) |
| `identity(pid)` | [implementation](../app/core.py#L142) |
| `same(d)` | [implementation](../app/core.py#L148) |
| `ledger()` | [implementation](../app/core.py#L149) |
| `set_process(key, d)` | [implementation](../app/core.py#L150) |
| `lock(name='lifecycle')` | [implementation](../app/core.py#L158) |
| `find(s)` | [implementation](../app/core.py#L176) |
| `spawn(s, args, env=None)` | [implementation](../app/core.py#L200) |
| `stop_process(s)` | [implementation](../app/core.py#L209) |
| `wait(s, path='/v1/models', timeout=60)` | [implementation](../app/core.py#L236) |
| `discover()` | [implementation](../app/core.py#L245) |
| `fingerprint(m)` | [implementation](../app/core.py#L349) |
| `engine_signature(engine)` | [implementation](../app/core.py#L354) |
| `profile_for(m, engine)` | [implementation](../app/core.py#L360) |
| `save_presets(rows=None, engine='llama')` | [implementation](../app/core.py#L364) |
| `gguf_link(m)` | [implementation](../app/core.py#L373) |
| `models()` | [implementation](../app/core.py#L381) |
| `api_base(engine)` | [implementation](../app/core.py#L385) |
| `get_model(mid)` | [implementation](../app/core.py#L390) |
| `start(s)` | [implementation](../app/core.py#L396) |
| `stop(s)` | [implementation](../app/core.py#L480) |
| `available_services(include_unlinked=False)` | [implementation](../app/core.py#L532) |
| `unload_all(except_engine=None)` | [implementation](../app/core.py#L539) |
| `load(mid, engine)` | [implementation](../app/core.py#L557) |
| `model_headers(engine)` | [implementation](../app/core.py#L656) |
| `state()` | [implementation](../app/core.py#L666) |

### supervisor.py

Loopback authenticated supervisor, serialized jobs and OpenAI-compatible routing. Background state/maintenance threads never imply model readiness. The optional portable owner UI is enabled only by its launcher.

| Symbol / signature | Source |
|---|---|
| `pending_gpu()` | [implementation](../app/supervisor.py#L11) |
| `host_request(command, body, actor)` | [implementation](../app/supervisor.py#L12) |
| `host_result(rid, actor=None)` | [implementation](../app/supervisor.py#L20) |
| `host_next()` | [implementation](../app/supervisor.py#L25) |
| `host_complete(body)` | [implementation](../app/supervisor.py#L31) |
| `job(action, value=None, engine=None, actor='Mac')` | [implementation](../app/supervisor.py#L37) |
| `monitor()` | [implementation](../app/supervisor.py#L166) |
| `maintenance()` | [implementation](../app/supervisor.py#L179) |
| `forward_chat(handler, body)` | [implementation](../app/supervisor.py#L199) |
| `Handler` | [implementation](../app/supervisor.py#L252) |
| `Handler.log_message(self, *a)` | [implementation](../app/supervisor.py#L254) |
| `Handler.send(self, d, code=200)` | [implementation](../app/supervisor.py#L255) |
| `Handler.auth(self)` | [implementation](../app/supervisor.py#L257) |
| `Handler.do_GET(self)` | [implementation](../app/supervisor.py#L260) |
| `Handler.do_POST(self)` | [implementation](../app/supervisor.py#L270) |
| `ensure()` | [implementation](../app/supervisor.py#L288) |

### operations.py

Controlled evaluations, model-specific tuning, version checks and agent profiles. Synthetic benchmarks are distinct from passively observed requests; trial failure/cancellation is persisted rather than reported as valid speed.

| Symbol / signature | Source |
|---|---|
| `installed(s, exe)` | [implementation](../app/operations.py#L22) |
| `check_updates()` | [implementation](../app/operations.py#L48) |
| `update_agents(s)` | [implementation](../app/operations.py#L71) |
| `configure_agents(mid, select=True, engine=None, targets=None)` | [implementation](../app/operations.py#L95) |
| `configure_active_agents(target)` | [implementation](../app/operations.py#L134) |
| `agent_profiles()` | [implementation](../app/operations.py#L152) |
| `restore_agents()` | [implementation](../app/operations.py#L163) |
| `evaluation_model(value)` | [implementation](../app/operations.py#L172) |
| `benchmark(mid, engine, cancel, progress)` | [implementation](../app/operations.py#L185) |
| `benchmark_all(mid, cancel, progress)` | [implementation](../app/operations.py#L239) |
| `functional(engine, public, strict=True)` | [implementation](../app/operations.py#L268) |
| `optimize_all(value, cancel, progress)` | [implementation](../app/operations.py#L294) |
| `optimize(mid, engine, cancel, progress)` | [implementation](../app/operations.py#L342) |
| `optimize_mirai(mid, cancel, progress)` | [implementation](../app/operations.py#L401) |
| `restore_profile(mid, engine)` | [implementation](../app/operations.py#L440) |
| `agent_checks(cancel, progress, only=None)` | [implementation](../app/operations.py#L448) |
| `configure_cloud()` | [implementation](../app/operations.py#L519) |
| `rollback_update(s)` | [implementation](../app/operations.py#L538) |

### integrations.py

Reviewed, user-owned local HTTP integrations; discovery never starts software.

| Symbol / signature | Source |
|---|---|
| `definitions()` | [implementation](../app/integrations.py#L10) |
| `definition(s)` | [implementation](../app/integrations.py#L11) |
| `validate(value)` | [implementation](../app/integrations.py#L12) |
| `install_registry()` | [implementation](../app/integrations.py#L54) |
| `register(value)` | [implementation](../app/integrations.py#L63) |
| `unregister(sid)` | [implementation](../app/integrations.py#L73) |
| `attach_models(rows)` | [implementation](../app/integrations.py#L78) |
| `probe_custom(s)` | [implementation](../app/integrations.py#L87) |
| `stop_custom(s)` | [implementation](../app/integrations.py#L95) |
| `verify_loopback(s)` | [implementation](../app/integrations.py#L101) |
| `launch(s, model=None)` | [implementation](../app/integrations.py#L112) |
| `public_model(s, m)` | [implementation](../app/integrations.py#L130) |
| `scan()` | [implementation](../app/integrations.py#L133) |
| `view()` | [implementation](../app/integrations.py#L154) |

### integration_assistant.py

Existing agent CLI, isolated local provider, no tools, reviewed JSON output.

| Symbol / signature | Source |
|---|---|
| `parse(text)` | [implementation](../app/integration_assistant.py#L6) |
| `propose(value, cancel, progress)` | [implementation](../app/integration_assistant.py#L22) |

### remote_servers.py

Opt-in LAN APIs. No remote process control, redirects or internet targets.

| Symbol / signature | Source |
|---|---|
| `definitions()` | [implementation](../app/remote_servers.py#L5) |
| `definition(s)` | [implementation](../app/remote_servers.py#L6) |
| `networks()` | [implementation](../app/remote_servers.py#L7) |
| `validate_url(url)` | [implementation](../app/remote_servers.py#L18) |
| `headers(s)` | [implementation](../app/remote_servers.py#L28) |
| `api_base(s)` | [implementation](../app/remote_servers.py#L31) |
| `request(s, path, body=None, timeout=5)` | [implementation](../app/remote_servers.py#L32) |
| `connected(s)` | [implementation](../app/remote_servers.py#L33) |
| `connect(s)` | [implementation](../app/remote_servers.py#L34) |
| `disconnect(s)` | [implementation](../app/remote_servers.py#L43) |
| `register(v)` | [implementation](../app/remote_servers.py#L47) |
| `unregister(s)` | [implementation](../app/remote_servers.py#L64) |
| `install_registry()` | [implementation](../app/remote_servers.py#L66) |
| `models_remote()` | [implementation](../app/remote_servers.py#L68) |
| `rows()` | [implementation](../app/remote_servers.py#L75) |

### external_providers.py

Explicit cloud connections with private keys and OpenAI/Anthropic adapters.

Local proxy ports are authenticated and loopback-only. No provider is enabled by
startup, discovery or Start all. TLS targets are pinned to validated public IPs.

| Symbol / signature | Source |
|---|---|
| `definitions()` | [implementation](../app/external_providers.py#L11) |
| `definition(s)` | [implementation](../app/external_providers.py#L12) |
| `target(url)` | [implementation](../app/external_providers.py#L13) |
| `upstream(s, path, body=None)` | [implementation](../app/external_providers.py#L21) |
| `register(v)` | [implementation](../app/external_providers.py#L40) |
| `install_registry()` | [implementation](../app/external_providers.py#L58) |
| `inventory(s)` | [implementation](../app/external_providers.py#L63) |
| `connect(s)` | [implementation](../app/external_providers.py#L73) |
| `disconnect(s)` | [implementation](../app/external_providers.py#L86) |
| `unregister(s)` | [implementation](../app/external_providers.py#L92) |
| `models_cloud()` | [implementation](../app/external_providers.py#L94) |
| `to_anthropic(body)` | [implementation](../app/external_providers.py#L101) |
| `finish_reason(reason)` | [implementation](../app/external_providers.py#L137) |
| `from_anthropic(d)` | [implementation](../app/external_providers.py#L138) |
| `anthropic_chunks(response)` | [implementation](../app/external_providers.py#L144) |
| `Proxy` | [implementation](../app/external_providers.py#L167) |
| `Proxy.log_message(self, *a)` | [implementation](../app/external_providers.py#L169) |
| `Proxy.authorized(self)` | [implementation](../app/external_providers.py#L170) |
| `Proxy.send_json(self, d, status=200)` | [implementation](../app/external_providers.py#L171) |
| `Proxy.do_GET(self)` | [implementation](../app/external_providers.py#L173) |
| `Proxy.do_POST(self)` | [implementation](../app/external_providers.py#L177) |
| `rows()` | [implementation](../app/external_providers.py#L203) |
| `view()` | [implementation](../app/external_providers.py#L205) |
| `import_freellmapi()` | [implementation](../app/external_providers.py#L208) |

### lan.py

Authenticated HTTPS access on one physical, private LAN interface.

Inference backends keep their loopback bindings. This gateway is the only LAN listener.
Account administration is deliberately available only through the native Mac panel.

| Symbol / signature | Source |
|---|---|
| `access_db()` | [implementation](../app/lan.py#L19) |
| `users()` | [implementation](../app/lan.py#L29) |
| `save_user(v)` | [implementation](../app/lan.py#L32) |
| `security_status(name=None)` | [implementation](../app/lan.py#L47) |
| `totp_begin(name)` | [implementation](../app/lan.py#L52) |
| `totp_check(name, code, enroll=False)` | [implementation](../app/lan.py#L60) |
| `security_local(body)` | [implementation](../app/lan.py#L73) |
| `address()` | [implementation](../app/lan.py#L86) |
| `certificate(ip)` | [implementation](../app/lan.py#L93) |
| `status()` | [implementation](../app/lan.py#L105) |
| `configure(enabled, dispatch=None)` | [implementation](../app/lan.py#L108) |
| `Gateway` | [implementation](../app/lan.py#L130) |
| `Gateway.log_message(self, *args)` | [implementation](../app/lan.py#L132) |
| `Gateway.send(self, value, code=200, ctype='application/json', headers=None)` | [implementation](../app/lan.py#L133) |
| `Gateway.allowed_host(self)` | [implementation](../app/lan.py#L138) |
| `Gateway.origin_ok(self)` | [implementation](../app/lan.py#L141) |
| `Gateway.session(self)` | [implementation](../app/lan.py#L153) |
| `Gateway.payload(self)` | [implementation](../app/lan.py#L159) |
| `Gateway.login(self)` | [implementation](../app/lan.py#L164) |
| `Gateway.do_GET(self)` | [implementation](../app/lan.py#L180) |
| `Gateway.do_POST(self)` | [implementation](../app/lan.py#L181) |
| `Gateway.do_PUT(self)` | [implementation](../app/lan.py#L182) |
| `Gateway.do_DELETE(self)` | [implementation](../app/lan.py#L183) |
| `Gateway.do_PATCH(self)` | [implementation](../app/lan.py#L184) |
| `Gateway.do_OPTIONS(self)` | [implementation](../app/lan.py#L185) |
| `Gateway.handle_request(self)` | [implementation](../app/lan.py#L186) |
| `Gateway.proxy(self)` | [implementation](../app/lan.py#L263) |

### privileged.py

Client for the fixed GPU helper. Never accepts arbitrary privileged operations.

| Symbol / signature | Source |
|---|---|
| `request(value=None)` | [implementation](../app/privileged.py#L5) |
| `status()` | [implementation](../app/privileged.py#L24) |

### app_settings.py

Validated user preferences. Secrets and managed runtime state are excluded.

| Symbol / signature | Source |
|---|---|
| `save(value)` | [implementation](../app/app_settings.py#L4) |

### reset_state.py

Reversible application reset. Never uninstalls engines, weights or agent data.

Invoke under the supervisor lifecycle lock. Stop only identities in this data
profile's managed ledger. Back up own configuration and SQLite consistently;
restoration invalidates sessions and does not restart services or enable LAN.

| Symbol / signature | Source |
|---|---|
| `latest()` | [implementation](../app/reset_state.py#L12) |
| `status()` | [implementation](../app/reset_state.py#L16) |
| `snapshot(prefix='reset-')` | [implementation](../app/reset_state.py#L19) |
| `clear_sessions()` | [implementation](../app/reset_state.py#L32) |
| `detach(value, progress)` | [implementation](../app/reset_state.py#L37) |
| `restore(progress)` | [implementation](../app/reset_state.py#L64) |
| `attach_known(sid)` | [implementation](../app/reset_state.py#L94) |

### comparison.py

Measured per-model/per-engine comparisons. No inference, ranking or invented rates.

| Symbol / signature | Source |
|---|---|
| `build(catalog, results, optimizations)` | [implementation](../app/comparison.py#L4) |

### inference_stats.py

Persistent aggregate inference metrics. Never stores prompts or generated text.

| Symbol / signature | Source |
|---|---|
| `summary(connection)` | [implementation](../app/inference_stats.py#L4) |
| `Capture` | [implementation](../app/inference_stats.py#L26) |
| `Capture.__init__(self)` | [implementation](../app/inference_stats.py#L28) |
| `Capture.item(self, d)` | [implementation](../app/inference_stats.py#L30) |
| `Capture.feed(self, b)` | [implementation](../app/inference_stats.py#L36) |
| `Capture.finish(self)` | [implementation](../app/inference_stats.py#L44) |

### memory_status.py

macOS memory breakdown; cache categories overlap and are not summed.

| Symbol / signature | Source |
|---|---|
| `read()` | [implementation](../app/memory_status.py#L4) |

### gpu_telemetry.py

Read macOS GPU driver counters without root; absent counters stay unknown.

| Symbol / signature | Source |
|---|---|
| `read()` | [implementation](../app/gpu_telemetry.py#L4) |

### updater.py

Fixed update adapters. All downloads/builds execute as the logged-in user.

| Symbol / signature | Source |
|---|---|
| `policy(s)` | [implementation](../app/updater.py#L8) |
| `rows_with_current_versions(rows)` | [implementation](../app/updater.py#L12) |
| `github(repo, path='releases?per_page=30')` | [implementation](../app/updater.py#L29) |
| `stable_release(repo, asset_filter)` | [implementation](../app/updater.py#L33) |
| `download(asset, folder)` | [implementation](../app/updater.py#L40) |
| `unpack(archive, folder)` | [implementation](../app/updater.py#L53) |
| `app_update(s, backup, progress)` | [implementation](../app/updater.py#L60) |
| `replace_llama_runtime(incoming, target)` | [implementation](../app/updater.py#L95) |
| `_update(s, progress=lambda _: None)` | [implementation](../app/updater.py#L113) |
| `update(s, progress=lambda _: None)` | [implementation](../app/updater.py#L174) |
| `restore(folder)` | [implementation](../app/updater.py#L184) |
| `rollback(s)` | [implementation](../app/updater.py#L209) |

### exo_local.py

Official EXO v1.0.71, restricted to this Mac. No libp2p sockets/mDNS.

Only the transport is local-only; Node/Master/Worker/inference and dashboard are
EXO's real implementation. Cluster features are deliberately unavailable.

| Symbol / signature | Source |
|---|---|
| `LocalTransport` | [implementation](../app/exo_local.py#L15) |
| `LocalTransport.gossipsub_subscribe(self, topic)` | [implementation](../app/exo_local.py#L16) |
| `LocalTransport.gossipsub_unsubscribe(self, topic)` | [implementation](../app/exo_local.py#L17) |
| `LocalTransport.gossipsub_publish(self, topic, data)` | [implementation](../app/exo_local.py#L18) |
| `LocalTransport.recv(self)` | [implementation](../app/exo_local.py#L19) |
| `loopback_api(self, ev)` | [implementation](../app/exo_local.py#L21) |
| `local_api_init(self, *args, **kwargs)` | [implementation](../app/exo_local.py#L29) |
| `prepare_catalog()` | [implementation](../app/exo_local.py#L42) |

### desktop_server.py

Loopback desktop browser bridge for the portable Windows/Linux distribution.

The launcher owns a private bearer, obtains a single-use 30-second capability,
then opens a random, cookie-scoped desktop session. No bearer is embedded in JS.
Only same-origin, CSRF-protected bridge requests can administer this profile.
This interface is never bound to LAN; LAN access uses lan.py's HTTPS accounts.

| Symbol / signature | Source |
|---|---|
| `launch_url()` | [implementation](../app/desktop_server.py#L17) |
| `bootstrap_js(base, csrf)` | [implementation](../app/desktop_server.py#L25) |
| `handler_class(parent)` | [implementation](../app/desktop_server.py#L33) |

### portable_launcher.py

Portable per-user launcher. Starts a loopback supervisor and opens its panel.

A PyInstaller build bundles the shared backend and Python dependencies. From
source: python portable_launcher.py [--data DIRECTORY] [--port 8040]. Engines,
weights and credentials are never bundled. No administrator account is needed.

| Symbol / signature | Source |
|---|---|
| `prepare(data)` | [implementation](../app/portable_launcher.py#L12) |
| `main()` | [implementation](../app/portable_launcher.py#L28) |

### portable_security.py

Per-user filesystem protection and LAN TLS without macOS command dependencies.

| Symbol / signature | Source |
|---|---|
| `secure_directory(path)` | [implementation](../app/portable_security.py#L6) |
| `certificate(root, ip)` | [implementation](../app/portable_security.py#L27) |

### install_clean.py

Fresh, offline installation into user-selected app/data directories.

No existing directory is replaced. Only allowlisted payload files are copied;
no accounts, keys, model paths, histories or network access are preconfigured.
The bundled Python runtime makes the installed backend independent of Strata.

| Symbol / signature | Source |
|---|---|
| `install(payload_app, applications, data, desktop=False, port=8040)` | [implementation](../app/install_clean.py#L10) |

### build_release.py

Build the unsigned-source/ad-hoc-signed macOS arm64 distribution.

Provide a prepared relocatable CPython prefix with requirements.txt installed.
Only allowlisted app source/assets enter the payload. Personal runtime state,
models, vendor checkouts, evidence and credentials are never copied.

| Symbol / signature | Source |
|---|---|
| `command(args)` | [implementation](../app/build_release.py#L12) |
| `build(runtime, out)` | [implementation](../app/build_release.py#L13) |

### build_portable.py

Build a native portable executable on the target OS; no cross compilation.

pip install -r requirements-portable.txt
python build_portable.py --out dist/portable

| Symbol / signature | Source |
|---|---|
| `build(out)` | [implementation](../app/build_portable.py#L11) |

### install_portable_source.py

Install the portable source edition using an existing Python 3.12+.

This edition is usable before frozen binary distribution: a private virtualenv
installs official PyPI dependencies, with source/configuration kept separate.
Never overwrites an installation or installs an inference engine/model.

| Symbol / signature | Source |
|---|---|
| `install(destination, data, desktop=False)` | [implementation](../app/install_portable_source.py#L11) |

### build_source_portable.py

Create clean source-edition installers; these are not native executable builds.

| Symbol / signature | Source |
|---|---|
| `build(out)` | [implementation](../app/build_source_portable.py#L7) |

## Shared interface and native code

`index.html` contains the shared native/web layout, controls, state rendering, comparison/evaluation views, settings/reset dialogs and ES/EN dictionary. `native()` selects WKWebView, the portable owner bridge or authenticated HTTPS. `reconcileControls()` derives meaningful actions from current state; backend authorization remains authoritative. Pure Node tests exercise the shared functions.

`App.swift` handles native file authorization, export and the fixed helper install. `Installer.swift` presents selected app/data folders and invokes the allowlisted clean installer. `authorize.c` implements macOS authorization; `gpu_helper.c` and `privileged_gpu.c` enforce the one-sysctl scope. Portable install scripts are per-user and never request global administrator privileges.

## Persistence and compatibility changes

Keep optional native adapters import-safe on clean profiles. State schema additions must preserve missing/unknown fields as unknown and keep public catalogues separate from private credentials. When adding an action, update LAN role/step-up allowlists, shared controls, manuals and regression tests. Never use the real user data directory in a test.
