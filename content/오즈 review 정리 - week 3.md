# 15일차 : OOP

## Type 1 과제 : 오늘의 내용 정리

---

### 1. OOP의 5대 원칙(SOLID)

1. SRP 단일 책임 원칙 - 객체는 오직 하나의 책임을 가져야 한다.

‘하나의 기능’이 아니다. ‘하나의 책임’이다.

```csharp
// SRP 위반 사례: Enemy 클래스
class Enemy {
    // 1. **게임 로직 / 능력치** 책임 (밸런스 디자이너 변경 요구)
    private int health;
    private int attackDamage;
    public void takeDamage(int damage) { /* 체력 계산 로직 */ }
    public void move() { /* A* 길찾기 알고리즘 */ }
    
    // 2. **렌더링 / 시각 효과** 책임 (아티스트/UI 개발자 변경 요구)
    public void draw(Renderer renderer) { 
        // 3D 모델 로딩 및 화면에 그리는 로직 
    }
    
    // 3. **데이터 저장 / 영속화** 책임 (서버 개발자 변경 요구)
    public String toSaveData() { 
        // 현재 상태를 JSON이나 DB 형식으로 변환하는 로직 
        return "state:..." + health;
    }
}
```

인터넷에서 말하는 ‘S’의 장점은 ‘하나의 책임만 다루면 그 클래스만 수정하면 됨’, ‘유지보수가 좋음’ 이런건데 와닿지 않는다.

가장 잘 와닿는 이유는 ‘컴파일’과 ‘병합’이었다.

**세개 다 같이 다룬다면, 렌더링에 수정이 일어났을 때 Enemy 전체를 재컴파일 해야하고, Enemy를 사용하는 다른 모든 애들이 렌더링과 무관하게 재컴파일 해야한다.**

**세개 다 같이 다룬다면, 렌더링 담당과 밸런스 담당이 코드를 수정하고 커밋할 때 머지 충돌이 발생한다. 이러면 수동으로 병합해야 하는데 매우매우 좋지 않다. 심지어 남의 코드를 잘못 건드릴 수 있다.(휴먼 에러)**

위의 코드를 `EnemyCore` / `EnemyRenderer` / `EnemyDataRepos` 이렇게 세개의 클래스로 나눈다면? 모든 문제가 해결된다.

각각의 클래스는 ‘**논리적으로 관련 있는 애들만 모여**’있다. 응집도가 높다 라는건 이런 뜻이다.

- 너무 클래스가 많아지는 것 아닌가? 너무 분해시키는데 얘네들 다 함께 쓰려면 어떡하지?
    
    함께 쓰려면 세가지 책임을 모두 조립한 Enemy 클래스를 만든다.  
    이러면 ‘필요에 의해 렌더러만 바꾼’ Enemy를 만들 수 있다. 즉, 유연성이 높아진다
    
- 원칙을 지키는 법
    

**논리적으로 관련 있는 애들만 모여있는지 확인한다. 분리해보고 괜찮다면 분리한다.**

1. OCP 개방 폐쇄 원칙 - 확장에는 열려 있으나 변경에는 닫혀 있어야 한다.

새로운 객체를 추가할 때 쉽게 추가할 수 있으나, 기존 코드 변경은 피할 수 있어야 한다.

확장. 즉, ‘~인 경우’가 추가될 때 쉽게 추가되어야 한다.  
변경. 기존 코드의 변경은 거의 없어야 한다.

- 원칙을 지키는 법

쉽게 말해, 추상화를 통한 업캐스팅-다운캐스팅의 다형성을 고려한다.  
if else를 쓴다면, 다형성으로 해결할 수 있는지 확인한다.

1. LSP 리스코프 치환 원칙 - 자식은 부모의 역할을 대신 할 수 있어야 한다.

**LSP를 만족한다는 뜻은 ‘is-a’관계를 넘어서 ‘can be substituted for’ 관계를 보장함을 의미한다.**  
LSP를 만족한다는 뜻은 부모의 행동 원리를 답습한다는 뜻이다.

