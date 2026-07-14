# 클릭 후 OCR 기반 제조 노드 스캐너

고정된 게임 화면에서 후보 노드 5개를 차례로 클릭하고 정보 패널의 한국어 노드명을 EasyOCR로 읽어 정확한 SchaleDB `NodeId` 목록으로 변환한다. 아이콘을 공유하는 `은은함`, `영롱함`, `반짝임`도 이름으로 구분한다.

## 안전 원칙

- 제조 확정 버튼은 다루지 않는다.
- `(stage, nameKr)` 완전 일치를 우선한다.
- 완전 일치가 실패하면 세 글자 이상 이름에 한해 복수 전처리 결과의 제한적 합의 보정을 허용한다.
- 한 슬롯이라도 인식하지 못하면 전체 스캔을 중단한다.
- 짧은 이름, 최인접 동률, 전처리 간 의견 불일치는 자동으로 채택하지 않는다.
- 정규화된 이름이 5글자 이상이면 합의 보정의 최대 편집 거리를 3으로 확장한다. 그보다 짧은 이름은 기존 최대 거리 2를 유지한다.
- 화면 해상도가 프로파일과 다르면 클릭하지 않는다.

## 설치

Python 3.10 이상이 필요하다. Windows에서는 가상 환경 사용을 권장한다.

```powershell
uv sync --extra test
```

EasyOCR 모델은 최초 실행 시 다운로드될 수 있다. GPU를 사용하지 않으면 기본 CPU 모드로 실행된다.

## 화면 프로파일 작성

`screen_profile.example.json`을 복사한 뒤 실제 고정 화면을 기준으로 값을 측정한다.

- `width`, `height`: 캡처 대상 모니터 해상도
- `stageClickPoints`: 단계별 후보 5개의 절대 화면 클릭 좌표
- `nodeNameRegion`: 클릭 후 표시되는 한국어 노드명만 포함하는 절대 화면 영역
- `ocrConfidenceThreshold`: 단일 고신뢰 exact match에 요구할 OCR confidence
- `relaxedExactConfidenceThreshold`: 3글자 이상 이름의 단일 exact match에 적용할 완화 confidence
- `relaxedExactMinimumNameLength`: 완화된 단일 exact match를 허용할 최소 이름 길이
- 안정화 관련 값: 애니메이션이 끝난 크롭을 판정하는 시간과 평균 픽셀 차이
- `fuzzyMinimumConfidence`: 합의 보정에 사용할 전처리별 최소 confidence
- `fuzzyMaximumDistance`: 실제 노드명과 허용할 최대 편집 거리
- `fuzzyMinimumNameLength`: 합의 보정을 허용할 최소 노드명 길이
- `fuzzyMinimumConsensusCount`: 같은 NodeId를 지목해야 하는 최소 전처리 수

OCR 판정은 고신뢰 exact match, 저신뢰 exact consensus, 3글자 이상 relaxed exact match, 제한된 알려진 오인식, fuzzy consensus 순서로 수행한다. 1~2글자 이름은 단일 저신뢰 결과로 확정하지 않는다.

예제의 좌표와 노드명 영역은 `0`인 자리표시자이므로 실제 측정 없이 실행할 수 없다.

## 실행

게임 화면과 프로파일의 해상도·창 위치·UI 배율을 맞춘 뒤 실행한다.

```powershell
uv run scan-crafting-nodes `
  --stage 1 `
  --profile .\screen_profile.json `
  --manifest ..\crafting-data-builder\generated\node_manifest.json `
  --crafting-table ..\crafting-data-builder\generated\crafting_table.json
```

성공 시 슬롯 순서를 보존한 `candidateNodeIds`와 클릭 좌표를 JSON으로 출력한다. 실패 시 exit code `2`를 반환하고 기본 `diagnostics/` 아래에 전체 화면, 노드명 크롭, OCR 결과와 근접 후보를 저장한다.

```json
{
  "success": true,
  "stage": 1,
  "candidateNodeIds": [1, 2, 3, 4, 13],
  "candidates": []
}
```

`CandidateNodeBatch.candidate_node_ids`를 선물 우선 알고리즘의 `SelectBestNode`에 전달한다. 선택 결과는 `find_first_candidate(batch, recommended_node_id)`로 다시 클릭할 슬롯과 좌표로 변환한다.

