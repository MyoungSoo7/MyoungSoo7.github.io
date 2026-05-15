---
layout: page
title: Progress
permalink: /progress/
---

진행 중인 변경 작업과 다음에 손댈 항목을 모아두는 작업 로그입니다. 완료된 운영 기록은 [/about/](/about/) 의 운영 기록 섹션과 블로그 포스트로 옮깁니다.

*Last updated: 2026-05-16 (KST)*

---

## 🔧 진행 중인 변경

### 🎬 동영상 강의 플랫폼 — [lemuel-academy](https://github.com/MyoungSoo7/lemuel-academy)

Class101/탈잉 스타일 MSA. Spring Boot 4 Kotlin × 4 + Next.js 15 × 3 + ffmpeg HLS 트랜스코딩.

| 서비스 | 역할 |
|--------|------|
| user-service | JWT 인증 + 진도 + 즐겨찾기 |
| catalog-service | 강의/챕터/레슨/리뷰 + 검수 워크플로 |
| media-service + ffmpeg-worker | R2 업로드 → HLS 1080p/720p/480p |
| api-gateway | Spring Cloud Gateway + JwtFilter |
| learner / creator-studio / admin | Next.js 3개 (Tailwind + hls.js) |

**인프라**: 온프레미스 K3s 클러스터 (5 노드, 100% 자체호스팅).

---

### 일원 SSD 1TB 통합 — hot / cold 스토리지 티어 분리

**현재 상태**: SSD 1TB 추가, 노드 라벨링 + nodeSelector 작업 중

**배경**
- 일원 노드는 이미 `4TB HDD` 가 `bind mount` 로 K3s storage 풀에 통합되어 있음 (2026-05-12 작업, [블로그 포스트](/2026/05/12/k3s-local-path-storage-hdd-bind-mount/))
- HDD 단일 풀은 PostgreSQL / Redis 같이 IOPS 민감한 워크로드와 ASAT 트레이닝 오디오 같이 용량 큰 워크로드가 같은 디스크를 다툼

**계획**
- 일원에 `storage-tier=hot` (SSD) / `storage-tier=cold` (HDD) 노드 라벨 부여
- StorageClass 두 개: `local-path-hot` (SSD path) / `local-path-cold` (HDD path)
- PVC 의 `storageClassName` + Pod 의 `nodeSelector` 조합으로 hot / cold 분리
- 마이그레이션: 기존 PVC 는 Velero PodVolumeBackup → 새 StorageClass 로 restore

**남은 일**
- [ ] SSD 마운트 포인트 확정 (`/mnt/ssd-1tb`)
- [ ] `local-path-config` ConfigMap 두 path 등록 + K3s 자동 복원 함정 재대응
- [ ] PostgreSQL / Redis 우선 hot 으로 이동, ASAT MinIO 는 cold 유지
- [ ] Velero hourly-critical 백업으로 안전망 확보 후 cutover

---

## 📋 TODO

(우선순위 / 마감 / 비고는 추가하면서 정리)

- [ ] (placeholder) 추가하면서 채우기

---

## ✅ 완료된 항목 (최근)

진행 중 → 완료 전환된 작업은 짧은 한 줄 + 블로그 포스트 링크로만 남깁니다.

- 2026-05-12 — K3s 3-master HA 마이그레이션 (SQLite → embedded etcd) · [postmortem](/2026/05/12/k3s-3master-ha-sqlite-etcd-migration/)
- 2026-05-12 — 솔로몬 WiFi 3-NIC floating VIP failover · [postmortem](/2026/05/12/solomon-wifi-3nic-vip-floating-failover/)
- 2026-05-12 — 일원 4TB HDD `bind mount` 로 K3s storage 풀 통합 · [postmortem](/2026/05/12/k3s-local-path-storage-hdd-bind-mount/)
- 2026-05-12 — Spring Boot 4 의존성 지옥 디버깅 · [postmortem](/2026/05/12/spring-boot-4-dependency-hell-debugging/)
