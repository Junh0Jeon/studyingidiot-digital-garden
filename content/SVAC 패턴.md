```
이 구조가 어떤 구조나면, 다음과 같아.
sensor : 기본적으로는 validator가 필요한 context를 만들어내는 객체. 여기에 한 단계 더 나아간다면, context를 만들어내는데 필요한 데이터를 제공하는 이벤트를 구독해서 context가 변할 때마다 외부에 Action<context> OnContextChanged를 발행할 수 있음.
validator : 기본적으로는 context를 받아서 bool을 return하는 메소드들을 제공하며, 'Policy'를 담당함. 어떤 상황에서 되고, 안되고 그런 것들을 판정하는 객체. 여기에 한 단계 더 나아간다면, bool을 return하는게 아니라 result DTO를 return할 수도 있음.
actor : 어떤 작업, 행동을 실제로 하는 객체. 이 객체 스스로는 어떤 판정도 하지 않으며, 그저 아무 맥락 없이도 작동을 수행하는 메서드를 제공함.
controller : 앞의 세개의 조율자이자 encapsulize하는 주체. 실제로는 'actor의 표면'으로써 존재하며 행동한다. 외부에는 actor의 메서드와 같은 시그니쳐 메서드를 표면으로 가지고 있으며, 실제로는 sensor로부터 context를 받고 validator로부터 policy에 기반한 act가능 여부를 받고 actor의 act를 실행하거나 실행하지 않는다.
```

등장하게 된 배경
Actor에 대해서 '특정 조건(외부 조건)이 필요하고, 그 조건(policy)의 변동성이 존재하는 상황'이었음. `(Dropship에 대해서 Landing, TakeOff이 있는데 이 기능이 여러 조건을 탔음. 그런데 나는 Dropship을 마치 외부 에셋처럼 만들길 바랬음. 딱히 외부 조건 없이 그냥 문열고 문닫고 이륙하고 착륙하는 메서드를 제공하길 원했음.)`
Actor를 최대한 분리시켜 만들고 싶었고, 그 결과로 나옴.

단점
- 작은 기능에는 과함. 하나의 Actor에 Sensor, Context, Validator, Controller가 붙음.
- 가독성이 떨어짐(근데 이건 책임 분리에서 오는 trade off)
- 변경 지점이 context, sensor, validator임.


---
### **Sensor-Validator-Actor-Controller 패턴**

`Sensor-Validator-Actor-Controller` 패턴은 외부 에셋, 독립 기능, 또는 프로젝트의 세부 구현 객체를 프로젝트 도메인에 맞는 안전한 표면으로 감싸기 위한 구조이다.

핵심 의도는 다음이다.

```text
외부 객체나 Actor는 우리 프로젝트의 규칙을 모른다.
따라서 실행 조건과 프로젝트 맥락은 별도 객체에서 판단하고,
검증된 요청만 실제 실행 객체에게 전달한다.
```

**구성 요소**

```text
Sensor
- 현재 상태를 읽어 Context를 만든다.
- Validator가 판단하는 데 필요한 데이터를 모은다.
- 필요하다면 관련 상태 변화 이벤트를 구독하고, Context가 바뀔 때 OnContextChanged를 발행한다.

Validator
- Context를 받아 실행 가능 여부를 판단한다.
- “어떤 상황에서 되고, 어떤 상황에서 안 되는가”라는 정책을 담당한다.
- 단순 bool을 반환할 수도 있고, 실패 이유를 포함한 Result DTO를 반환할 수도 있다.

Actor
- 실제 행동을 수행한다.
- 스스로 정책 판단을 하지 않는다.
- 외부 에셋 자체일 수도 있고, 외부 에셋 호출을 감싼 Adapter일 수도 있다.

Controller
- 외부에 노출되는 도메인 표면이다.
- Sensor, Validator, Actor를 조율한다.
- 외부 호출자는 Actor를 직접 호출하지 않고 Controller를 호출한다.
- 실제로는 Actor의 기능을 프로젝트 규칙에 맞게 안전하게 노출하는 역할을 한다.
```