## 선물 우선 선택기

`GiftPrioritySelector`는 화면이나 마우스를 사용하지 않는 순수 계산 객체다. 일반 선물 가중치 `1`, 고급 선물 가중치 `3`으로 선물 기대 가치를 계산하고, 동률일 때만 가구 기대 수량을 비교한다.

```python
from pathlib import Path

from crafting_ocr import CraftingTable, GiftPrioritySelector

table = CraftingTable.from_json(
    Path("../crafting-data-builder/generated/crafting_table.json")
)
selector = GiftPrioritySelector(table)

decision = selector.select_best_node(
    stage=1,
    candidate_node_ids=[7, 1, 3, 5, 11],
)

print(decision.to_dict())
```

이 예제는 선물 기대 가치가 가장 높은 `반짝임`의 NodeId `3`을 추천한다.

핵심 결과는 다음과 같다.

```json
{
  "recommendedNodeId": 3,
  "giftScore": 0.6230290456431535,
  "furnitureScore": 0.06136929460580912,
  "tiedNodeIds": [3],
  "selectionReason": "highest-gift-score"
}
```

`evaluations`에는 실제로 다섯 후보의 NodeId와 선물·가구 점수가 모두 들어간다.

## 3단계 제조 자동화

`CraftingAutomationRunner`는 제조 슬롯 선택부터 1·2·3차 OCR 및 추천 노드 선택, 제조 확정까지 수행한다. `--all` 실행은 세 슬롯을 처리한 뒤 일괄 수령 과정도 실행한다.

자동화는 버튼 이미지를 확인하지 않고 `screen_profile.v1.json`의 `automation.waits` 시간만큼 기다린다. 따라서 게임 창 위치·해상도와 각 좌표를 실제 화면에 맞춰야 한다.

### 자동화 좌표

`automation`의 `(0, 0)`은 실행할 수 없는 자리표시자다. Window Spy의 `Screen` 좌표로 다음 값을 모두 채운다.

- `craftingStartPoints`: 목록 화면의 제조 시작 버튼 세 개
- `primaryMaterialPoint`, `primaryUnlockPoint`: 1차 재료와 개방 버튼
- `candidateReadyPoints`: 1·2·3차 개방 후 후보 화면을 준비하는 단계별 클릭 좌표
- `nodeConfirmPoints`: 각 단계의 노드 선택 확정 버튼
- `addMaterialPoint`, `additionalMaterialPoint`: 재료 추가 투입 버튼과 4초간 누를 재료
- `unlockPoints`: 2차·3차 개방 버튼
- `beginCraftingPoint`, `confirmCraftingPoint`: 최종 제조 시작과 확인
- `craftingAnimationSkipPoint`: 제조 확인 후 재생되는 애니메이션을 건너뛰는 클릭 좌표
- `collectAllPoint`, `collectConfirmPoint`: 목록 화면 일괄 수령과 확인
- `resultCollectAllPoint`, `resultDismissPoint`: 결과 화면 일괄 수령과 화면 닫기

`automation.waits`에는 각 클릭 이후 대기시간이 초 단위로 들어 있다. 같은 이름의 대기는 해당 동작이 끝난 직후부터 다음 동작 직전까지 적용된다.

