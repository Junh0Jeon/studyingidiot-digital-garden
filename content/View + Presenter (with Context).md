# View + Presenter (with Context)

## 계기

특정 Model의 상태를 표현하는 방식은 하나로 고정되지 않을 수 있다.

처음에는 `Debug.Log`로만 표현할 수도 있고,
나중에는 하나의 UI에서 표현할 수도 있고,
또 다른 UI나 이펙트, 사운드, 선택 표시 오브젝트에서 같은 상태를 다른 방식으로 표현할 수도 있다.

이때 각 표현 객체가 Model을 직접 참조해서 필요한 데이터를 알아서 꺼내가게 만들면,
표현 방식이 늘어날수록 Model에 대한 의존성이 여러 곳으로 퍼진다.

그래서 중간에 View 레벨의 읽기 전용 상태 객체를 하나 만들고,
그 상태 객체를 여러 Presenter에게 전달해서 각자 렌더링하게 만들 수 있다.

```text
Model
-> View 또는 Viewer가 Model 변경을 감지
-> View가 표현에 필요한 Context를 생성
-> 여러 Presenter에게 Render(context) 호출
```

이 구조를 임시로 부르면 `View + Presenter (with Context)`라고 할 수 있다.

## 일반화된 구조

이 구조의 핵심은 `View`가 Model의 현재 상태를 표현용 데이터로 변환하고,
`Presenter`는 그 데이터를 받아 자기 방식으로 표현한다는 점이다.

```text
Model
- 실제 도메인 상태를 가진다.
- 상태 변경 이벤트를 발행한다.

View 또는 Viewer
- Model의 변경 이벤트를 구독한다.
- 현재 Model 상태를 표현에 필요한 Context로 변환한다.
- Presenter 목록을 관리한다.
- 모든 Presenter에게 Render(context)를 호출한다.

Context
- View가 Presenter에게 전달하는 읽기 전용 표현 데이터다.
- Model 전체가 아니라, 이 View가 표현하기 위해 필요한 상태만 담는다.
- 특정 Presenter 하나가 아니라 여러 Presenter가 공유할 수 있는 상태 스냅샷이다.

Presenter
- Context를 받아 실제 시각 표현으로 바꾼다.
- Text, Image, Button 상태, Debug.Log, Effect, Sound 같은 구체적인 표현을 담당한다.
- Model을 직접 알 필요가 없다.
```

코드로 쓰면 대략 이런 모양이 된다.

```csharp
public readonly struct SomeViewerContext
{
    public string Title { get; }
    public bool IsEnabled { get; }
    public int Count { get; }

    public SomeViewerContext(string title, bool isEnabled, int count)
    {
        Title = title;
        IsEnabled = isEnabled;
        Count = count;
    }
}
```

```csharp
public abstract class SomeViewerPresenter : MonoBehaviour
{
    public abstract void Render(SomeViewerContext context);
    public abstract void Clear();
}
```

```csharp
public sealed class SomeViewer : MonoBehaviour
{
    [SerializeField]
    private SomeViewerPresenter[] presenters;

    private SomeModel model;

    public void Initialize(SomeModel model)
    {
        this.model = model;
        this.model.Changed += Render;

        Render();
    }

    private void OnDestroy()
    {
        if (model == null)
        {
            return;
        }

        model.Changed -= Render;
    }

    private void Render()
    {
        SomeViewerContext context = CreateContext();

        foreach (SomeViewerPresenter presenter in presenters)
        {
            presenter.Render(context);
        }
    }

    private SomeViewerContext CreateContext()
    {
        return new SomeViewerContext(
            model.Title,
            model.IsEnabled,
            model.Count);
    }
}
```

여기서 `SomeViewerPresenter`라는 이름을 쓰고 있지만,
역할만 보면 `Renderer`, `Display`, `Presentation`에 더 가까울 수도 있다.

전통적인 MVP의 Presenter는 보통 View와 Model 사이에서 흐름을 조정한다.
반면 이 구조의 Presenter는 이미 만들어진 Context를 받아서 자기 표현만 갱신한다.

그래서 이 구조는 전통적인 MVP라기보다는 다음 개념들이 섞여 있다.

```text
Observer
- View가 Model 변경 이벤트를 구독한다.

Presentation Model 또는 ViewModel Snapshot
- Context가 표현에 필요한 상태를 읽기 전용으로 묶는다.

Strategy
- 여러 Presenter가 같은 Context를 서로 다른 방식으로 표현한다.

Composite에 가까운 fan-out
- View가 Presenter 목록 전체에 Render를 전파한다.
```

## SpaceMapViewer 예시

SpaceMap의 Orbit 선택 상태를 여러 방식으로 표현해야 한다고 하자.

