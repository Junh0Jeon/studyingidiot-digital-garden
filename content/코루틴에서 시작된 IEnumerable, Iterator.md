# 파트
1. 코루틴에 대한 초기 공부
2. 현재 돌이켜본 후 정리

## 1. 코루틴에 대한 초기 공부
(출처 : oz 데일리 노트)
‘WASD’를 만드는 것은 구현해봤다. 3D 오브젝트에 스크립트를 부착시키고 다음과 같이 하면 됐다.

```csharp
[SerializeField]
private float moveSpeed = 1.0f;

void MoveFoward(float weight) {
	transform.position += Time.deltaTime * weight * transform.forward;
}
// i.t.s.w
void Update() {
	if(Input.GetKey(KeyCode.W)) MoveFoward(moveSpeed);
	// i.t.s.w
}
```

이러면 매 프레임마다 WASD를 인식하고, 그 인식을 토대로 포지션 변경에 기여하며 3D 오브젝트가 움직이는 것과 같은 효과를 낸다. 한 번에 두 개 이상 키를 움직여서 대각선으로 움직이는 것 또한 잘 구현이 되었다. **하지만, ‘점프’를 하고 싶다면 어떡하지?**

이 궁금증에서 시작된 코루틴 공부였다. 내가 원하는 것은 단순 점프가 아니었다. 이동하면서 점프였다.

AI와의 공부를 통해 얻어낸 것은 다음과 같다.

```csharp
IEnumerator CoJump()
{
    isJumping = true; // WARNING: 공유자원 사용 주의
    float elapsed = 0f;

    // jumpDuration, jumpHeight이 공유 자원이고 inspector에서 변경이 가능하므로 상수화
    float latestJumpDuration = jumpDuration;
    float latestJumpHeight = jumpHeight;

    // 다시 돌아가야 하는 위치 저장
    float originalY = transform.position.y;

    while (elapsed < latestJumpDuration)
    {
        elapsed += Time.deltaTime;
        float t = Mathf.Clamp01(elapsed / latestJumpDuration); // 시간은 0~1까지

        // convex 형태의 점프 -> x(1-x). 여기에 계수는 latestJumpHeight 사용.
        float yOffset = latestJumpHeight * t * (1f - t);

        // Cube의 y 위치 업데이트
        transform.position = new Vector3(
            transform.position.x,
            originalY + yOffset,
            transform.position.z
        );
        Debug.LogFormat("x,y,z : {0}, {1}, {2}", transform.position.x, transform.position.y, transform.position.z);

        yield return null; // 매 프레임마다 이정도 움직이도록 yield를 while내부에
    }
    // 점프가 끝난 후 원래 위치로 복귀 점검
    if(transform.position.y != originalY)
    {
        Debug.LogAssertion("처리 결과가 완벽하지 못함");
        transform.position = new Vector3(
            transform.position.x,
            originalY,
            transform.position.z
        );
    }

    isJumping = false; // WARNING: 공유자원
}
```

여기서 가장 중요한 것은 `yield` 의 위치다. (여기서부터 이해 하기 편하게 스레드를 전부 프로세스로 치환해서 이야기 하겠음. 본질적으로 둘은 같으니)

`StartCoroutine()`은 프로세서에게 프로세스를 하나 주는 것이다.  
기존 유니티 메인 프로세서는 매 프레임마다 Update()라는 프로세스 하나만 처리하는 상태다.  
하지만 여기서 코루틴으로 `CoJump`라는 _프로세스_를 하나 줬다. 이제 메인 프로세서는 매 프레임마다 Update()와 CoJump()라는 프로세스 두개를 처리한다.

마치 UniProcessor에서 스케줄링 하는 상황을 생각하면 된다. 그 말인 즉슨, 비동기적이지만 병렬 처리는 아니다. 하나의 프로세서 흐름에서 수행되는 것이다.  
’_비동기적이라면, 공유자원이 있을 때 레이스 컨디션을 고려해야 하지 않나_’ 싶지만, 그렇지 않다.  
_**유니티의 프로세스 흐름은 비선점 방식이기 때문에 레이스 컨디션이 발생하지 않는다.**_  
(단, 프로그래머의 논리적 버그로 인해서는 발생할 수 있음.)

