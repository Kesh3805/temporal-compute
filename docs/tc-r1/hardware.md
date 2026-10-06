# Qualification host, not execution hardware

Observed Windows host: Windows 11 build 22631, Intel Core i5-1135G7 (four physical/eight logical cores), 16,893,386,752 bytes RAM, Intel Iris Xe integrated graphics. There is no detected NVIDIA CUDA device. C: initially had approximately 1.5 GB free. No C++ compiler was found on PATH; no Visual Studio installation was found through its installation locator. Docker's Linux daemon was not running.

Mitsuba 3.9.1 and Dr.Jit 1.5.0 were installed in ignored `target/tc-r1e-env`; the global Python environment was not changed. `scalar_rgb` runs. `llvm_ad_rgb` fails because LLVM-C.dll is unavailable, and `cuda_ad_rgb` fails backend initialization. The retained probe records those failures rather than treating a listed variant as an available backend.

These constraints prevent a credible local CUDA/PBRT qualification and full reference commitment now. No execution hardware/backend is frozen. The original two independent 8192-spp reference streams and convergence escalation remain unchanged. A separate machine or storage location must be identified and measured before choosing a backend or starting expensive references. GitHub Actions provides a bounded CPU build/probe only; its runner identity is retained separately.