**기본 코드 흐름**

```text
외부 호출
→ Controller.RequestAction()
→ Sensor.CreateContext()
→ Validator.Validate(context)
→ 실패 시 중단 또는 실패 결과 반환
→ 성공 시 Actor.Act()
```

예시는 이런 형태다.

```csharp
public void RequestDepart()
{
    DropshipContext context = sensor.CreateContext(); // Context는 DTO
    ValidationResult result = validator.ValidateDepart(context); // Result는 DTO. 간단하게 하려면 bool로 할 수도 있음.

    if (result.IsValid == false)
    {
        return;
    }

    actor.Depart(); // actor는 외부 Dropship 에셋인 상황
}
```

중요한 점은 Controller가 외부 에셋의 메서드를 그대로 복사하는 얇은 wrapper가 아니라, **프로젝트의 도메인 언어로 행동을 노출해야 한다**는 것이다.

```text
덜 좋은 표면:
DropshipController.PlayAnimation("Launch")

좋은 표면:
DropshipController.RequestDepartToStage(stageId)
```

**의도**

이 패턴의 의도는 외부 객체의 API나 내부 구현 방식이 프로젝트 전체에 직접 퍼지는 것을 막는 것이다.

외부 에셋은 보통 이런 기능을 제공할 수 있다.

```text
PlayAnimation("Launch")
SetTarget(position)
OpenDoor()
```

하지만 프로젝트에서 실제로 의미 있는 행동은 보통 이런 식이다.

```text
RequestDepartToStage()
RequestOpenBoardingGate()
RequestReturnToHub()
```

Controller는 외부 에셋의 기능을 프로젝트 맥락에 맞는 행동으로 다시 정의한다.  
Validator는 그 행동이 가능한 상황인지 판단한다.  
Sensor는 판단에 필요한 현재 상태를 Context로 만든다.  
Actor는 검증된 요청을 받아 실제 실행만 담당한다.

**적절한 상황**

이 패턴은 다음 상황에 적절하다.

```text
- 외부 에셋이나 독립 기능을 프로젝트 규칙에 맞게 감싸야 할 때
- 실행 조건이 여러 개이고, 조건이 도메인 규칙으로서 의미가 있을 때
- 하나의 행동이 버튼, 트리거, 네트워크, 씬 이벤트 등 여러 경로에서 호출될 때
- 실패 이유를 UI, 로그, 사운드, 튜토리얼 등에 연결해야 할 때
- 행동 실행 전 현재 상태를 명확한 Context로 만들 필요가 있을 때
- Actor는 재사용하고, 정책만 상황별로 바꾸고 싶을 때
- 테스트에서 “판정”과 “실행”을 따로 확인하고 싶을 때
```

덜 적절한 상황은 다음이다.

```text
- 조건 없는 단순 실행일 때
- 한 곳에서만 호출되는 작은 기능일 때
- 실패 처리나 정책 판단이 거의 없을 때
- 단순 UI 토글이나 일회성 연출처럼 도메인 규칙이 약한 기능일 때
- 프로토타입 단계에서 구조 비용이 구현 속도보다 클 때
```

**Validation 변경 이벤트 흐름**

UI에서 “현재 이 행동이 가능한지”를 즉시 표시해야 하는 경우, 다음 흐름을 사용할 수 있다.

```text
외부 상태 변화
→ Sensor가 관련 이벤트 수신
→ Sensor가 새 Context 생성
→ Sensor.OnContextChanged(context) 발행
→ Controller가 Context 변경 수신
→ Validator.Validate(context)
→ Controller가 최신 ValidationResult와 비교
→ 결과가 달라졌으면 Controller.OnValidationResultChanged(result) 발행
→ UI가 버튼 활성화, 비활성화, 안내 문구 등을 갱신
```