가장 중요한 핵심 : 코루틴은 유니프로세서에게 직렬 수행 프로세스를 하나 던져주는 것과 같다.

---

- 유니티 프레임 루프

사실 위에서 설명한 내용은 엄밀하게 맞는 내용은 아니다. 유니티 프레임 루프라는 시스템이 있기 때문이다. 유니티에서 프레임 루프는 다음과 같다.

**Update → Physics 계산 → LateUpdate → 렌더링 → Coroutine**

한 프레임에 이 모든 작업을 마치고, 다시 Update부터 실행한다.  
LateUpdate는 ‘Update 시점에 수행하고 싶은데, Update와 우선순위를 명백히 하고 싶은’ 기능들에 사용한다. 예컨대 ‘카메라 따라가기’가 대표적인 예시이다.

그래서 위의 설명, ‘메인 프로세서는 매 프레임마다 Update()와 CoJump()라는 프로세스 두개를 처리한다.’는 엄밀하게는 틀린 설명이다. 이 두 작업 수행에는 명백한 우선순위가 존재하기 때문이다.

몇 가지 코루틴에 대해 알아낸 정보는 다음과 같다.

1. 코루틴은 호출 될 때마다 코루틴 인스턴스를 생성한다. 즉, `Update()` 에서 `StartCoroutine(Foo1())`이 제대로 제어되지 않는다면 `Foo1()`이 완료되기 이전에 다른 `Foo1()` 코루틴이 생성되어서 심각한 문제를 야기할 수 있다.  
    → 코루틴 생성은 조건처리를 까다롭게 해야 한다.
2. 코루틴 함수는 반드시 `IEnumerator` 반환 함수로 작성해야 한다.
3. 프로그래머가 제대로 제어 및 인지하지 않는다면, 여전히 공유 자원을 다루는 변수는 레이스 컨디션의 위험이 있다. preemptive해서 생기는 레이스 컨디션만 없을 뿐이다.


## 2. 현재 돌이켜본 후 정리

일단 지금은 코루틴을 잘 안 쓰고 있고, UniTask 위주로 쓰고 있긴 하다.

돌이켜보면서 몇 가지 수정하자면
1. yield 종류에 따라서 코루틴 재개 시점이 다르다
2. 새 스레드, 프로세스라는 관점으로 바라보는 것은 개념적 이해를 위해서 비유로써 사용할 수는 있지만 정확히는 `IEnumerator` 상태머신 기반이다.

우선 코루틴을 쓰기 전에 `IEnumerator`, `IEnumerable`부터 알아야한다.

### `IEnumerable` : Iterator를 생성할 수 있는 객체
```csharp
public interface IEnumerable<out T> : IEnumerable
{
    // 컬렉션을 순회할 수 있는 열거자(Enumerator)를 반환합니다.
    IEnumerator<T> GetEnumerator();
}
```

이걸 상속받으면 `IEnumearator`를 제공할 수 있는 서비스를 보장해야한다. 즉, '너 iterator 가지고 있지? 줘봐'라고 할 때 내놓을 수 있어야 한다는 뜻이다.

### `IEnumerator` : Iterator
csharp의 iterator.
```csharp
public interface IEnumerator<out T> : IDisposable, IEnumerator
{
    // 현재 가리키고 있는 요소 (읽기 전용)
    T Current { get; }
    
    // 다음 요소로 이동 (이동할 요소가 있으면 true, 없으면 false 반환)
    bool MoveNext();
    
    // 컬렉션의 첫 번째 위치 이전으로 인덱스를 초기화
    void Reset();
}
```

이걸 상속받으면 나 스스로는 iterator가 된다.

#### Iterator...?
cpp 공부할 때 여러 자료구조를 직접 만들었을때를 기억해보자.
linked list를 구현할 때, 보통 이렇게 쓰게 된다.
```cpp
#include <iostream>
// Stack, Queue 등에 쓸 구조체 Node를 만드는 경우
struct Node {
    int data;       // 데이터 저장 변수
    Node* next;     // 다음 노드를 가리키는 포인터(단방향)
};
```
즉, Node라는 컨테이너가 내부에 값을 가지고 단방향 포인터를 가진다.