| 설정 | 의미 |
|---|---|
| `startupSeconds` | `--execute` 시작 후 첫 제조 슬롯을 클릭하기 전 대기 |
| `afterCraftingSlotSeconds` | 목록에서 제조 시작 슬롯을 클릭한 후 대기 |
| `afterPrimaryMaterialSeconds` | 1차 재료를 한 번 클릭한 후 대기 |
| `afterPrimaryUnlockSeconds` | 1차 개방 버튼을 클릭한 후 대기 |
| `afterCandidateReadySeconds` | 각 단계의 `candidateReadyPoints`를 클릭한 후 OCR 시작 전 대기 |
| `afterRecommendedNodeSeconds` | 추천 노드를 처음 클릭한 뒤 노드 선택 확정 버튼을 누르기 전 대기 |
| `afterNodeConfirmBeforeRepeatSeconds` | 노드 선택 확정 버튼을 클릭한 뒤 추천 노드 좌표를 다시 클릭하기 전 대기, 기본 `0.5`초 |
| `afterNodeConfirmSeconds` | 추천 노드 좌표를 두 번째로 클릭한 뒤 다음 동작 전 대기 |
| `afterAddMaterialSeconds` | 재료 추가 투입 버튼을 클릭한 후 대기 |
| `materialHoldSeconds` | 2·3차 추가 재료를 마우스로 누르고 있는 시간, 기본 `4.0`초 |
| `afterMaterialHoldSeconds` | 추가 재료에서 마우스 버튼을 놓은 후 대기 |
| `afterNodeUnlockSeconds` | 2·3차 개방 버튼을 클릭한 후 후보 화면 준비 좌표를 누르기 전 대기 |
| `afterCraftingStartSeconds` | 최종 제조 시작 버튼을 클릭한 후 확인 창 대기 |
| `afterCraftingConfirmBeforeSkipSeconds` | 제조 확인 버튼을 클릭한 후 애니메이션 스킵 좌표를 누르기 전 대기 |
| `afterCraftingConfirmSeconds` | 애니메이션 스킵 좌표를 클릭한 후 목록 화면 복귀 대기 |
| `betweenCraftsSeconds` | 전체 실행에서 한 제조가 끝난 뒤 다음 슬롯 시작 전 추가 대기 |
| `afterCollectAllSeconds` | 목록 화면의 첫 번째 일괄 수령 클릭 후 확인 창 대기 |
| `afterCollectConfirmSeconds` | 일괄 수령 확인 버튼 클릭 후 결과 화면 대기 |
| `afterResultCollectAllSeconds` | 결과 화면의 두 번째 일괄 수령 클릭 직후 추가 대기, 기본 `0.0`초 |
| `resultDisplaySeconds` | 두 번째 일괄 수령 후 화면 중앙을 클릭하기 전 결과 표시 시간, 기본 `2.0`초 |
| `afterResultDismissSeconds` | 결과 화면 중앙 클릭 후 목록 화면 안정화 대기 |

두 번째 일괄 수령 후 중앙 클릭까지의 총 대기는 `afterResultCollectAllSeconds + resultDisplaySeconds`다. 기본값은 정확히 `2.0`초다.

### Dry-run

`--execute`가 없으면 프로파일과 제조 데이터를 검증하고 예정 동작만 출력한다. OCR, 클릭, 길게 누르기는 실행하지 않는다.

```powershell
uv run automate-crafting `
  --craft-slot 1 `
  --profile .\screen_profile.v1.json `
  --manifest ..\crafting-data-builder\generated\node_manifest.json `
  --crafting-table ..\crafting-data-builder\generated\crafting_table.json
```

### 단일 제조 실행

첫 실게임 검증은 반드시 첫 번째 슬롯 하나로 수행한다. `startupSeconds` 동안 게임 목록 화면으로 전환한다.

```powershell
uv run automate-crafting `
  --craft-slot 1 `
  --execute `
  --profile .\screen_profile.v1.json `
  --manifest ..\crafting-data-builder\generated\node_manifest.json `
  --crafting-table ..\crafting-data-builder\generated\crafting_table.json
```

### 제조 3회와 일괄 수령

```powershell
uv run automate-crafting `
  --all `
  --execute `
  --profile .\screen_profile.v1.json `
  --manifest ..\crafting-data-builder\generated\node_manifest.json `
  --crafting-table ..\crafting-data-builder\generated\crafting_table.json
```

OCR, 선택, 좌표 입력 중 하나라도 실패하면 즉시 중단하고 마지막 완료 상태와 action log를 JSON으로 출력한다. 자동 재시도와 다음 제조 슬롯 진행은 하지 않는다. 자동화 도중 마우스를 화면 왼쪽 위로 이동하면 PyAutoGUI failsafe가 동작한다.

## 테스트

```powershell
uv run --extra test pytest
```

실제 OCR 표본 테스트는 게임에서 `은은함`, `영롱함`, `반짝임` 제목 크롭을 수집한 뒤 별도 fixture로 추가해야 한다. 현재 자동 테스트는 manifest 정합성, 단계별 이름 변환, 클릭 순서, 안전 중단과 진단 저장을 검증한다.