이 방식에서는 UI가 Sensor나 Validator를 직접 알 필요가 없다.  
UI는 Controller의 현재 검증 결과와 변경 이벤트만 바라보면 된다.

예시 흐름은 다음과 같다.

```csharp
private void HandleContextChanged(DropshipContext context)
{
    ValidationResult result = validator.ValidateDepart(context);
    UpdateDepartValidationResult(result);
}


private void UpdateDepartValidationResult(ValidationResult result)
{
    if (latestDepartValidationResult.Equals(result) == true)
    {
        return;
    }

    latestDepartValidationResult = result;
    OnDepartValidationResultChanged?.Invoke(result);
}
```

이때 캐싱된 ValidationResult는 UI 표시용 상태로 보는 것이 좋다.  
실제 행동 요청이 들어왔을 때는 실행 직전에 다시 Context를 만들고 Validator를 통과시키는 흐름이 안전하다.

**장점**

```text
- 정책 판단과 실제 실행이 분리된다.
- 외부 에셋 API가 프로젝트 전체에 퍼지는 것을 막는다.
- Controller가 안전한 단일 진입점이 된다.
- 프로젝트 도메인 언어로 public API를 만들 수 있다.
- Validator를 테스트하기 쉽다.
- Actor를 정책과 무관하게 재사용하기 쉽다.
- 실패 이유를 ValidationResult로 구조화하기 좋다.
- UI가 현재 행동 가능 여부를 표시하기 쉽다.
- 문제가 생겼을 때 Sensor, Validator, Actor, Controller 중 어느 책임의 문제인지 나누어 볼 수 있다.
- 외부 에셋 교체 시 영향 범위를 Actor 또는 ActorAdapter 근처로 줄일 수 있다.
```

**순수 단점**

```text
- 타입과 파일 수가 늘어난다.
- 단순 기능에는 구조 비용이 크다.
- 실행 흐름을 이해하려면 여러 파일을 오가야 한다.
- 변경 하나가 Context, Sensor, Validator에 함께 퍼질 수 있다.
- 공통 흐름의 반복 코드가 생길 수 있다.
- 팀원이 패턴을 모르면 탐색 비용이 커진다.
- 비동기 실행이 섞이면 Context, Validator, Actor, Controller 경계가 무거워질 수 있다.
```

**주의사항**

```text
- Controller는 외부 에셋 API를 그대로 복사하지 말고 도메인 행동을 노출해야 한다.
- Validator는 정책만 담당하고, 실제 실행이나 Unity 오브젝트 조작을 하지 않아야 한다.
- Actor는 실행만 담당하되, 자기 내부 상태 일관성을 지키는 최소한의 방어는 가질 수 있다.
- Context는 판정에 필요한 최소 정보만 담는 스냅샷으로 유지하는 것이 좋다.
- Controller에 UI, 사운드, 저장, 로그, 씬 전환 책임이 과도하게 몰리지 않게 해야 한다.
- 캐싱된 ValidationResult는 UI 표시용 힌트로 보고, 실제 실행 시점에는 다시 검증하는 것이 안전하다.
- 모든 기능에 강제하지 말고, 실행 조건과 도메인 규칙이 의미 있는 기능에 선택적으로 적용하는 것이 좋다.
```

**요약**

```text
Sensor-Validator-Actor-Controller 패턴은
Context 수집, 정책 판정, 실제 실행, 외부 표면을 분리해서
외부 에셋이나 독립 기능을 프로젝트 도메인 규칙에 맞게 감싸는 구조이다.
```

한 문장으로 줄이면:

> 외부 Actor를 직접 노출하지 않고, Sensor가 만든 Context와 Validator의 정책 판정을 거친 뒤, Controller라는 프로젝트 도메인 표면을 통해서만 Actor를 실행하게 만드는 패턴이다.