정사각형은 직사각형이다.(is-a) 하지만 정사각형은 직사각형을 대체할 수 없다.(cannot substitute)  
→ ‘직사각형’을 사용하면서 height=1 weight=2를 기대할텐데 그게 안된다.  
독실은 방이다.(is-a) 하지만 독실이 방을 대체할 수 없다.(cannot substitute)  
→ ‘방’을 사용하면서 capacity=3을 기대할텐데 그게 안된다.

- 원칙을 지키는 법

문장 그대로’ can be substituted for’가 되는지 고려한다.  
자식이 오버라이딩 한 메서드를 주의깊게 살펴본다.

1. ISP 인터페이스 분리 원칙 - 클라이언트는 관심있는 메소드만 제공받아야 한다.

인터페이스 시점에서 SRP라고 보면 된다.

인터페이스는 선언된 클래스에 대해 광범위하게 사용되므로 변경을 지양해야 한다. OCP원칙을 지킬 것을 고려해야 한다.

- 원칙을 지키는 법

**지금 당장 클라이언트가 필요한 만큼만 인터페이스를 제공**하고, 나중에 새 인터페이스의 필요성이 느껴진다면 **작은 인터페이스를 추가 상속** 받거나, **작은 인터페이스의 집합을 새로 상속** 받는 식으로 변경한다.

1. DIP 의존 역전 원칙 - 상위 모듈이 하위 모듈에 의존해서는 안된다.

‘모듈’이라는 단어와 ‘상위/하위’ 개념이 매우 모호하다.

법률의 위계를 생각하면 된다. ‘모듈’은 ‘정책_policy’이다.  
헌법은 상위 모듈이다. ‘**무엇을 해야 하는가**’에 대한 선언이다. 근본적이고 본질적인 정책이다.  
시행령, 조례는 하위 모듈이다. 상위 모듈에 대해 ‘**어떻게 해야 하는가**’를 구현한 것이다. 자주 바뀔 수 있다.

헌법은 시행령, 조례에 의존하지 않는다. 조례가 바뀔 때마다 헌법을 바꾸면 안된다.

“이동 정책”은 “키보드”에 의존해서는 안된다.  
”이동 정책”은 “입력 인터페이스”라는 추상 서비스를 이용하고, 상황에 맞춰 “키보드”나 “컨트롤러”를 주입받는다.

- 원칙을 지키는 법

상위 모듈과 하위 모듈 둘 다 ‘추상화 인터페이스’를 사용한다.  
하위 모듈은 추상화 인터페이스를 상속받아 구현하고,  
상위 모듈은 하위 모듈을 추상 인터페이스로써 주입받아 구현한다.

### 2. 인터페이스

- `interface` 라는 키워드로 선언한다.
- 클래스 상속과 마찬가지로 `:` 를 사용한다.
- 기본적으로 `public` 속성이다.
- **can-do 관계의 구현이다. ‘기능 구현의 약속’을 의미한다.**
- 인터페이스의 본질은 “계약”이다.
- override 등의 키워드 없이 그대로 구현한다.

그래도, 실제로 작성을 할 때 막막하다면

→ 인터페이스는 “계약서” 그 자체.

→ “계약으로 인해 작업을 수행할 당사자”는 인터페이스 상속 객체  
계약을 구체적으로 어떻게 수행할지는 당사자 재량임.

→ “계약으로 서비스를 제공받을 당사자”는 인터페이스 변수를 가지는 객체.  
클라이언트임. 업캐스팅된 형태로 사용함.

→ “계약”은 클라이언트가 인터페이스 변수에 객체를 전달 받을 때 시작되며, 객체의 소멸까지 유효함.

---

## Type 2 과제 : 인터페이스 응용

---

### 3. 구현 과정

