# IA Local user guide

## First launch and settings

Open IA Local and wait for “Supervisor connected”. Settings controls language, appearance, telemetry, discovery and update intervals. Save applies shared desktop/web preferences. A clean installation starts without accounts, keys, registered models or LAN access. Use Integrations for missing engines; weights are not downloaded automatically.

## Control and states

Cards distinguish process state, health and model state. Start prepares a service; Load selected may allocate memory and perform a readiness inference. Stop only terminates an identified managed process. Start all leaves weight-dependent engines waiting. Reclaim memory unloads local models and releases their engines; agents and macOS caches may still use RAM. Controls are enabled only when their operation is valid.

## Models and context

Authorize the SSD folder on the Mac and select Find new models. GGUF, MLX and other formats keep their locations; no universal conversion is performed. Choose a model, compatible engine and context, then save context before loading. Comparison updates with the selection. A listed model is not proof that it is loaded. New integration format declarations need a real test. Remote models show their server and are not downloaded to the Mac.

## Hermes and OpenCode

Start an agent and use Open web once its interface is available. Load a model, then use Use active model on its card or for both agents. Server, model and context are transferred for new sessions with configuration backups. Hermes requires at least 64000 tokens. OpenAI and other existing providers are retained; the local gateway does not enable cloud providers. Assistant tests use isolated profiles without editing yours.

## Add installations with AI

In Integrations, scan installations or enable automatic discovery. Detected does not mean compatible or running. Choose Configure or enter a name, type, executable and free port. Prepare a template, load a local model and choose OpenCode or Hermes to propose arguments based on --help. Review the JSON and explicitly save it. Model-proposed commands are never launched without that review. Terminal-only agents require an HTTP adapter; AI cannot create unsupported compatibility.

## Servers on other LAN computers

Add a name, private API URL ending in /v1, confirmed context and optional key. Only IPs on private networks connected to the Mac are accepted; moving networks may require editing the address. Internet targets and redirects are rejected. HTTPS requires a trusted certificate; sending a key over HTTP requires explicit acceptance. Saving does not connect. Connect queries /models and adds its inventory; select a model and test response and streaming. Disconnect prevents its use from IA Local and preserves the remote process. It does not use SSH or guarantee remote weight unloading or remote host updates.

## Evaluation and optimization

Telemetry is passive; Evaluate actively consumes resources. Close other workloads before testing. Llama uses warmup, pp512/tg128 and three repetitions; other engines use arithmetic, Spanish, streaming and synthetic generations. Evaluate all runs compatible engines sequentially and releases local memory. Optimize all searches parameters only where an adapter exists; other engines are evaluated without tuning. Compare matching model, quantization, context, engine version and method. Memory errors are not valid speed results. Speed does not measure quality. LAN timings include network latency; remote physical memory is unknown.

## Statistics

Control shows CPU, GPU, RAM, live generation, latest inference and day/week/month/all-time means. Tokens and streaming chunks are not equivalent. Missing measurements stay empty. The gateway observes its own requests and stores aggregate metrics. Direct connections may be outside its coverage; the UI states that coverage.

## GPU limit and permissions

Read the current value first. Unload models, choose a limit and apply. The helper is installed once with macOS authorization and only reads or sets iogpu.wired_limit_mb. Restore uses the verified previous value. Raising the ceiling does not create RAM and can reduce system headroom. Web access requires administrator rights and a second factor without sending your macOS password. Clean setup does not install the helper automatically.

## Web access, users and security

Create an account and enable LAN under Network and users. Install and verify the public certificate on every device. Set up the second factor on the Mac for remote administrative actions. Administrators manage users and integrations; Control users manage services and conversations; Read-only users view the panel. Remote keys remain in private 0600 files inside the 0700 data folder and are not exported. Do not expose ports to the Internet. Desktop and web share the same panel; iPad uses Safari.

## Updates and recovery

Check official versions, review scope and update a stopped component. Supported changes are backed up first. Recover version restores an available backup. Network failure leaves version status unknown; periodic checks cannot guarantee perpetual freshness. New integrations and remote servers need their own update adapter; AI-invented installers are never executed.

## Clean installation and troubleshooting

Install IA Local lets you select application and data folders or use user defaults. The package contains no keys, users, models or conversations. It detects Python requirements and reports missing ones before installation. Only one supervisor may use port 8040; an existing active installation is not replaced. For service failures, open Activity and review the bounded log. Port conflicts preserve foreign processes. For model failures check format, architecture, context and memory. Logs and model responses keep their original language.

## External APIs and FreeLLMAPI

Under External APIs, select OpenAI, Anthropic, Kimi, DeepSeek, FreeLLMAPI or Custom. Enter protocol, URL, exclusive adapter port, confirmed context, optional model IDs and your key. Saving leaves the connection disabled. Connect queries models; if inventory is unavailable, declare IDs and verify generation. Import FreeLLMAPI reuses its local key without exposing it and preserves existing profiles. Start its service and configure upstream cloud keys in its own panel. OpenAI Chat Completions and Anthropic Messages are different protocols; the adapter does not implement all extensions. Messages and files you send may leave the Mac and incur charges. Start all and the local assistant never enable cloud. Explicitly select an external model before evaluation or agent transfer. Accounts without balance or permissions may list models but fail generation.

## Reset and recovery

Settings → Reset entire application requires RESTABLECER. A private backup is saved, installations are unlinked and users and preferences reset. Programs, models and conversations are preserved. Recover last reset restores configuration with services and LAN stopped. Resynchronize agents if they used the previous token.

## Windows and Linux

The portable launcher opens the shared panel in your browser. Link executables under Integrations and model folders under Settings. No engines or weights are bundled. Mac-only adapters and iogpu controls are unavailable on these systems.