이 Node는 container다.
그리고
```cpp
Node* currentPtr
```
이런 식으로 현재 노드를 가지고 있는데, 이게 iterator와 더 가까운 개념이다.

vector, list, map에서 모두 iter 방식이 동일하지 않다.
그러면 iter는 어떻게 동작하는걸까? iter 자체는 dumb하게 있고, vector/list/map이 move next하는 규칙을 iter에게 제공하고 해당 정의에 의해서 iter는 자신의 current를 move하는 방식일까?

엄밀하게 이야기하자면, STL iterator는 각각 고유한 STL에 대응하는 iterator를 가진다. vector는 vector의 iter를, list는 list의 iter를, map은 map의 iter를 가진다. 그래서 코드를 작성할 때
```cpp
using namespace std;

vector<int> v;
auto it_1 = v.begin(); // vector<int>::iterator it_1 = v.begin();
list<int> l;
auto it_2 = l.begin(); // list<int>::iterator it_2 = l.begin();
```

이렇게 `auto`를 쓰는 이유가 그 이유이다. 겉보기에는 동일한 iterator 타입이라고 헷갈릴 수 있지만 엄밀하게는 두 타입이 다른 것.

iterator는 겉보기에는 같은 문법으로 동작하도록 설계되어 있다.(`++iter`, `*iter`..) cpp에서 iterator라는 개념은 일정한 타입이라기보단 일종의 protocol, concept라고 보면 된다. 

### 다시, IEnumerable
cpp에서 `vector`가 `.begin()`을 통해 `iter`를 제공하고, `list`가 `.begin()`을 통해 `iter`를 제공하듯이, csharp에서는 `IEnumerable`을 상속받는 객체가 `GetEnumerator()`를 통해 `iter`(`IEnumerator`)를 제공한다.

따라서, `IEnumerator`는 특정 class에 귀속되는 규칙의 소유자이자 current Index(현재 상태)의 소유자이다.


```csharp
public interface IEnumerator<out T> : IDisposable
{
    // 현재 가리키고 있는 요소 (읽기 전용)
    T Current { get; }
    
    // 다음 요소로 이동 (이동할 요소가 있으면 true, 없으면 false 반환)
    bool MoveNext();
    
    // 컬렉션의 첫 번째 위치 이전으로 인덱스를 초기화
    void Reset();
}
```

좋아, 이제 `IEnumerator`를 구현해보자. 하고 착석해서 작업하려고 보면, 이상한 점이 생긴다. 바로 `MoveNext()`를 위해서는 내부 구현을 알고 있어야 한다는 점이다.

`LinkedList` 형태의 `IEnumerator`를 구현하려고 하면, `Node` 정의가 필요하다.
```csharp
class Node
{
	public int Value;
	public Node Next;
}
```
그런데, 그렇다는건 `IEnumerable`의 내부 구조가 외부에 노출된다는 것 아닌가?

여기서 `Interface`의 존재가 의미를 가진다.

```csharp
public class MyLinkedList<T> : IEnumerable<T>
{
    private Node head;

    private class Node
    {
        public T Value;
        public Node Next;
    }

    public IEnumerator<T> GetEnumerator()
    {
        return new Enumerator(head);
    }

    IEnumerator IEnumerable.GetEnumerator()
    {
        return GetEnumerator();
    }

    private class Enumerator : IEnumerator<T>
    {
        private Node head;
        private Node current;

        public Enumerator(Node head)
        {
            this.head = head;
            this.current = null;
        }

        public T Current => current.Value;

        object IEnumerator.Current => Current;

        public bool MoveNext()
        {
            if (current == null)
                current = head;
            else
                current = current.Next;

            return current != null;
        }

        public void Reset()
        {
            current = null;
        }

        public void Dispose()
        {
        }
    }
}
```

애초에 `Enumerator`가 캡슐화 되어있는 것이다.
cpp에서는 `vector<T>::iterator`를 겉으로 드러내지만, `interface`개념이 있는 csharp에서는 그럴 필요가 없는 것이다.

`Enumerator` 자체는 내부에서 선언하고 내부에서 구현한다. 외부에 드러나는 것은 `IEnumerator`로 제한한다.

