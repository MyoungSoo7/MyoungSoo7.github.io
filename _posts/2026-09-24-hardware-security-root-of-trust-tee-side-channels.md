---
layout: post
title: "하드웨어 보안 — 소프트웨어가 딛고 선 바닥은 누가 지키는가?"
date: 2026-09-24 19:53:25 +0900
categories: [Security, Hardware]
tags: [Hardware Security, TPM, Secure Boot, TEE, SGX, SEV-SNP, Spectre, Meltdown, Rowhammer, Root of Trust]
---

소프트웨어 보안은 한 가지 전제 위에 서 있다. **CPU 는 명령어를 적힌 대로 실행하고, 메모리는 쓴 값을 그대로 돌려주며, 부팅된 코드는 우리가 설치한 그 코드다.** 권한 분리, 프로세스 격리, 컨테이너, 암호 라이브러리 전부가 이 전제를 공짜로 가져다 쓴다.

하드웨어 보안은 이 전제를 공짜로 두지 않는 분야다. 그리고 지난 10년의 연구가 보여준 건, 그 전제가 생각보다 훨씬 자주 틀린다는 사실이었다.

이 글은 하드웨어 보안을 세 개의 질문으로 나눠 본다.

| 질문 | 대표 기술 | 대표 실패 |
|---|---|---|
| 1. 지금 돌고 있는 코드가 진짜인가? | Root of Trust, Secure Boot, TPM Measured Boot | 서명 체인 우회, fTPM 타이밍 누출 |
| 2. OS·하이퍼바이저가 뚫려도 비밀이 남는가? | TEE — SGX, TrustZone, SEV-SNP, TDX, Secure Enclave | Foreshadow, Plundervolt |
| 3. 하드웨어 자체가 약속을 지키는가? | 캐시·투기실행·DRAM 설계 | Spectre, Meltdown, Rowhammer |

## 1. 신뢰의 뿌리 — "첫 번째 명령어" 를 누가 보증하나

부팅은 사슬이다. ROM → 펌웨어 → 부트로더 → 커널 → 사용자 공간. 각 단계가 다음 단계를 검증한다면, 사슬 전체의 신뢰는 **맨 처음 고리**로 환원된다. 이 첫 고리를 수정 불가능한 하드웨어(마스크 ROM, 퓨즈)에 박아 둔 것이 **Root of Trust(RoT)** 다.

RoT 위에서 두 가지 서로 다른 전략이 돈다.

| | Secure Boot (검증 부팅) | Measured Boot (측정 부팅) |
|---|---|---|
| 동작 | 다음 단계의 서명을 검사해 **틀리면 멈춘다** | 다음 단계의 해시를 TPM PCR 에 **기록만 한다** |
| 판단 주체 | 부팅하는 기기 자신 | 나중에 원격 검증자(attestation) |
| 대표 사양 | UEFI Secure Boot[^uefi] | TCG TPM 2.0[^tcg] |

Secure Boot 는 "이상하면 안 켠다", Measured Boot 는 "켜되 무엇이 켜졌는지 위조 불가능하게 남긴다" 이다. 리눅스 커널 문서도 TPM 이벤트 로그를 펌웨어가 PCR 에 확장(extend)한 측정값의 기록으로 설명한다.[^kernel-tpm]

이게 더는 서버만의 이야기가 아니다. Microsoft 는 Windows 11 최소 요구사항에 **"UEFI, Secure Boot capable"** 과 **"TPM version 2.0"** 을 명시했다.[^win11] 일반 PC 가 하드웨어 RoT 를 전제로 출하되는 시대가 된 것이다.

데이터센터 쪽은 한 발 더 나갔다. CHIPS Alliance 의 **Caliptra** 는 RoT 자체를 오픈소스 IP·펌웨어로 공개한 프로젝트로, 스스로를 이렇게 소개한다: *"Caliptra targets datacenter-class SoCs like CPUs, GPUs, DPUs, TPUs ... A Caliptra integration provides the SoC with Identity, Measured Boot and Attestation capabilities."*[^caliptra] 신뢰의 뿌리를 블랙박스로 두지 않고 감사 가능하게 만들겠다는 방향이다.