프로토타입 단계에서는 선택된 Orbit과 Stage 정보를 `Debug.Log`로만 보고 싶을 수 있다.
이후에는 오른쪽 상세 정보 UI에 표시하고,
나중에는 Orbit 위에 선택 이펙트를 띄우거나 진입 버튼의 활성 상태를 바꾸고 싶을 수 있다.

이때 `SpaceMapViewer`가 현재 선택 상태를 Context로 만들고,
여러 Presenter에게 같은 Context를 전달하게 할 수 있다.

```csharp
/// <summary>
/// SpaceMapViewer가 Presenter에게 전달하는 현재 선택 상태 읽기 전용 데이터입니다.
/// </summary>
public readonly struct SpaceMapViewerContext
{
    #region Properties

    /// <summary>
    /// 현재 선택된 Orbit 읽기 전용 데이터입니다.
    /// </summary>
    public SpaceMapManager.OrbitView OrbitView { get; }

    /// <summary>
    /// 현재 선택된 Orbit에 Stage가 있는지 여부입니다.
    /// </summary>
    public bool HasStage { get; }

    /// <summary>
    /// 현재 선택된 Orbit에 배치된 Stage 읽기 전용 데이터입니다.
    /// </summary>
    public SpaceMapManager.StageView StageView { get; }

    /// <summary>
    /// 현재 선택된 Orbit의 Stage 진입 가능 상태입니다.
    /// </summary>
    public SpaceMapManager.OrbitConfirmState ConfirmState { get; }

    /// <summary>
    /// 현재 선택된 Orbit의 Stage 진입 확정 가능 여부입니다.
    /// </summary>
    public bool IsConfirmable => ConfirmState == SpaceMapManager.OrbitConfirmState.Confirmable;

    #endregion



    #region Object Lifecycles

    /// <summary>
    /// 현재 선택 상태 읽기 전용 데이터를 생성합니다.
    /// </summary>
    /// <param name="orbitView">현재 선택된 Orbit 읽기 전용 데이터입니다.</param>
    /// <param name="hasStage">현재 선택된 Orbit에 Stage가 있는지 여부입니다.</param>
    /// <param name="stageView">현재 선택된 Orbit에 배치된 Stage 읽기 전용 데이터입니다.</param>
    /// <param name="confirmState">현재 선택된 Orbit의 Stage 진입 가능 상태입니다.</param>
    public SpaceMapViewerContext(
        SpaceMapManager.OrbitView orbitView,
        bool hasStage,
        SpaceMapManager.StageView stageView,
        SpaceMapManager.OrbitConfirmState confirmState)
    {
        OrbitView = orbitView;
        HasStage = hasStage;
        StageView = stageView;
        ConfirmState = confirmState;
    }

    #endregion
}
```

```csharp
/// <summary>
/// SpaceMapViewer가 전달한 선택 상태를 실제 시각 표현으로 변환하는 Presenter 기본 클래스입니다.
/// </summary>
public abstract class SpaceMapViewerPresenter : MonoBehaviour
{
    #region Public APIs

    /// <summary>
    /// 현재 선택 상태를 표현합니다.
    /// </summary>
    /// <param name="context">현재 선택 상태 읽기 전용 데이터입니다.</param>
    public abstract void Render(SpaceMapViewerContext context);

    /// <summary>
    /// 현재 표현 중인 선택 상태 표시를 제거합니다.
    /// </summary>
    public abstract void Clear();

    #endregion
}
```

`SpaceMapViewer`는 Presenter 목록을 가지고 있다가,
Model 변경 이벤트 또는 Model 변경 이벤트를 위임받은 객체의 이벤트를 구독해서 렌더링을 전파한다.

```csharp
public sealed class SpaceMapViewer : MonoBehaviour
{
    [SerializeField]
    private SpaceMapViewerPresenter[] presenters;

    private SpaceMapManager spaceMapManager;

    public void Initialize(SpaceMapManager spaceMapManager)
    {
        this.spaceMapManager = spaceMapManager;
        this.spaceMapManager.SelectedOrbitChanged += Render;

        Render();
    }

    private void OnDestroy()
    {
        if (spaceMapManager == null)
        {
            return;
        }

        spaceMapManager.SelectedOrbitChanged -= Render;
    }

    private void Render()
    {
        SpaceMapViewerContext context = CreateContext();

        foreach (SpaceMapViewerPresenter presenter in presenters)
        {
            presenter.Render(context);
        }
    }

    private SpaceMapViewerContext CreateContext()
    {
        SpaceMapManager.OrbitView orbitView = spaceMapManager.SelectedOrbitView;
        bool hasStage = spaceMapManager.TryGetStageView(orbitView, out SpaceMapManager.StageView stageView);
        SpaceMapManager.OrbitConfirmState confirmState = spaceMapManager.GetConfirmState(orbitView);

        return new SpaceMapViewerContext(
            orbitView,
            hasStage,
            stageView,
            confirmState);
    }
}
```

그러면 구체적인 표현은 Presenter 단위로 분리할 수 있다.

