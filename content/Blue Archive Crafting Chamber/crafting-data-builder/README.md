# SchaleDB 제조 데이터 빌더

SchaleDB의 공개 JSON을 다운로드하고 선물 우선 알고리즘에서 사용하는 `CRAFTING_TABLE[stage][nodeId]` 형식으로 변환한다. 노드 아이콘과 아이콘-노드 매니페스트도 함께 생성한다.

## 요구 사항

- Python 3.10 이상
- 최초 다운로드 시 인터넷 연결
- 외부 Python 패키지는 필요하지 않음

## 실행

```powershell
python build.py
```

또는

```powershell
cd "C:\Users\msp04\Desktop\Workspace\Obsidian Space\studyingidiot-digital-garden\content\Blue Archive Crafting Chamber\crafting-data-builder"
uv run --no-project python build.py
```

기본값은 글로벌 서버, 한국어 메타데이터, `./generated` 출력이다.

```powershell
python build.py --output-dir .\generated
python build.py --offline
python build.py --skip-icons
```

- `--offline`: 기존 `generated/raw`만 사용해 다시 변환
- `--skip-icons`: 노드 아이콘 다운로드 생략
- `--server jp|global|cn`: 서버 출시 여부 필터 변경
- `--language kr`: 아이템 메타데이터 언어 변경

## 출력

```text
generated/
├─ raw/
│  ├─ crafting.json
│  ├─ groups.json
│  ├─ items.json
│  └─ furniture.json
├─ icons/
│  ├─ Favor.png
│  ├─ Furniture.png
│  └─ ...
├─ crafting_table.json
├─ node_manifest.json
└─ validation_report.json
```

### `crafting_table.json`

```text
craftingTable[stage][nodeId] = List<CraftingResult>
```

```json
{
  "itemId": 5032,
  "itemType": "Gift",
  "giftGrade": "Normal",
  "probability": 0.0178,
  "minQuantity": 1,
  "maxQuantity": 1
}
```

최종 결과 확률은 다음과 같이 계산한다.

```text
resultProbability
    = nodeGroup.Weight / SUM(node.Groups[].Weight)
    * groupItem.Chance
```

같은 결과가 여러 그룹에서 나오면 확률을 합산한다. `node.Property`과 `ChanceGlobal`은 노드 자체의 출현 확률 계산에 사용되는 값이므로, 이미 화면에 나타난 노드의 결과 확률에는 곱하지 않는다.

### `node_manifest.json`

노드 ID, 단계, 품질, 한국어·영어 이름과 아이콘 ID를 보관한다. 동일 아이콘을 공유하는 노드들을 확인할 수 있도록 각 아이콘에 `nodeIds` 목록을 기록한다.

### `validation_report.json`

각 노드의 결과 확률 합계와 수량 범위를 검사한다. SchaleDB 확률의 반올림을 고려해 합계 `1.0 ± 0.02`를 허용한다.

## 선물 변환 규칙

```text
Category == Favor and Rarity == SR  -> Gift / Normal
Category == Favor and Rarity == SSR -> Gift / Advanced
```

일반 선물 가중치 `1`과 고급 선물 가중치 `3`은 데이터가 아니라 선택 알고리즘에서 적용한다.

## 주의 사항

- SchaleDB는 비공식 데이터베이스이며 라이브 JSON 스키마가 바뀔 수 있다.
- 필수 필드가 없거나 알려지지 않은 선물 등급이 나오면 빌드가 실패한다.
- 생성물의 `metadata.sources`에는 원본 URL, 파일 크기와 SHA-256 해시가 기록된다.
- SchaleDB 및 게임 이미지 자산을 재배포할 때는 별도의 이용 조건을 확인해야 한다.