NIST SP 800-193 은 플랫폼 펌웨어 복원력을 **보호(Protection)·탐지(Detection)·복구(Recovery)** 세 축으로 정리한다.[^nist193] 막는 것만으로는 부족하고, 뚫렸을 때 알아채고 정상 이미지로 되돌릴 수 있어야 한다는 뜻이다.

**하지만 RoT 도 실리콘이다.** TPM-Fail 연구는 Intel 펌웨어 TPM 과 한 상용 TPM 칩의 ECDSA 서명 구현에서 타이밍 누출을 찾아 개인키를 복원했다.[^tpmfail] "TPM 에 넣었으니 안전하다" 는 구현까지 봐야 참이 된다.

## 2. TEE — 운영체제를 믿지 않는 연산

두 번째 질문은 더 급진적이다. **커널·하이퍼바이저·클라우드 운영자가 적이어도** 내 코드와 데이터를 지킬 수 있는가?

Trusted Execution Environment(TEE) 는 CPU 가 메모리를 암호화·무결성 검증하고, 특권 소프트웨어조차 그 영역을 읽지 못하게 막는 구조다.

| 기술 | 격리 단위 | 누구를 믿지 않나 |
|---|---|---|
| Arm TrustZone | Secure World / Normal World | Normal World OS |
| Intel SGX | 프로세스 안의 enclave | OS, 하이퍼바이저 |
| AMD SEV-SNP[^snp] | VM 전체 | 하이퍼바이저 (메모리 무결성 포함) |
| Intel TDX[^tdx] | VM 전체 (Trust Domain) | 하이퍼바이저 |
| Apple Secure Enclave[^apple] | 별도 보조 프로세서 | 메인 애플리케이션 프로세서 커널 |

Apple 의 설명이 TEE 의 목적을 가장 명확하게 요약한다: *"The Secure Enclave is isolated from the main processor to provide an extra layer of security and is designed to keep sensitive user data secure even when the Application Processor kernel becomes compromised."*[^apple] 같은 문서는 Secure Enclave Processor 를 전용 코어로 둔 이유를 *"This helps prevent side-channel attacks that depend on malicious software sharing the same execution core"* 라고 적는다. 이 문장이 3장의 복선이다.

흐름을 보면 격리 단위가 **enclave → VM 전체** 로 커지고 있다. SGX 는 애플리케이션을 쪼개 다시 짜야 했지만, SEV-SNP·TDX 는 기존 VM 을 거의 그대로 올린다. 이른바 컨피덴셜 컴퓨팅이 클라우드 상품이 된 건 이 전환 덕분이다.

그리고 SGX 는 그 자체로 **공격 연구의 표적**이 되었다.

- **Foreshadow** (USENIX Security 2018) — 투기 실행을 이용해 SGX enclave 메모리와 머신의 attestation 개인키까지 추출했다.[^foreshadow]
- **Plundervolt** (IEEE S&P 2020) — 소프트웨어로 CPU 전압을 낮춰(undervolting) enclave 안 연산에 오류를 주입하고, 이를 통해 암호키를 복원했다.[^plundervolt]

두 공격 모두 SGX 의 "암호화 설계" 가 틀려서가 아니라, **enclave 가 적과 같은 칩·같은 전원선 위에 산다**는 물리적 사실 때문에 성립했다.

## 3. 하드웨어가 약속을 어길 때 — 부채널과 결함

### 3.1 Spectre & Meltdown: 성능 최적화가 보안 경계를 무너뜨리다

2018년 공개된 두 공격은 CPU 의 **투기적·비순차 실행** 을 겨냥했다. 버그가 아니라 **설계대로 동작하는 성능 기능**이었다는 점이 충격이었다.