## Csharp에서 yield + IEnumerator return

결론만 이야기하자면, csharp에서 `yield` + `IEnumerator`를 return하는 함수 정의는 겉보기에는 함수지만, 컴파일 이후에는 `IEnumerator`객체를 생성하는 함수처럼 동작한다.

예를 들어
```csharp
IEnumerator<T> Foo()
{
	// code block A
	yield return a;
	// code block B
	yield return b;
	// code block C
	yield return c;
}
```
이런 함수가 있다면, 컴파일한 이후 실질적으로

```csharp
private class FooEnumerator : IEnumerator
{
    private int state = 0;
    private object current;

    public object Current => current;

    public bool MoveNext()
    {
        switch (state)
        {
            case 0:
                // code block A
                current = a;
                state = 1;
                return true;

            case 1:
                // code block B
                current = b;
                state = 2;
                return true;

            case 2:
                // code block C
                current = c;
                state = 3;
                return true;

            case 3:
                return false;
        }

        return false;
    }

    public void Reset()
    {
        throw new NotSupportedException();
    }
}
```
이런 정의가 추가되며

```csharp
IEnumerator<T> Foo()
{
/*
	// code block A
	yield return a;
	// code block B
	yield return b;
	// code block C
	yield return c;
*/
	return new FooEnumerator();
}
```
원래 함수는 개념적으로 이렇게 바뀐다고 보면 된다.

### 다시, Coroutine
Coroutine은 `StartCoroutine()` 메서드를 통해서 사용한다.
`StartCoroutine`은 `IEnumerator` 상태머신을 Unity의 스케줄러에 등록하고, 스케줄러는 `MoveNext()`를 호출해서 코드블럭을 실행한 뒤 `yield return`을 통해 얻어지는 `Current`값을 보고 스케줄러에 다시 등록한다고 보면 된다.

예를 들어
```csharp
IEnumerator Co()
{
    Debug.Log("A");
    yield return null;

    Debug.Log("B");
    yield return new WaitForSeconds(1f);

    Debug.Log("C");
}
```

이런 코드가 있다면

```plain text
StartCoroutine(Co())
→ IEnumerator 객체 등록

MoveNext() 1회
→ "A" 실행
→ yield return null
→ Current = null
→ Unity: 다음 프레임 스케줄러에 등록

다음 프레임 MoveNext() 2회
→ "B" 실행
→ yield return WaitForSeconds(1f)
→ Current = WaitForSeconds
→ Unity: 1초 뒤 스케줄러에 등록

1초 뒤 MoveNext() 3회
→ "C" 실행
→ 함수 끝
→ MoveNext() false
→ Unity: 코루틴 종료
```


이제 'Unity에서 Coroutine이 GC 비용을 만든다.'라는 문장의 정체를 알 수 있다.
IEnumerator를 만드는데 이게 힙할당 객체니까


# 그렇다면 UniTask?
Unitask는 await, async를 사용하는데, 이건 뭘까

## 우선, `await`, `async`

`await`과 `async` 역시 동일하게 컴파일하면서 '상태머신'으로 치환된다.
```csharp
async Task FooAsync()
{
    Debug.Log("A");

    await Task.Delay(1000);

    Debug.Log("B");
}
```
이런 코드가 있다면,

```csharp
class FooAsyncStateMachine
{
    int state;
    TaskAwaiter awaiter;
    AsyncTaskMethodBuilder builder;

    void MoveNext()
    {
        try
        {
            if (state == 0)
                goto AfterDelay;

            Debug.Log("A");

            var task = Task.Delay(1000);
            awaiter = task.GetAwaiter();

            if (!awaiter.IsCompleted)
            {
                state = 0;

                // Task가 끝나면 MoveNext를 다시 호출해달라고 등록
                awaiter.OnCompleted(MoveNext);
                return;
            }

        AfterDelay:
            awaiter.GetResult();

            Debug.Log("B");

            builder.SetResult();
        }
        catch (Exception e)
        {
            builder.SetException(e);
        }
    }
}
```
대략 이런 코드로 변환된다고 할 수 있다.(실제로 이렇진 않지만, 원리만 본다면 이런 코드)

