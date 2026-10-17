# Third-party software

IA Local source uses the repository's Apache-2.0 license. Bundled or separately installed programs keep their own licenses. No model weights are distributed; each model's terms remain the user's responsibility.

| Component | Usage | License / official source |
|---|---|---|
| CPython | Bundled Mac runtime; frozen portable Python | PSF and included notices, https://www.python.org/psf/license/ |
| python-build-standalone | Relocatable runtime distribution | https://github.com/astral-sh/python-build-standalone; preserve distribution notices |
| psutil | Process/system metrics | BSD-3-Clause, https://github.com/giampaolo/psutil |
| PyYAML | Agent configuration | MIT, https://github.com/yaml/pyyaml |
| gguf / llama.cpp Python helpers | GGUF metadata | MIT, https://github.com/ggml-org/llama.cpp |
| NumPy | GGUF dependency | BSD-3-Clause and bundled notices, https://numpy.org/ |
| Requests, tqdm and transitive dependencies | GGUF dependencies | Their included dist-info licenses/notices |
| cryptography | Portable LAN certificates | Apache-2.0/BSD-3-Clause, https://github.com/pyca/cryptography |
| PyInstaller | Portable packaging | GPL with bootloader exception; https://pyinstaller.org/en/stable/license.html |
| macOS frameworks | Native UI and authorization | System frameworks; not redistributed separately |

The Mac Python payload preserves LICENSE and package dist-info notices. Portable archives include dependency notices under licenses/. Inference engines and agents are separate existing installations, not bundled or relicensed by IA Local. Do not include vendor checkouts, model downloads, personal data directories or build evidence when publishing source.