```csharp
public sealed class SpaceMapDebugLogPresenter : SpaceMapViewerPresenter
{
    public override void Render(SpaceMapViewerContext context)
    {
        if (context.HasStage == false)
        {
            Debug.Log($"Selected Orbit: {context.OrbitView.Id}, Stage: None");
            return;
        }

        Debug.Log(
            $"Selected Orbit: {context.OrbitView.Id}, " +
            $"Stage: {context.StageView.Id}, " +
            $"Confirmable: {context.IsConfirmable}");
    }

    public override void Clear()
    {
    }
}
```

```csharp
public sealed class SpaceMapStageInfoPresenter : SpaceMapViewerPresenter
{
    [SerializeField]
    private TextMeshProUGUI stageNameText;

    [SerializeField]
    private Button confirmButton;

    public override void Render(SpaceMapViewerContext context)
    {
        stageNameText.text = context.HasStage
            ? context.StageView.Name
            : "Empty Orbit";

        confirmButton.interactable = context.IsConfirmable;
    }

    public override void Clear()
    {
        stageNameText.text = string.Empty;
        confirmButton.interactable = false;
    }
}
```

```csharp
public sealed class SpaceMapOrbitHighlightPresenter : SpaceMapViewerPresenter
{
    [SerializeField]
    private OrbitHighlightEffect highlightEffect;

    public override void Render(SpaceMapViewerContext context)
    {
        highlightEffect.Show(context.OrbitView.Position);
        highlightEffect.SetConfirmable(context.IsConfirmable);
    }

    public override void Clear()
    {
        highlightEffect.Hide();
    }
}
```

이렇게 하면 같은 선택 상태를 여러 표현 방식으로 확장할 수 있다.

```text
SpaceMapViewerContext
-> DebugLogPresenter
-> StageInfoPresenter
-> OrbitHighlightPresenter
-> ConfirmButtonPresenter
```

각 Presenter는 `SpaceMapManager`를 직접 알 필요가 없다.
자신이 받은 Context 안에서 필요한 값만 읽고 자기 UI 또는 표현 객체를 갱신하면 된다.

## MVP와의 차이

전통적인 MVP에서는 Presenter가 중심에 있다.

```text
View
-> Presenter
-> Model
-> Presenter
-> View 갱신
```

Presenter는 View의 입력을 받고,
Model을 조회하거나 변경하고,
View 인터페이스를 호출해서 화면을 갱신한다.

반면 이 구조에서는 View 또는 Viewer가 Model 변경을 감지하고 Context를 만든다.
Presenter는 그 Context를 받아서 자신의 표현을 갱신한다.

```text
Model 변경
-> Viewer가 Context 생성
-> Presenter.Render(context)
```

즉 이 구조의 Presenter는 MVP의 Presenter보다 더 수동적이다.
Model과 View 사이의 조정자라기보다는, Context를 해석하는 표현 전략에 가깝다.

그래서 이름을 더 정확하게 붙인다면 다음 쪽이 더 어울릴 수도 있다.

```text
SpaceMapViewerRenderer
SpaceMapSelectionRenderer
SpaceMapViewerPresentation
SpaceMapViewerDisplay
```

다만 Unity에서는 `Presenter`라는 이름을 사용해도 의미가 완전히 틀리지는 않는다.
중요한 것은 팀 안에서 이 Presenter가 Model 흐름을 조정하는 객체인지,
아니면 Context를 받아 표현만 갱신하는 객체인지 합의하는 것이다.

## 장점

Model 의존성이 Presenter 여러 곳으로 퍼지는 것을 줄일 수 있다.

표현 방식이 늘어나도 `SpaceMapViewerContext`만 공유하면 된다.

프로토타입 표현과 실제 UI 표현을 같은 구조 안에서 같이 둘 수 있다.

Presenter를 켜고 끄거나 교체하기 쉽다.

View가 어떤 데이터를 표현해야 하는지 Context 형태로 명확하게 드러난다.

## 주의할 점

Context가 너무 커지면 View 전용 Model처럼 비대해질 수 있다.

Presenter마다 필요한 데이터가 지나치게 다르면 하나의 Context로 묶는 것이 오히려 어색할 수 있다.

Presenter가 다시 Model을 직접 참조하기 시작하면 이 구조의 장점이 줄어든다.

`Presenter`라는 이름이 MVP의 Presenter와 혼동될 수 있다.

그래서 이 구조를 사용할 때는 다음 기준을 두는 것이 좋다.

```text
Context에는 이 View가 표현하기 위해 필요한 읽기 전용 상태만 넣는다.
Presenter는 Context를 읽고 자기 표현만 갱신한다.
Model 변경 구독과 Context 생성 책임은 Viewer 쪽에 둔다.
입력 처리나 도메인 정책 판단은 별도 Interact 또는 Controller 계층으로 분리한다.
```
