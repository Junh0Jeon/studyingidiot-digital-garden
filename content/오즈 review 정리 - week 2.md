#### 8일차 : enum, input key event
![[Pasted image 20260708115102.png]]
```csharp
public enum MyEnum : short {}
```
이런식으로 타입(크기) 자체를 정할 수 있다.

![[Pasted image 20260708115450.png]]
csharp에서 `enum`의 메타데이터는 뭐가 있을까?
타입이름, 선언된 이름들, 각 이름의 값, 접근 제한자 등등을 확인할 수 있음.

![[Pasted image 20260708122521.png]]
##### serialize
![[Pasted image 20260708122713.png]]
유니티에서 serializeation은 csharp객체를 파일에 저장해두고 그 값을 복원하는 시스템

씬에 붙은 컴포넌트라면 씬 파일의 yaml에, 프리팹이라면 프리팹의 yaml에, SO라면 SO의 yaml에 해당 값이 저장됨

`System.Serializable`은 `.NET`쪽 attribute임.
![[Pasted image 20260708123829.png]]
![[Pasted image 20260708123835.png]]

serializable은 명시적인 attribute에 불과하다. 그 자체로 어떤 기능을 제공하지 않는다. 
컴파일에 미치는 영향은 고작 메타데이터에 attribute 하나가 붙는 것 말고 없다.

유니티에서 직렬화를 지원하는 과정을 개략적으로 설명하자면 다음과 같다.

-> `MonoBehaviour`, `ScriptableObject`, `Scene Object` 등등을 저장할 때 필드를 검사
-> serialize 대상이라면, 텍스트(인라인)으로 저장
-> `System.Serializable` attribute라면 인라인으로 저장(메타데이터로써 역할)
-> Unity Object라면 `fileID`를 가리킴. 외부 에셋이라면 `guid`로 가리킴(참조)
-> 씬 로드, Instantiate 등의 Object 생성시에 데이터를 읽어서 주입

##### 코루틴
따로 문서화

##### 추가 점검할 내용
![[Pasted image 20260709120739.png]]
`SerializeField`는 명령어라기보단 `attribute`
###### attribute?
csharp에서 클래스, 메서드, 필드, 프로퍼티 등에 붙이는 '메타데이터 문법'
`attribute`는 메타데이터를 추가하는 것이며, 컴파일러/런타임/프레임워크/툴이 해당 메타데이터를 읽어서 행동을 바꿀 수 있음

일반적으로 컴파일 자체에 유의미한 영향을 주진 않는다. `[Obsolete]`같은 attr는 csharp 컴파일러가 읽고 유의미한 영향을 준다. 따라서 '컴파일 자체에 유의미한 영향을 전혀 주지 않는다.' 라고 이야기하면 틀린 이야기지만, '일반적으로 런타임이나 프레임워크가 읽어서 처리한다'라고 하면 보통 옳은 표현이다.

###### Reflection
[reflection 정리 문서] 참고

###### 유니티 프레임 루프?
유니티 공식 문서를 참고. 해소된 사항.