```csharp
using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class Hw_Interface : MonoBehaviour
{
    /* --------------------------------------- */
    enum Rarity
    {
        NONE = 0,
        COMMON = 1,
        RARE = 2,
        EPIC = 3,
        LEGENDARY = 4
    }
    /* --------------------------------------- */

    /* --------------------------------------- */
    readonly struct ItemData
    {
        public string Name { get; }
        public Rarity ItemRarity { get; }
        public int Id { get; }
        public bool Stackable { get; }
        public ItemData(string name, Rarity rarity, int id, bool stackable)
        {
            Name = name;
            ItemRarity = rarity;
            Id = id;
            Stackable = stackable;
        }
    }
    /* --------------------------------------- */

    /* --------------------------------------- */
    class Item
    {
        protected readonly ItemData data;

        private int count = 1;

        protected Item(ItemData data)
        {
            this.data = data;
        }

        public int Count { 
            get { return count; }
            protected set
            {
                if (data.Stackable)
                {
                    count = value;
                }
                else
                {
                    if (value == 0) count = value;
                }
            }
        }
        public void PrintItemName()
        {
            Debug.LogFormat("Item name is {0}", data.Name);
        }
    }
    interface IEquipable
    {
        public void Equip(Player player);
    }
    interface IConsumable
    {
        public void Consume(Player player);
    }
    class Armor : Item, IEquipable
    {
        static readonly ItemData ARMOR_BASE_DATA = new("CommonArmor",Rarity.RARE, 10, false);
        private readonly int defense = 3;

        public int Defense { get { return defense * (int)ARMOR_BASE_DATA.ItemRarity; } }

        public Armor() : base(ARMOR_BASE_DATA) {}

        public void Equip(Player player)
        {
            Debug.Log("아이템 장착 기능 수행");
        }
    }

    class Weapon : Item, IEquipable
    {
        static readonly ItemData WEAPON_BASE_DATA = new("IronSword", Rarity.EPIC, 2, false);
        private readonly int attack = 7;

        public int Attack { get { return attack + (int)WEAPON_BASE_DATA.ItemRarity; } }

        public Weapon() : base(WEAPON_BASE_DATA) {}

        public void Equip(Player player)
        {
            Debug.Log("아이템 장착 기능 수행");
        }
    }

    class Potion : Item, IConsumable
    {
        static readonly ItemData POTION_BASE_DATA = new("HongOk", Rarity.COMMON, 20, true);
        private readonly int healAmount = 11;

        public int HealAmount { get {  return healAmount; } }

        public Potion(int amount) : base(POTION_BASE_DATA)
        {
            Count = amount;
        }

        public void AddAmount(int amount)
        {
            Count += amount;
        }
        public void Consume(Player player)
        {
            Debug.Log("아이템 소모 기능 수행");
            Count--;
        }
    }

    class Scroll : Item, IConsumable
    {
        static readonly ItemData SCROLL_BASE_DATA = new("Hearthstone", Rarity.LEGENDARY, 30, false);
        public readonly float returnTime = 5.0f;

        public Scroll() :base(SCROLL_BASE_DATA) {}

        public void Consume(Player player)
        {
            Debug.Log("귀환합니다");
            Count--;
        }
    }

    class Player
    {
        public Item[] inventory;

        public Player()
        {
            inventory = new Item[4] {
                new Armor(),
                new Weapon(),
                new Potion(10),
                new Scroll()
            };
        }

        public void UseItem(IConsumable consumableItem)
        {
            consumableItem.Consume(this);
        }
        public void EquipItem(IEquipable equipableItem)
        {
            equipableItem.Equip(this);
        }
    }

    // Start is called before the first frame update
    void Start()
    {
        Player p = new();
        for (int i = 0; i < p.inventory.Length; i++)
        {
            p.inventory[i].PrintItemName();
        }

        p.EquipItem(p.inventory[0] as IEquipable);
        p.EquipItem(p.inventory[1] as IEquipable);

        p.UseItem(p.inventory[2] as IConsumable);
        p.UseItem(p.inventory[3] as IConsumable);
    }

    // Update is called once per frame
    void Update()
    {
        
    }
}

```

---

### 4. 어려웠던 점

최초에 간단하게 접근할 때는 다음과 같이 구조를 구상했다.

```csharp
class Item

class Armor : Item, IEquipable
class Weapon : Item, IEquipable

class Potion : Item, IConsumable
class Scroll : Item, IConsumable

interface IEquipable
+ Equip(Player)

interface IConsumable
+ Consume(Player)

class Player
+ UseItem(IConsumable)
+ EquipItem(IEquipable)
```

그런데, 막상 ‘실제 기능 구현’을 수행하려다 보니 어려움에 봉착했다.

