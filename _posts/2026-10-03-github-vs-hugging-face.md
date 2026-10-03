---
layout: post
title: "깃허브 vs 허깅페이스 — 둘 다 Git 인데 왜 따로 쓰나: 코드의 집과 모델의 집"
date: 2026-10-03 14:20:00 +0900
categories: [ai]
tags: [github, huggingface, git, git-lfs, xet, mlops, model-hub]
---

AI 프로젝트를 하다 보면 리포를 두 군데 만들게 된다. 코드는 **GitHub**, 모델 가중치와 데이터셋은 **Hugging Face**.
그런데 둘 다 Git 기반이다. 왜 하나로 안 되고 따로 쓰는 걸까.

결론부터 말하면 둘은 **같은 도구(Git) 위에 지은 다른 용도의 집**이다. GitHub 는 *사람이 읽고 고치는 코드*에 맞춰져 있고,
Hugging Face 는 *기계가 읽는 거대한 파일*(가중치, 데이터)에 맞춰져 있다. 이 글은 두 서비스의 공식 문서만 근거로 그 차이를 정리한다.

## 공통점 — 둘 다 Git 리포다

Hugging Face 공식 문서는 이렇게 시작한다.
*"Models, Spaces, and Datasets are hosted on the Hugging Face Hub as Git repositories"*([HF Hub 문서](https://huggingface.co/docs/hub/repositories)).
그래서 `git clone`, 커밋, 브랜치, PR 같은 익숙한 개념이 그대로 통한다. 차이는 **무엇을 넣도록 설계됐느냐**에서 난다.

## 차이 1 — 큰 파일을 대하는 태도

여기서 둘이 가장 크게 갈린다.

**GitHub** ([공식 문서](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github))

- 50MiB 넘는 파일은 Git 이 **경고**한다 (푸시는 된다).
- **100MiB 넘는 파일은 차단**한다. 그 이상은 Git LFS 를 써야 한다.
- 브라우저로 올리는 파일은 25MiB 까지다.
- Git LFS 를 써도 파일당 최대 크기가 정해져 있다: Free·Pro **2GB**, Team 4GB, Enterprise Cloud 5GB ([LFS 문서](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-git-large-file-storage)).

**Hugging Face** ([저장소 한도 문서](https://huggingface.co/docs/hub/storage-limits))

- 리포 구조 권장치로 **파일당 200GB 미만**, 리포당 파일 10만 개 미만, 폴더당 항목 1만 개 미만을 제시한다.
- 저장 백엔드로 **Xet** 을 쓴다. 문서 설명으로는 *"chunk-level deduplication, smaller uploads, and faster downloads than Git LFS"*,
  즉 파일을 청크 단위로 중복 제거해서 Git LFS 보다 업로드는 작게, 다운로드는 빠르게 한다([Xet 문서](https://huggingface.co/docs/hub/xet/index)).

수치를 나란히 놓으면 이 차이가 확 보인다. GitHub 는 **2GB 짜리 파일 하나**에서 이미 벽(Free 기준)을 만나는데,
요즘 오픈 모델 가중치는 파일 하나가 수 GB 인 경우가 흔하다. 반대로 HF 는 파일 하나가 수십 GB 여도 정상 사용 범위다.
**GitHub 는 큰 파일을 '예외'로, HF 는 '기본'으로 다룬다.**

## 차이 2 — 저장 용량과 요금의 기준

HF 문서의 저장 플랜 표를 보면, 무료 계정은 **비공개 저장소 100GB**, 공개 저장소는 "best-effort"(가능한 한 넉넉히)다.
Team·Enterprise 조직은 비공개 저장 공간이 **멤버당 1TB** 포함이다. 대신 HF 는 공개 저장소도 "커뮤니티에 실제로 가치 있는 것"을 올려 달라고 분명히 요청한다.
좋아요·다운로드 수 같은 지표를 그 예로 든다.

즉 HF 의 무료 공개 저장소는 **공유를 전제로 한 넉넉함**이다. 개인 백업 창고로 쓰는 곳이 아니다.

## 차이 3 — 리포 첫 화면에 무엇이 오는가

**GitHub** 리포의 얼굴은 README 와 코드 트리, 그리고 이슈·PR·Actions(CI/CD)다. 질문은 "이 코드 어떻게 빌드하지?"다.

**Hugging Face** 모델 리포의 얼굴은 **모델 카드**다. 공식 문서에 따르면 모델 카드는 메타데이터가 붙은 Markdown 파일(리포의 `README.md`)이고,
모델이 무엇인지, **의도된 용도와 한계**, 학습 데이터, 평가 결과 등을 담아야 한다([모델 카드 문서](https://huggingface.co/docs/hub/model-cards)).
질문은 "이 모델 어디에 써도 되고, 어디에 쓰면 안 되지?"다.

HF 에는 **게이티드 모델**도 있다. 모델 작성자가 접근 요청을 켜 두면, 사용자는 자기 연락처(사용자명·이메일)를 작성자와 공유하는 데 동의해야
파일을 받을 수 있다([게이티드 모델 문서](https://huggingface.co/docs/hub/models-gated)). 코드 리포에는 없는, 모델 배포 특유의 장치다.

## 차이 4 — "실행"의 의미

GitHub 에서 실행은 주로 **GitHub Actions** 다. 테스트하고, 빌드하고, 배포하는 파이프라인이다.

HF 에는 **Spaces** 가 있다. 공식 문서 표현으로 *"ML-powered demos"* 를 몇 분 만에 만들어 배포하는 곳이고,
SDK 로 **Gradio, Docker, static HTML** 을 고를 수 있다([Spaces 문서](https://huggingface.co/docs/hub/spaces-overview)).
모델 리포 옆에 바로 써 볼 수 있는 데모를 붙이는 셈이다.

## 한눈에 보기

| | GitHub | Hugging Face Hub |
|---|---|---|
| 기반 | Git | Git (+ Xet 저장 백엔드) |
| 주인공 | 코드 | 모델 가중치, 데이터셋, 데모 |
| 큰 파일 | 100MiB 초과 차단 → LFS (파일당 2~5GB, 플랜별) | 파일당 200GB 미만 권장, 청크 단위 중복 제거 |
| 리포의 얼굴 | README, 코드, 이슈·PR | 모델 카드 (용도·한계·평가) |
| 접근 통제 | 공개/비공개 리포 | 공개/비공개 + 게이티드(동의 후 다운로드) |
| 실행 | Actions (CI/CD) | Spaces (Gradio·Docker·HTML 데모) |
| 무료 저장 (공식 표 기준) | — | 공개 best-effort, 비공개 100GB |

## 그래서 어떻게 나눠 쓰나

실무에서 흔한 조합은 이렇다.

- **코드, 학습·추론 스크립트, 설정, 테스트 → GitHub.** 리뷰와 CI 가 필요한 건 전부 여기.
- **학습된 가중치, 토크나이저, 데이터셋 → Hugging Face.** 모델 카드에 용도와 한계를 적는다.
- **데모 → HF Spaces.** 모델 리포와 같은 곳에 둔다.
- **둘의 동기화 → GitHub Actions.** HF 는 공식 `huggingface/hub-sync` 액션을 제공한다. GitHub 리포를 Space(모델·데이터셋 리포도 가능)와 자동으로 맞춰 준다([HF 문서](https://huggingface.co/docs/hub/spaces-github-actions)).

피해야 할 것도 있다.

- 가중치를 GitHub 에 LFS 로 밀어 넣지 말 것. Free 플랜이면 파일당 2GB 벽을 바로 만난다.
- 반대로 HF 를 코드 협업의 중심으로 쓰지 말 것. 이슈 트래킹, 코드 리뷰, CI 는 GitHub 쪽 도구가 훨씬 두껍다.
- HF 공개 저장소를 개인 백업용으로 쓰지 말 것. 공식 문서가 직접 "커뮤니티에 가치 있는 것"을 요청한다.

## 정리

같은 Git 이지만, GitHub 는 **사람이 고치는 작은 텍스트 파일 수천 개**에, Hugging Face 는 **기계가 읽는 거대한 바이너리 몇 개**에 최적화돼 있다.
그래서 AI 프로젝트의 정답은 둘 중 하나가 아니라 **"코드는 GitHub, 모델은 HF, 그 사이는 Actions"**다.

## References

- Hugging Face Hub, *Repositories* — <https://huggingface.co/docs/hub/repositories>
- Hugging Face Hub, *Storage limits* — <https://huggingface.co/docs/hub/storage-limits>
- Hugging Face Hub, *Xet: our Storage Backend* — <https://huggingface.co/docs/hub/xet/index>
- Hugging Face Hub, *Model Cards* — <https://huggingface.co/docs/hub/model-cards>
- Hugging Face Hub, *Gated models* — <https://huggingface.co/docs/hub/models-gated>
- Hugging Face Hub, *Spaces Overview* — <https://huggingface.co/docs/hub/spaces-overview>
- Hugging Face Hub, *Managing Spaces with GitHub Actions* — <https://huggingface.co/docs/hub/spaces-github-actions>
- GitHub Docs, *About large files on GitHub* — <https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github>
- GitHub Docs, *About Git Large File Storage* — <https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-git-large-file-storage>
