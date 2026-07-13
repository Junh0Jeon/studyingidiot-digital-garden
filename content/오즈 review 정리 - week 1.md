#### 1일차 : print(debug.log)
![[Pasted image 20260708100806.png]]
수업중에 배운게 아니면 안 쓰려는 경향이 보임

#### 2일차 : 변수, 할당(타입), 스코프, 조건문, 반복문
![[Pasted image 20260708100908.png]]
유니티의 guid를 제대로 알기 전에 실험해본 기록.

![[Pasted image 20260708101008.png]]

C++에서는 constructor 하나로 끝나던 초기화가 유니티에서는 여러 phase로 이루어진다.

다만,
![[Pasted image 20260708102059.png]]
C++도 실질적으로 작업하다보면 상호참조 등의 처리를 하기 위해 phase가 분리되긴 한다

+) 추가공부
Awake, Start, OnEnable
Awake는 ***Mono의 활성화와 관계 없이***, GameObject의 활성화에 영향을 받는다. 1회 실행된다
Start는 GameObject가 활성화되어있을 때, Mono의 활성화에 영향을 받는다. 1회 실행된다.
OnEnable은 GameObject가 활성화되어있을 때, Mono의 활성화에 영향을 받는다. 여러번 실행된다.

#### 3일차 : 전위/후위 연산,  배열, 할당
![[Pasted image 20260708103409.png]]

배열은 깊은복사가 일어나지 않는다. 잘못 정리했음. 배열은 얕은 복사임.
문자열의 경우 참조타입인데 리터럴 그 자체가 새 할당, 새 주소이므로 GC spike를 주의해야함.

![[Pasted image 20260708103937.png]]
다시 알아보니
1. stackalloc이라는게 있음.
![[Pasted image 20260708104003.png]]
2. struct + unsafe로 fixed를 쓸 수 있음.
![[Pasted image 20260708104029.png]]
3. NativeArray라는 유니티가 제공하는 기능이 있음
![[Pasted image 20260708104046.png]]

#### 4일차 : parameter, return, 함수, ref/in/out
![[Pasted image 20260708104216.png]]
![[Pasted image 20260708105058.png]]

까먹고 있던 것. ~~함수 시그니쳐의 대상이 아니다.~~
함수 시그니처의 대상이긴 하다. `void Foo(int a)`랑 `void Foo(ref int a)`는 분명히 다른 시그니처로 구분된다. 하지만 `void Foo(ref int a)`랑 `void Foo(out int a)`는 다른 시그니처로 구분되지 않는다. 따라서, '오버로딩을 이 키워드만으로 구분할 수 없다'라는 표현이 더 정확하다.

tmi) C++에서 mutable을 쓰면 const여도 수정 가능하다

![[Pasted image 20260708110149.png]]
record는 불변성을 보장하지 않는다. record는 그냥 편의문법이고, 여전히 내부 멤버가 변경 가능하다.

다만, positional record는 생성 이후 재할당을 막는 스타일이다. 예를 들어
```csharp
public record PlayerData
{
	public int Hp { get; set; }
}
var p = new PlayerDAta { Hp = 100 };
p.Hp = 50;
```
이건 가능하기 때문에 내부 멤버가 변경 가능하지만
```csharp
public record PlayerData(int Hp);
var p = new PlayerData(100);
p.Hp = 100; // 불가능
```
이건 불가능하다.
`불변하게 만들기 쉬운 데이터 타입 문법`이라고 봐야함
이건 `record`가 프로퍼티를 생성할 때 명시하지 않으면 `init`키워드를 쓰는 프로퍼티를 사용하기 때문에 가능한 부분이다.

##### `init`키워드 프로퍼티
1번만 사용할 수 있는 setter라고 보면 된다. **외부에서 보기 좋은 named initialization을 허용**한다는 장점이 있다.

![[Pasted image 20260708110743.png]]
그나마 비슷한건 csharp에서 interface, 그중에서도 `IReadOnly~`로 붙는 인터페이스가 그나마 비슷하게 흉내낼 수 있어보인다.

#### 5일차 : MiningGold(ref 실전 연습), Swap 구현
![[Pasted image 20260708111557.png]]
`new Color`, `new Vector3` 같은걸 생각해보면 당연한 내용이다.

![[Pasted image 20260708112006.png]]
`local variable`에 대해서 `ref`는 alias의 개념에 가깝다.

![[Pasted image 20260708112208.png]]
![[Pasted image 20260708112214.png]]
![[Pasted image 20260708112309.png]]

기본적으로 dangling reference를 막기 위해 local variable은 ref return이 불가능하지만, local variable이 아닌 경우에 ref return이 가능하다. (단, return type이 ref여야함)

![[Pasted image 20260708112411.png]]

#### 6일차 : 배열, 매개변수, 함수 오버로딩 반복연습
![[Pasted image 20260708112858.png]]

#### 7일차 : none