예컨대, Potion이 ‘플레이어의 체력을 10 회복시키는’ 기능을 수행한다고 하자.  
그러면 어디선가 ‘player의 체력 10 증가’시키는 작업을 수행해야한다.  
대체 어디서 수행해야 하는가?

만약 player에서 수행한다면, player는 IConsumable 타입의 객체 item의 정보를 파헤치면서 다뤄야 한다.  
그러면 item이 체력회복인지, 마나회복인지, 힘증가인지, 음식인지…. 모른다.  
각각의 케이스를 if else로 구분한다? SOLID 위반이다.

그래서 UseItem에서 IConsumable item에 대해 item.ApplyEffect 와 같은 식으로 구현을 한다고 생각해보자.  
그러면 item 스스로가 Player에 대해 정보가 필요하다.  
만약 Consume을 통해 player 객체를 받는 식으로 수행한다면, Item이 굉장히 Player에 종속적이 된다.  
Item은 Player의 모든 구조를 알고 있어야 하는 객체인 것이다.

**이게… 적절한 구조가 맞나?**

또 이런 고민도 생겼다.  
’Shift + Click’을 하면 우리가 ‘할 것이다’라고 기대하는 작업을 일괄적으로 수행하는 유저친화 시스템이 있다.  
예컨대 Equipable은 장착하고, Consumable은 사용한다.  
그러면 이거는 어떻게 처리해야 하는가? if-else를 사용해야 하지 않나? 그러면 OCP를 위반하는데

또 이런 고민도 생겼다.  
’아이템 등급에 따라 장착을 못 할 수도 있는데, 그러면 플레이어가 아이템 등급을 확인해야 하나? 아이템이 플레이어 등급을 확인해야 하나?’

---

### 5. 공부 할 만한 내용

라우팅 책임

명령 패턴

메타데이터 및 맵핑

validator와 명세 패턴


---

## Review 정리

- OOP 5대 원칙의 경우 신경쓰면서 작업하면 좋긴 하지만, 이거에 매몰되는 순간 오히려 코딩의 목적성을 잃고 애자일하게 작업하지 못하게 되므로 주의

### Potion과 Player의 관계

지금 내가 볼 때는, 해당 고민은
`IConsumable`이랑 `IConsumeTarget` 이 두가지 인터페이스로 처리 가능해보인다.
`Potion` 입장에서는 `IConsumeTarget`을 참조해서 예컨대 `Heal(int)`라거나 `AddButt(Buff)`라거나 뭐 이런식으로 인터페이스를 사용하는 것.

대신 `IConsumable`은 `Consume(IConsumable)` 이런 형태로 자신의 참조를 전달해야 할 것임

### Shift + Click의 다양한 행동

이것도 앞선 것과 비슷한 구조로 가는게 적절해보인다.
`IQuickClickable` 인터페이스를 하나 만들고
클릭했을 때 `QuickClick` 함수를 호출하도록 하면 된다.
그리고 `Potion`객체는 `IQuickClick`을 호출했을 때 `Consume`하게 만들고, `Equipment` 객체는 `IQuickClick`을 호출했을 때 `Equip`하게 만들면 된다.

### 아이템 장착 조건의 확인 위치

`Player`쪽에서 검사하는게 맞는 것 같다.
`Item`입장에서는 그냥 '나 장착해줘~'하고
`Player` 입장에서 장착하려고 할 때 장착 조건을 검사하는 것
대신, 초반엔 그냥 `Player`쪽에서 로직을 직접 다루더라도
장기적으로 본다면 `Player`쪽에서 직접 장착 조건을 다루는게 아니라, `Item`과 `Player` 상황 모두 파악해서 장착 조건을 파악할 수 있는 개인 모듈을 아예 두는게 좋다고 느껴진다. OOP적으로 볼 때도 그게 맞으니까.

### 공부해야겠다고 적은 내용...

#### 라우팅 책임

뭐지? ai한테 물어보니까 `요청을 받은 객체가 직접 모든 경우를 판단할 것인가, 아니면 적절한 대상에게 위임할 것인가?` 에 대한 이야기 같다고 한다.