Meltdown 논문의 요약: *"The attack is independent of the operating system, and it does not rely on any software vulnerabilities. Meltdown breaks all security guarantees provided by address space isolation."*[^meltdown]

Spectre 는 범위가 더 넓다: *"speculative execution implementations violate the security assumptions underpinning numerous software security mechanisms, including operating system process separation, containerization, just-in-time (JIT) compilation..."*[^spectre]

"컨테이너 격리" 가 저 목록에 들어 있다는 점을 기억해 두자. 쿠버네티스 노드 위 서로 다른 테넌트의 파드가 같은 물리 코어를 공유한다면, 네임스페이스와 cgroup 은 이 층위의 격리를 제공하지 않는다.

완화는 대부분 **소프트웨어가 하드웨어의 빈틈을 메우는** 형태다. 리눅스 커널 문서는 Spectre 변종별로 커널이 적용하는 완화책(배리어, retpoline, IBRS 등)과 부트 파라미터를 정리해 두었다.[^kernel-spectre] 즉 하드웨어 결함의 비용을 소프트웨어가 성능으로 치르고 있다.

### 3.2 Rowhammer: 메모리가 쓴 값을 지키지 못하다

2014년 ISCA 논문은 DRAM 의 같은 행(row)을 반복해서 활성화하면 **인접 행의 비트가 뒤집힌다**는 걸 보였다. 저자들은 세 제조사의 DDR3 모듈 **129개 중 110개**에서 오류를 유도했다.[^rowhammer]

> *"By reading from the same address in DRAM, we show that it is possible to corrupt data in nearby addresses."*

원인은 미세공정이 진행될수록 셀 간 전기적 간섭을 막기 어려워지는 물리 현상이다. 이후 DDR4 에 도입된 칩 내부 완화책(TRR)도 TRRespass 연구에서 우회되었다.[^trrespass] 메모리 셀이 작아질수록 이 싸움은 쉬워지지 않는다.

Rowhammer 가 무서운 건 **읽기만으로 쓰기를 일으킨다**는 점이다. 권한 검사는 "누가 어디에 쓰는가" 를 보지, "누가 옆 줄을 너무 자주 읽는가" 를 보지 않는다.

## 4. 실무자가 가져갈 것

하드웨어를 직접 설계하지 않는 개발자·운영자에게도 체크리스트는 있다.

1. **펌웨어·마이크로코드는 패치 대상이다.** OS 패키지만 업데이트하고 BIOS·마이크로코드를 방치하면 3장의 완화책 절반이 빠진다.
2. **Secure Boot 와 TPM 을 켜고, 측정값을 실제로 쓴다.** 켜 두기만 하고 attestation 을 검증하지 않으면 Measured Boot 는 아무도 읽지 않는 로그다.
3. **멀티테넌트라면 코어 공유를 위협 모델에 넣는다.** 민감 워크로드는 전용 노드, SMT 비활성화, 혹은 컨피덴셜 VM 을 검토한다.
4. **TEE 는 "신뢰 대상을 줄이는" 도구지 "신뢰를 없애는" 도구가 아니다.** 여전히 CPU 벤더, 마이크로코드, attestation 서비스를 믿어야 한다.
5. **ECC 메모리는 Rowhammer 의 해결책이 아니라 완충재다.** 오류 로그(EDAC)를 모니터링해 비정상 패턴을 본다.

## 5. 맺으며 — 바닥을 믿는 비용

하드웨어 보안의 역사는 **"하드웨어는 믿을 수 있다" 는 가정이 하나씩 철회되어 온 기록**이다. 투기 실행은 격리를 새게 했고, DRAM 은 비트를 뒤집었고, 신뢰 실행 환경은 전압 조작에 흔들렸다.