###### 코루틴 함수를 `IEnumerator`?
[코루틴 정리 문서](obsidian://open?vault=content&file=%EC%BD%94%EB%A3%A8%ED%8B%B4%EC%97%90%EC%84%9C%20%EC%8B%9C%EC%9E%91%EB%90%9C%20IEnumerable%2C%20Iterator) 참고

#### 9일차 : 구조체 사용
```
### 1. 구현 목표

- 구조체를 만들어보기

1. 구조체 하나 만들기
2. 구조체의 멤버 변수를 만들어 넣기
3. 구조체의 멤버 함수 만들고 호출하기
4. 외부에서 구조체를 매개변수로 접근하는 함수 만들기
5. 적합하게 getter, setter 사용해보기
```

![[Pasted image 20260709122911.png]]
##### `this`, 그리고 확장메서드
```csharp
public static class 클래스명
{
    public static 반환타입 메서드명(this 확장할타입 대상, 추가매개변수...)
    {
    }
}
```

`this`는 확장 메서드를 만들 때 쓰인다.
`interface`에 붙이면 꽤 강력하게 사용할 수 있다. 수많은 객체에 동일한 메서드를 제공하는 것이기 때문에...

![[Pasted image 20260709123745.png]]
cpp의 패딩과 csharp의 패딩 관련해서 적은 문장은 틀린 문장.

##### 복사생성자, 이동생성자(cpp, csharp)
```cpp
class Player
{
public:
    int hp;

    Player(int hp) : hp(hp) {}

    Player(const Player& other)
    {
        hp = other.hp;
    }
};

Player a(100);
Player b = a; // 복사 생성자 호출
```

cpp에서 복사생성자는 `const &`로 정의한다.(lvalue, rvalue 모두 동일하게 받아들이며 선언된 객체 그 자체를 받아들이는 것)

```cpp
class Inventory
{
public:
    int* gold;

    Inventory(int value)
    {
        gold = new int(value);
    }

    Inventory(Inventory&& other)
    {
        gold = other.gold;
        other.gold = nullptr;
    }

    ~Inventory()
    {
        delete gold;
    }
};
```
이동생성자는 `&&`로 정의한다. rvalue만 받는다는 것. rvalue 자체가 '곧 사라질 수 있는 객체'를 의미하기 때문에, 명시적으로 rvalue만 받는다.

Rule of Three / Five / Zero 순서로 cpp 생성자 규칙 권장사항이 옮겨졌다 정도만 뭐 교양으로 기억해두면 됨.
> Three : 소멸자 / 복사 생성자 / 복사 대입 연산자는 셋이 구현의무를 묶어서 가짐
> Five : 소멸자 / 복사 생성자 / 복사 대입 연산자 / 이동 생성자 / 이동 대입 연산자 다섯이 묶임
> Zero : 직접 new/delete 하지 말고, STL 쓰자

csharp에서는 cpp처럼 주소를 직접 다루지 않으며, value type과 reference type으로 엄격하게 구분하며 class는 reference로 다뤄지기 때문에 딱히 복사 생성, 이동 생성 할 필요가 없어서 해당 문법이 공식적으로 존재하지 않는다.

#### 10일차 : 구조체
![[Pasted image 20260709141438.png]]

인덱서 까먹고 있었다. 잘 안쓰다보니까...


![[Pasted image 20260709141456.png]]


#### 11일차 : 구조체
![[Pasted image 20260709180410.png]]

```
### 3. 구현 과정의 어려움과 깨달음

처음엔 Item, Player, Battle 시스템 순서로 구조를 떠올리면서 작성했음  
그러다보니까 ‘데이터의 관리’라던지, ‘게임 흐름에서 실행의 주체’라던지 여러 부분에 대한 고민이 깊어짐.  
잠시 접어두고 다른 일 하다가 상향식이 아닌 하향식으로 하니까 현재 범위 내에서 진행할 수 있는 방법을 떠올렸는데, 너무 늦은게 안타까움.

Update에서 Battle의 상태를 체크하면서 Battle에 입력을 보내주고, Battle(gameManager)이 내부에서 Player의 처리를 받은 입력에 기반하여 수행하는 흐름으로 작성하면 된다고 생각함

초기에는 Player→Battle→Update순서로 생각을 하다보니까  
‘플레이어에 Play를 넣어야겠어’ 하면서 삽질하고,  
‘아니다 Battle에서 해야겠는데?’ 하면서 삽질하고, 마지막에야  
‘Battle에서 하면 배틀 코루틴을 만들어야 할 것 같은데… 왜냐하면 Update에서 시작 입력만 받고 배틀에서 실제 흐름을 처리하면 gameManager에서만 이루어지는 코드 흐름이 따로 있어야하니까…’ 하면서 한참 삽질하다가 겨우 떠올렸음.

구조를 짜는게 어려울때는 하향식으로 생각하는게 좋은 것 같다는 깨달음을 얻었음.  
돌이켜 생각해보면 내가 다른 게임들의 플레이 구조에 대해서 고민하고 상상할 때 하향식으로 생각했었음. 이미 겉으로 드러난 게임 플레이를 기반으로 ‘이 처리는 이런 방식이겠구나’, ‘순서가 이런 식으로 이루어지네? 아 얘는 이펙트-계산-이펙트 순서구나’… 뭐 이런 식으로.  
이미 드러난 흐름에서 생각이 출발하는게 익숙하고 이해하기 편한 것 처럼, 이미 완성된 게임의 플레이를 생각하고 그걸 분석하는 식으로 상상하면 더 나을 것 같다는 생각이 들었음.
```

#### 12일차 : 선택 정렬
![[Pasted image 20260709180621.png]]

cpp에서 `std::sort`가 기본적으로 `operator<`를 사용하기 때문에 해당 연산자만 오버로딩하면 정렬을 할 수 있지만, csharp은 그렇지 않다.

csharp의 `List<T>.Sort()`는 기본적으로 `operator<`를 보는것이 아니라, `IComparable<T>`의 `CompareTo`를 본다. 따라서 정렬이 목적이라면 `IComparable<T>`를 구현해야 한다. (또는 `IComparer<T>`)

`operator <`, `operator >`같은건 비교식을 이쁘게 쓰기 위한 추가 기능, 추가 작업에 가깝다. 

csharp에서 연산자를 오버로딩하려면
```csharp
public static 반환타입 operator 연산자(매개변수...)
```

![[Pasted image 20260709181101.png]]
`StringBuilder`

#### 13일차 : UML 클래스 다이어그램, 컴파일
- UML 클래스 다이어그램, 관계

일반화 관계는 —▷ 를 사용한다. 상속 관계를 표현하는데 사용한다.

실체화 관계는 - -▷ 를 사용한다. 인터페이스 구현 관계를 표현하는데 사용한다.

연관 관계는 —> 를 사용한다. ‘참조’하고 있을 때 사용한다. 굉장히 포괄적이다.

의존 관계는 - -> 를 사용한다. ‘참조’하고 있으면서, 해당 참조 스코프에서만 참조가 존재할 때 사용한다.

구성 관계는 ◆—> 를 사용한다. 멤버 변수로 강하게 참조하며, 생애 주기를 함께 한다. 일반적으로 생성자/소멸자를 통해 구현된다.

집합 관계는 ◇—> 를 사용한다. 멤버 변수로 약하게 참조하며, 생애 주기가 독립적이다. 일반적으로 parameter injection을 통해 구현된다.

##### 컴파일
![[Pasted image 20260709181543.png]]
csharp은 csharp 컴파일러가 `.exe`, `.dll`을 만든다. 이 확장자는 `.Net Assembly`이다. 닷넷 환경에서 읽을 수 있고 동작할 수 있는 어셈블리 파일인 것이다. 이 안에 `IL 코드`(`Intermediate Language`)와 `metadata`, `manifest` 등등이 들어있다.

닷넷 어셈블리 파일은 실행할 때 CLR(`.Net Runtime`) 위에서 실행된다. 정확히는 CLR이 어셈블리를 로드하고 IL을 JIT 컴파일해서 현재 환경의 네이티브 코드로 바꾼 뒤 실행한다.
즉, csharp 디버깅 중 디스어셈블리에서 보이는 어셈블리 코드는 CLR의 JIT 컴파일러가 IL로부터 생성한 네이티브 코드이다.

![[Pasted image 20260709182612.png]]
인라인

inline이란 값이 별도의 객체 참조를 통해 존재하지 않고,
그 값을 포함하는 대상의 메모리 영역 안에 직접 배치되어 있다는 뜻이다.

C#에서 struct 타입 필드가 class의 인스턴스 필드라면,
그 struct 값은 해당 class 객체의 인스턴스 데이터 안에 직접 포함된다.
따라서 class 객체가 힙에 있으면 그 안의 struct 필드도 힙 영역 안에 함께 존재한다.

다만 이것은 "값 타입이라서 힙에 할당되면 inline"이라는 뜻은 아니다.
boxing처럼 값 타입이 별도의 객체로 만들어지는 경우도 있다.

#### 14일차 : 다형성
![[Pasted image 20260709183237.png]]

![[Pasted image 20260709183453.png]]
SO를 배우기 전에 했던 고민


![[Pasted image 20260709183501.png]]
"클래스 내부에서는 개발자의 의도대로 동작할 것이라는 신뢰도 하나로 믿고 간다"


![[Pasted image 20260709183603.png]]


![[Pasted image 20260709183839.png]]

Vtable, Vptr은 cpp에서 주로 쓰는 개념. 다형성에 사용.

`Virtual Table`은 클래스마다 하나씩 가지는 map이라고 생각하면 된다. 자신의 virtual 함수가 `Child::Foo`를 호출해야 하는지, `Parent::Foo`를 호출해야 하는지 명시해놓은 테이블이다.

`Virtual Table Pointer(Vptr)`은 객체 안에 숨어있는 포인터로, 자신의 `virtual table`을 가리키는 포인터이다. 따라서 호출 흐름은 대략
```
Parent* a = new Child();
a->Foo();

1. a가 가리키는 객체로 간다
2. 객체 안의 vptr을 읽는다
3. vptr이 가리키는 vTable로 간다
4. Foo를 찾는다
5. Child::Foo를 호출한다
```
이렇게 된다.

virtual이 없으면 자식함수 호출 없이 바로 부모함수 호출을 한다. 왜냐하면 `Parent*` 타입이니까.