![[Pasted image 20260713160451.png]]

이 문장을 디커플링해본다면, 처리해야 할 정책적인 부분은 다음과 같이 분리할 수 있을 것 처럼 보인다.


'요청을 받는다', '경우를 판단한다', '위임한다'
애초에 '요청을 받는다'라는게 이제 API라고 볼 수 있는데
요청이 일관된 API함수 하나에서 오는 경우가 있을 수 있고, 각 요청에 해당하는 함수에서 일어날 수 있다.

case 1: 요청이 일관된 API함수 하나에서 오는 경우
이럴때는 이 '요청'이라는게 결국 parameter로 추상화된 객체가 들어오거나, `context`라는 DTO의 형태로 온다고 생각할 수 있다.(그런 구현이 아니라면 이상한 구현이라고밖에 생각이 들지 않는다.)

추상화된 객체가 들어올 경우 `switch`를 통해서 '이 객체의 요청이라면 이렇게 처리하고, 저 객체의 요청이라면 저렇게 처리하고...'의 방식으로 처리하는게 최선이라고 생각된다.
DTO가 올 때 역시 `switch`를 통해서 처리하는게 최선이라고 생각된다.

case 2: 요청이 각 요청에 해당하는 함수에서 일어나는 경우
이 경우 애초에 `switch`가 API함수 그 자체로 나눠져 있는 경우라고 볼 수 있다. 따라서 그 함수 자체에서 정책 처리를 하면 된다고 생각이 든다.

#### 명령 패턴(Command Pattern)

행위, 기능 자체를 캡슐화하는 것.

```csharp
interface ICommand
{
	void Execute()
}
interface IConsumable
{
	void Consume()
}
```
앞서 이야기한 구현에 그냥 이름 붙인 것이다.

호출하는 쪽에서 추상화된 `ICommand`(`IConsumable`)을 사용하고,
실제 동작 자체는 온전히 그 객체에게 의존하는 것.

#### 메타데이터 및 맵핑

객체 데이터 자체에 어떤 동작을 해야할지 전략이라던가, 델리게이트라던가 등을 애초에 넣어둘 수 있다. vtable, vptr마냥 쓰는 것이다.

heal potion 자체에 map id 1을 넣어두고, map id 1에는 델리게이트 A가 이미 있어서 해당 델리게이트를 실행하면 회복이 된다던가...

#### validator와 명세 패턴

validator의 경우 SVAC패턴을 통해서 많이 사용해본 경험이 있으니 패스

명세 패턴은, '조건' 자체를 객체화하는 것.

```csharp
public interface ISpecification<T>
{
    bool IsSatisfiedBy(T target);
}
```
추상화된 '조건' 객체.

```csharp
public class MinLevelSpec : ISpecification<Player>
{
    private readonly int minLevel;

    public MinLevelSpec(int minLevel)
    {
        this.minLevel = minLevel;
    }

    public bool IsSatisfiedBy(Player player)
    {
        return player.Level >= minLevel;
    }
}
```
구체화된 '레벨 N 이상이어야 한다'라는 조건 객체

```csharp
public class MinGradeSpec : ISpecification<Player>
{
    private readonly PlayerGrade minGrade;

    public MinGradeSpec(PlayerGrade minGrade)
    {
        this.minGrade = minGrade;
    }

    public bool IsSatisfiedBy(Player player)
    {
        return player.Grade >= minGrade;
    }
}
```
구체화된 '등급이 M 이상이어야 한다'라는 조건 객체

```csharp
public class AndSpec<T> : ISpecification<T>
{
    private readonly ISpecification<T> left;
    private readonly ISpecification<T> right;

    public AndSpec(ISpecification<T> left, ISpecification<T> right)
    {
        this.left = left;
        this.right = right;
    }

    public bool IsSatisfiedBy(T target)
    {
        return left.IsSatisfiedBy(target)
            && right.IsSatisfiedBy(target);
    }
}
```
이 두가지 조건이 합쳐진 조건 객체

```csharp
if (requirement.IsSatisfiedBy(player)) // requirement는 AndSpec 객체
{
    // 장착 가능
}
```
이런 식으로 사용할 수 있다.

