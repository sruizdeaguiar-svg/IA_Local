# Security model

This is a user-operated local control application, not an Internet-facing multi-tenant hosting service. Keep its ports on loopback or the authenticated private LAN gateway. Do not forward them through an Internet router.

- Local supervisor: random bearer token, private data directory, loopback bind, Host checks, no redirects for engine HTTP.
- Web: TLS, Secure/HttpOnly/SameSite cookie, session expiry, CSRF, Origin/Host validation, admin/control/read-only roles, PBKDF2 passwords and TOTP step-up for administration.
- Local processes: no shell argument strings, no generic kill-by-name/port, identity ledger, reserved ports, loopback verification for custom services. Definitions require an explicit review/save before launch.
- Discovery: targeted known paths and user-owned listeners; never executes discovered software. It is not a full subnet port scan.
- AI assistant: treats executable help as untrusted data, uses a selected existing CLI with isolated local provider credentials, denies tools, preserves real agent configurations. It cannot install software or bypass validation.
- LAN targets: literal private IPs on currently connected physical/private networks, no Internet/private-via-cloud SSRF redirection. Moving to another network requires revalidation. HTTPS certificate errors are not silently bypassed. HTTP keys require explicit acceptance.
- External targets: HTTPS and public DNS addresses only; the validated IP is pinned for the TLS connection and the hostname is checked. FreeLLMAPI is an explicit local exception requiring the known managed process before its key is sent.
- API keys: private 0600 JSON files inside 0700 directories; never returned to the UI, exported or committed. This is not full-disk/keychain encryption. Protect the macOS account and enable FileVault as appropriate to your own threat model.
- GPU helper: one sysctl operation, no arbitrary commands/network service. The installed root-owned launchd definition fixes the allowed local UID; the socket verifies the peer. Initial installation requires macOS authentication. The GUI never stores the system password.
- Updates: fixed adapters and official channels, backups and validation. Unknown integrations are not automatically updated using model-generated commands.

## Release and reporting

The included app and installer use local ad-hoc signatures. They are **not Developer ID signed or notarized**. A public production release should add Developer ID signing/notarization and independent security review. The source remains inspectable under the repository's Apache-2.0 license.

Do not include passwords, tokens, keys, conversations, health/patient data or personal logs in issues. Report a suspected secret privately to the repository owner through an available private channel. Public synthetic reproduction cases are preferred.

## Portable desktop owner session

The portable launcher runs without elevation and uses a distinct loopback browser bridge. A private bearer issues a 30-second single-use capability; the browser receives a random, path-scoped HttpOnly/SameSite session cookie and CSRF token. Exact Host/Origin validation and a same-origin content policy block cross-site bridge use. The root bearer is never embedded in the page. This owner UI represents the logged-in OS account, like the native app; it is not a LAN user session. Do not share its URL or run untrusted code under that account. Closing a tab does not stop the supervisor.

Windows credentials inherit a protected per-user NTFS ACL; POSIX directories/files use 0700/0600. Portable builds are unsigned. Engine drivers and optional GPU telemetry require their own installed tooling. Windows batch/PowerShell interpreters are not accepted as generic managed server commands. No process is terminated merely because it occupies a selected port; owned descendant identities are captured before parent teardown.

A complete reset backs up configuration and accounts privately before clearing active state. The backup contains sensitive credentials and must remain private. Recovery verifies its manifest, invalidates web sessions and never automatically starts services or opens LAN. No system GPU setting or external program/model/conversation is deleted by reset.
