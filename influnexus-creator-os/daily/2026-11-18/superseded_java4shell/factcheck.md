# Fact-check: Java4Shell (CVE-2026-114938): Calif says AI found a critical Java flaw in about an hour

Date: 2026-11-18

| ID | Claim | Status | Attribution | In script | Evidence | Note |
|---|---|---|---|---|---|---|
| c1 | An AI model found the bug in about one hour, at a token cost under $200 | THIRD-PARTY CLAIM | Calif | yes | [1](https://x.com/calif_io/status/2122799880221687837) [2](https://www.unite.ai/calif-uses-ai-to-find-java4shell-as-openjdk-and-oracle-ship-fixes/) | Calif's own account. Not independently checked. Calif's write-up was not opened directly from this environment. |
| c2 | The flaw is tracked as CVE-2026-114938 and sits in OpenJDK's Base64 decoder | CONFIRMED |  | no | [1](https://www.tenable.com/blog/java4shell-cve-2026-114938-frequently-asked-questions-about-openjdk-rce-vulnerability) [2](https://blog.qualys.com/vulnerabilities-threat-research/2026/11/17/how-to-find-mitigate-and-patch-the-critical-java4shell-flaw-cve-2026-114938-now) | Consistent across independent security vendors. Oracle advisory not opened directly. |
| c3 | Oracle released a fix in its 17 November 2026 Critical Patch Update | CONFIRMED |  | yes | [1](https://thehackernews.com/2026/11/java4shell-cve-2026-114938-enables-pre.html) [2](https://blog.qualys.com/vulnerabilities-threat-research/2026/11/17/how-to-find-mitigate-and-patch-the-critical-java4shell-flaw-cve-2026-114938-now) | Fixed versions reported: Java SE 17.0.21.1, 21.0.13.1, 25.0.5.1, 27.0.1.1. Re-check against Oracle's advisory before publishing. |
| c4 | Oracle rates the flaw 8.1 (CVSS 3.1) and describes it as difficult to exploit | COMPANY CLAIM | Oracle | yes | [1](https://www.malwarebytes.com/blog/bugs/2026/11/java4shell-a-critical-flaw-with-a-narrow-reach) | Calif rates it 9.2 (CVSS 4.0). Severity is disputed between the two. |
| c5 | No exploitation in the wild has been confirmed | THIRD-PARTY CLAIM | as of 18 Nov | yes | [1](https://www.aikido.dev/blog/java-17-rce-vulnerability-cve-2026-114938) | True as of research time on 18 November 2026. Must be re-checked on the day of publishing. |
| c6 | Java runs at banks, airlines and many company backends | CONFIRMED |  | yes | [1](https://www.techmeme.com/261117/p55) | Widely documented general fact; the '90% of Fortune 500' figure is deliberately not used. |
| c7 | Which model was used: Codex (Calif) or GPT-6 Cyber (New York Times) | DISPUTED |  | no | [1](https://x.com/Techmeme/status/2122802226464948303) | The script says only 'AI'. |
| c8 | CISA urged immediate patching | UNVERIFIED |  | no | [1](https://x.com/markgadala/status/2122840648336252938) | Conflicting reports. Not used. |
| c9 | The NSA network outage is linked to Java4Shell | SPECULATION |  | no | none | No reporting links them. Not used. |