명세 패턴의 경우
- 조건의 재사용성이 필요할 때
(AND, OR, NOT 조합의 사용이 잦을 때)
(서로 다른 맥락에서 서로 같은 규칙을 공유할 때)
- 조건을 직렬화/데이터화할 필요가 있을 때
등의 상황에서 유용하지만 그 외의 경우에는 복잡도만 늘어나기 때문에 딱히 좋아보이진 않는다.

# 16일차 : FSM

![[Pasted image 20260713165340.png]]

# 17일차 : x

# 18일차 : 박싱, 언박싱, 제네릭

밸류 타입을 레퍼런스 타입으로 캐스팅하는 것.
`object`를 함수의 parameter로 쓰는게 가장 일반적인 박싱의 용례.

## 제네릭

C++에서는 (내 기억이 맞다면) 컴파일 시점에 컴파일러가 템플릿을 전부 보고 해당 템플릿을 사용하는 타입에 맞춰 코드를 자동으로 생성 후 컴파일 했다. 즉, 컴파일 시점에 이미 코드가 다 되어있다.

C#은 다르다. (모노 백엔드 기준) JIT 컴파일러를 쓰는데, 얘는 동적 컴파일이라고 생각하면 된다. 따라서 제네릭도 해당 제네릭 타입을 사용하는 타이밍에 컴파일 된다. 마구 쓰면 오버헤드 주의.

(갑자기 든 생각)  
인터페이스에서 정의하는 '기능', 즉 함수가 있는데  
이 함수의 패러미터를 쓰는 법은 '이용하는 측에서 내가 주고싶은 정보'를 담으면 되겠구나, 싶음. 그러면

서비스 제공자(인터페이스 상속받은 클래스)는  
서비스 이용자(인터페이스의 함수를 사용하는 클래스. 인터페이스를 상속받은 객체의 메서드를 사용함.)에게서 서비스 이용자의 정보를 받아서 작업하는, 이른바 하청의 이미지를 그리면 되는 듯.

근데, '이용하는 측'이 특정되면 좋겠지만... 그렇지 않잖아?  
특정된다면 ‘이용하는 측’에서 안심하고 해당 클래스의 변수를 사용하고 변경하고 그러겠지만…  
그래서 '이용하는 측'도 인터페이스로 분류해주는구나... 싶음

# 19일차 : 제약조건, 자료구조

## 1. 오늘의 학습

- 제약조건 `where`
- 심플 팩토리 패턴
- `foreach`
- 자료구조 : Stack, Queue

## 2. 강의 내용 정리

---

### 제약조건 `where`

- 사용 방법

```csharp
class MyClass<T> where T : struct{}
```

제약조건은 다양하게 있는데,  
→ `struct` : 값 타입 한정  
→ `class` : 참조 타입 한정  
→ `new()` : 기본 생성자 필수

참조 타입으로 한정하면, `null` 을 사용할 수 있다는 장점이 있다.

`struct` + `interface` 제약조건은 `T` 가 박싱이 일어나지 않도록 최적화를 해준다.

---

### 심플 팩토리 패턴

```csharp
class MyClassSpawner
{
	public MyClass Spawn(MyType type)
	{
		MyClass ans = null;
		if(type == MyType.TypeA)
		{
			ans = new ClassA(); // MyClass를 상속받은 클래스.
		}
		else if(type == MyType.TypeB)
		{
			ans = new ClassB(); // MyClass를 상속받은 클래스.
		}
		// ...
		return ans;
}
```

---

### `foreach` : `foreach(var varName in lists)`

C++의 그것이다.

C++과 다른 점은, `var` 가 읽기전용이다. (Java와 마찬가지로, ‘주솟값 재정의’가 안되는거지 레퍼런스 타입의 필드 수정은 가능)

---

### 자료구조 : Stack, Queue

뭐.. 이미 알고 있는 그건데 C#의 특징이 있다.

바로 **이터레이터가 있어**서 `foreach` 에 사용할 수 있다는 것. C++과 차이점이다.

자료구조 콜렉션은 **제네릭 버전**과 **논-제네릭 버전**이 있는데, 논-제네릭은 `object` 를 쓴다.

## Review