그런데 이 분야의 해법은 대개 **더 많은 하드웨어**다. 더 깊은 RoT, 더 넓은 암호화 메모리, 더 독립된 보안 코어. 신뢰할 부품을 줄이려고 새 부품을 추가하는 셈이고, 그 부품도 결국 누군가 설계한 실리콘이다. Caliptra 같은 오픈 RoT 가 의미 있는 이유가 여기 있다 — 믿어야 한다면, 최소한 읽을 수는 있어야 한다.

비용은 명확하다. 완화책은 성능을 먹고, TEE 는 운영 복잡도를 늘리고, attestation 은 검증 인프라를 요구한다. 그 비용을 치를지 말지는 결국 **내 위협 모델에 "운영자" 와 "옆 테넌트" 가 들어 있는가** 로 결정된다.

---

## References

[^uefi]: UEFI Forum, *UEFI Specification — Secure Boot and Driver Signing*. <https://uefi.org/specs/UEFI/2.10/32_Secure_Boot_and_Driver_Signing.html>
[^tcg]: Trusted Computing Group, *TPM 2.0 Library Specification*. <https://trustedcomputinggroup.org/resource/tpm-library-specification/>
[^kernel-tpm]: The Linux Kernel documentation, *TPM Event Log*. <https://docs.kernel.org/security/tpm/tpm_event_log.html>
[^win11]: Microsoft Learn, *Windows 11 requirements* — "System firmware: UEFI, Secure Boot capable." / "TPM: Trusted Platform Module (TPM) version 2.0." <https://learn.microsoft.com/en-us/windows/whats-new/windows-11-requirements>
[^caliptra]: CHIPS Alliance, *Caliptra* (GitHub README). <https://github.com/chipsalliance/Caliptra>
[^nist193]: NIST, *SP 800-193: Platform Firmware Resiliency Guidelines* (2018). <https://csrc.nist.gov/pubs/sp/800/193/final>
[^tpmfail]: Moghimi et al., *TPM-FAIL: TPM meets Timing and Lattice Attacks*, USENIX Security 2020. <https://tpm.fail/>
[^snp]: AMD, *AMD SEV-SNP: Strengthening VM Isolation with Integrity Protection and More* (white paper). <https://www.amd.com/content/dam/amd/en/documents/epyc-business-docs/white-papers/SEV-SNP-strengthening-vm-isolation-with-integrity-protection-and-more.pdf>
[^tdx]: Intel, *Intel Trust Domain Extensions (Intel TDX) Overview*. <https://www.intel.com/content/www/us/en/developer/tools/trust-domain-extensions/overview.html>
[^apple]: Apple, *Apple Platform Security — The Secure Enclave*. <https://support.apple.com/guide/security/secure-enclave-sec59b0b31ff/web>
[^foreshadow]: Van Bulck et al., *Foreshadow: Extracting the Keys to the Intel SGX Kingdom with Transient Out-of-Order Execution*, USENIX Security 2018. <https://foreshadowattack.eu/>
[^plundervolt]: Murdock et al., *Plundervolt: Software-based Fault Injection Attacks against Intel SGX*, IEEE S&P 2020. <https://plundervolt.com/>
[^meltdown]: Lipp et al., *Meltdown: Reading Kernel Memory from User Space*, USENIX Security 2018. <https://meltdownattack.com/meltdown.pdf>
[^spectre]: Kocher et al., *Spectre Attacks: Exploiting Speculative Execution*, IEEE S&P 2019. <https://spectreattack.com/spectre.pdf>
[^kernel-spectre]: The Linux Kernel documentation, *Spectre Side Channels*. <https://docs.kernel.org/admin-guide/hw-vuln/spectre.html>
[^rowhammer]: Kim et al., *Flipping Bits in Memory Without Accessing Them: An Experimental Study of DRAM Disturbance Errors*, ISCA 2014. <https://users.ece.cmu.edu/~yoonguk/papers/kim-isca14.pdf>
[^trrespass]: Frigo et al., *TRRespass: Exploiting the Many Sides of Target Row Refresh*, IEEE S&P 2020. <https://www.vusec.net/projects/trrespass/>