이때 적었던 이터레이터라는 것의 정체가 바로 `IEnumerator`이고, 이젠 이해 완료.

# 20일차 : x

# 21일차 : 유니티 에디터

## 3. 오늘의 학습 내용

- 인스펙터에 있는 애들은 다 ‘컴포넌트’ 이다.

스크립트 상에서 제어가 가능한 애들이다.

`SerializedField` 를 통해 직렬화가 가능하고, 직렬화 시키면 에디터에서 컨트롤이 가능하다.

- ‘씬 화면’ 단축키

QWERTY를 이용해 오브젝트 제어가 가능하다. 익숙해지는게 가장 우선이다.  
Q 화면이동, W 물체이동, E 로테이션, R 스케일, Y는 총집합

우클릭 상태에서 WASD QE를 통해 화면제어가 가능하다.  
마우스 휠을 통해 이동속도 제어가 가능하고,  
컨트롤 키를 통해 단위 유닛 조절이 가능하고,  
V키를 통해 스냅할 수 있다.

Ctrl + Shift + F 를 통해 ‘현재 씬이 가리키는 화면각’으로 오브젝트가 이동한다.

- transform의 비밀

Transform 컴포넌트는 Empty인 오브젝트조차 가지고 있기 때문에, 별다른 제약 없이 접근할 수 있다.

`transform.position` 을 통해 값을 직접 변경할 수 없다. 대신 `transform.Translate()` 라는 함수를 통해 간단하게 변경 가능하다.

변경할 때, `global` 과 `local` 을 구분해야 한다. `Translate()` 메소드의 오버로드 된 함수를 보면 `Space` 라는 enum을 통해 해당 구분을 명확하게 할 수 있다.

- 유니티의 초기화 - 생성자 비추

유니티에서는 생성자 사용을 권장하지 않는다. 생성자를 쓰면 유니티 플로우가 일관성이 깨진다.

유니티에서는 Start, Awake 이런데에서 초기화를 할 것을 권장하고 있다.

- Time.deltaTime

‘프레임마다’ 일어나는 일에서는 항상 보정을 해주는 것으로 기억하면 된다.

- 머터리얼 : 주소참조

얘 하나 변하면 전부 다 같이 변한다.

- 오브젝트 하이어아키 : 부모만 바꾸고 싶다면?

분리한 다음에 합치거나, 애초에 동일 계층에 두는 것이다.

---

## 4. 추가 공부할 점

Quaternion이 뭐지?

왜 유니티 플로우의 일관성이 깨지는걸까? 뭐때문에?

transform.position이 ‘객체주소’가 아니라 ‘값’을 리턴하는데, 대입연산자는 또 되네. 왜지? 원리를 알아보고 싶은데

---

## 5. 어려웠던 점

내 욕심에 비해 내 작업속도가 너무 늦다.

가속도도 구현하고, 드리프트도 구현하고, 차량 바퀴도 같이 움직이는걸 구현하고 싶었는데

가속도에서 일단 너무 오래걸렸다. 그래프는 그렸고 속도 공식도 맞춰놨는데 그걸 이제 코드로 옮기는게 어렵고, 온전히 해내지 못했다. 그래도 소득은 있었다. “상태머신”을 적극적으로 이용하는 것이다. W를 누르면 ‘가속 모드’로 전환하고, 거기서 specific frame이 지나면 ‘정속 모드’로 전환하고…

상태머신을 잘 도입하고 잘 짜는 것에 익숙해질 필요가 있고 중요하다고 생각한다.

## Review

유니티 객체의 생성은 유니티 라이프사이클에 의해 제어되며 각종 이벤트 및 관리 대상으로 등록되므로, 유니티 객체 생성은 new를 통해서 이루어질경우 해당 객체는 우리가 흔히 기대하는 그런 동작이 제대로 이루어지지 않는다고 지금은 이해하고 있음.

transform.position이 ‘객체주소’가 아니라 ‘값’을 리턴하는데, 대입연산자는 또 되네. 왜지? 원리를 알아보고 싶은데
-> Unity에서 Transform의 position이라는 `Vector3`를 setter를 열어놓았기 때문에 가능한 부분.
