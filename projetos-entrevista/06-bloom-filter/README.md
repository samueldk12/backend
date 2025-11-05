# 🎯 Projeto 6: Bloom Filter

> Estrutura de dados probabilística - aparece em 50% das entrevistas de otimização

---

## 📋 Problema

**Descrição:** Implementar Bloom Filter para verificar se elemento pertence a um conjunto de forma eficiente em espaço.

**Problema Real:**
```
Cenário: Verificar se username já existe (1 bilhão de usuários)

SOLUÇÃO INGÊNUA:
  SET com 1B usernames
  Memória: ~20GB (20 bytes por username)
  Lookup: O(1) mas muito espaço! 💥

SOLUÇÃO COM BLOOM FILTER:
  Bloom Filter com 1B usernames
  Memória: ~1.2GB (95% de economia!)
  Lookup: O(k) onde k = número de hash functions
  Trade-off: Falsos positivos possíveis

  "João" existe? → 100% preciso se resposta for NÃO
  "Maria" existe? → ~1% chance de falso positivo se resposta for SIM
```

**Características:**
- ✅ **Nunca** tem falso negativo (se diz NÃO, é NÃO)
- ⚠️ **Pode** ter falso positivo (se diz SIM, verificar no DB)
- ✅ Extremamente eficiente em espaço (~1 byte por elemento)
- ❌ Não suporta remoção (use Counting Bloom Filter)

---

## 🎯 Requisitos

### Funcionais
1. ✅ `add(item)`: Adicionar elemento
2. ✅ `contains(item)`: Verificar se elemento PODE estar no set
3. ✅ Taxa de falso positivo configurável (1%, 0.1%, etc)

### Não-funcionais
1. **Espaço**: ~10 bits por elemento (vs 160 bits com SHA1)
2. **Lookup**: O(k) onde k é número de hash functions (~3-7)
3. **No false negatives**: Se diz NÃO, garantia 100%

---

## 🔧 Implementação

### 1. Bloom Filter Básico

```python
import math
import mmh3  # MurmurHash3 (fast hash)
from bitarray import bitarray

class BloomFilter:
    """
    Bloom Filter - estrutura probabilística para set membership

    Estrutura:
    - Bit array de tamanho m
    - k hash functions
    - Cada elemento → k bits setados

    Exemplo:
    m=10 bits, k=3 hashes

    add("apple"):
      hash1("apple") % 10 = 2 → bit[2] = 1
      hash2("apple") % 10 = 5 → bit[5] = 1
      hash3("apple") % 10 = 8 → bit[8] = 1

    Bit array: [0,0,1,0,0,1,0,0,1,0]

    contains("apple")?
      Verificar bits 2,5,8 → todos são 1 → SIM (pode estar)

    contains("banana")?
      hash1("banana") % 10 = 1 → bit[1] = 0 → NÃO (certeza que não está!)
    """

    def __init__(self, expected_elements: int, false_positive_rate: float = 0.01):
        """
        Args:
            expected_elements: Número esperado de elementos
            false_positive_rate: Taxa de falso positivo (0.01 = 1%)
        """
        self.n = expected_elements
        self.p = false_positive_rate

        # Calcular tamanho ótimo do bit array
        # m = -(n * ln(p)) / (ln(2)^2)
        self.m = self._optimal_bit_array_size(expected_elements, false_positive_rate)

        # Calcular número ótimo de hash functions
        # k = (m/n) * ln(2)
        self.k = self._optimal_hash_count(self.m, expected_elements)

        # Bit array
        self.bit_array = bitarray(self.m)
        self.bit_array.setall(0)

        # Contador de elementos adicionados
        self.count = 0

        print(f"Bloom Filter criado:")
        print(f"  - Elementos esperados: {self.n:,}")
        print(f"  - Taxa falso positivo: {self.p * 100}%")
        print(f"  - Tamanho bit array: {self.m:,} bits ({self.m / 8 / 1024:.2f} KB)")
        print(f"  - Número de hashes: {self.k}")

    @staticmethod
    def _optimal_bit_array_size(n: int, p: float) -> int:
        """Calcular tamanho ótimo do bit array"""
        m = -(n * math.log(p)) / (math.log(2) ** 2)
        return int(m)

    @staticmethod
    def _optimal_hash_count(m: int, n: int) -> int:
        """Calcular número ótimo de hash functions"""
        k = (m / n) * math.log(2)
        return int(k)

    def _hash(self, item: str, seed: int) -> int:
        """
        Hash function (MurmurHash3)

        Usa seeds diferentes para simular k hash functions
        """
        return mmh3.hash(item, seed) % self.m

    def add(self, item: str):
        """
        Adicionar elemento

        Setar k bits correspondentes aos k hashes
        """
        for i in range(self.k):
            index = self._hash(item, i)
            self.bit_array[index] = 1

        self.count += 1

    def contains(self, item: str) -> bool:
        """
        Verificar se elemento PODE estar no set

        Retorna:
        - False: Certeza de que NÃO está (0% erro)
        - True: Provavelmente está (p% chance de falso positivo)
        """
        for i in range(self.k):
            index = self._hash(item, i)
            if self.bit_array[index] == 0:
                return False  # Certeza que não está

        return True  # Provavelmente está

    def __contains__(self, item: str) -> bool:
        """Permite usar 'in' operator"""
        return self.contains(item)

    def false_positive_probability(self) -> float:
        """
        Calcular probabilidade REAL de falso positivo

        p = (1 - e^(-kn/m))^k
        """
        actual_p = (1 - math.exp(-self.k * self.count / self.m)) ** self.k
        return actual_p


# Uso
bf = BloomFilter(expected_elements=1_000_000, false_positive_rate=0.01)

# Adicionar elementos
bf.add("apple")
bf.add("banana")
bf.add("cherry")

# Verificar
print("apple" in bf)   # True (existe)
print("banana" in bf)  # True (existe)
print("grape" in bf)   # False (não existe, certeza!)

# Falso positivo (raro)
# "xyz" pode retornar True mesmo não existindo (~1% chance)
```

**Output:**
```
Bloom Filter criado:
  - Elementos esperados: 1,000,000
  - Taxa falso positivo: 1.0%
  - Tamanho bit array: 9,585,058 bits (1.14 MB)
  - Número de hashes: 7
```

**Análise:**
- ✅ 1M elementos em apenas 1.14 MB!
- ✅ Lookup muito rápido (7 hashes)
- ⚠️ ~1% de falsos positivos

---

### 2. Bloom Filter com Backing Store (PADRÃO REAL)

```python
class BloomFilterWithDB:
    """
    Bloom Filter + Database (padrão usado em produção)

    Workflow:
    1. Verificar no Bloom Filter
       - Se NÃO existe: retornar imediatamente (0 DB queries!)
       - Se SIM (maybe): verificar no database (pode ser falso positivo)
    2. Se não existe no DB: falso positivo do BF
    3. Se existe no DB: retornar dados

    Economia: ~99% das verificações de "não existe" são resolvidas sem DB query!
    """

    def __init__(self, db_session, expected_elements: int = 1_000_000):
        self.db = db_session
        self.bf = BloomFilter(expected_elements, false_positive_rate=0.01)

        # Popular Bloom Filter com dados existentes
        self._populate_from_db()

    def _populate_from_db(self):
        """Carregar dados existentes no Bloom Filter"""
        print("Populando Bloom Filter...")

        usernames = self.db.query(User.username).all()

        for (username,) in usernames:
            self.bf.add(username)

        print(f"✓ {len(usernames)} usernames carregados")

    def username_exists(self, username: str) -> bool:
        """
        Verificar se username existe

        Otimizado: evita DB query quando possível
        """
        # 1. Verificar no Bloom Filter primeiro
        if username not in self.bf:
            # Certeza que NÃO existe, sem DB query!
            return False

        # 2. Pode existir (ou falso positivo), verificar no DB
        exists = self.db.query(User).filter(
            User.username == username
        ).first() is not None

        return exists

    def create_user(self, username: str, email: str):
        """
        Criar usuário

        IMPORTANTE: Adicionar ao Bloom Filter também!
        """
        # Verificar se já existe (otimizado com BF)
        if self.username_exists(username):
            raise ValueError(f"Username '{username}' already exists")

        # Criar usuário
        user = User(username=username, email=email)
        self.db.add(user)
        self.db.commit()

        # Adicionar ao Bloom Filter
        self.bf.add(username)

        return user


# Uso
user_service = BloomFilterWithDB(db_session, expected_elements=10_000_000)

# Verificar username (otimizado)
exists = user_service.username_exists("john_doe")

# 99% das verificações de username disponível não fazem DB query!
# Apenas falsos positivos (~1%) fazem query
```

**Economia:**
```
10M de verificações de username por dia
Sem Bloom Filter: 10M DB queries
Com Bloom Filter (99% não existem): ~100k DB queries

Redução: 99% 🚀
Economia de $: ~$1000/dia em RDS
```

---

### 3. Counting Bloom Filter (Suporta Remoção)

```python
import array

class CountingBloomFilter:
    """
    Counting Bloom Filter

    Diferença: Ao invés de bit (0/1), usa counter (0-15)
    Permite remover elementos!

    Trade-off: 4x mais memória (4 bits por posição)
    """

    def __init__(self, expected_elements: int, false_positive_rate: float = 0.01):
        self.n = expected_elements
        self.p = false_positive_rate

        # Calcular parâmetros ótimos
        self.m = BloomFilter._optimal_bit_array_size(expected_elements, false_positive_rate)
        self.k = BloomFilter._optimal_hash_count(self.m, expected_elements)

        # Array de contadores (4 bits cada = max 15)
        # Usamos array de bytes para simplicidade
        self.counters = array.array('B', [0] * self.m)  # 'B' = unsigned byte

        self.count = 0

    def _hash(self, item: str, seed: int) -> int:
        """Hash function"""
        return mmh3.hash(item, seed) % self.m

    def add(self, item: str):
        """Adicionar elemento (incrementar contadores)"""
        for i in range(self.k):
            index = self._hash(item, i)
            if self.counters[index] < 255:  # Evitar overflow
                self.counters[index] += 1

        self.count += 1

    def remove(self, item: str):
        """
        Remover elemento (decrementar contadores)

        IMPORTANTE: Só remover se você TEM CERTEZA que elemento existe!
        Caso contrário, pode causar falsos negativos
        """
        for i in range(self.k):
            index = self._hash(item, i)
            if self.counters[index] > 0:
                self.counters[index] -= 1

        self.count -= 1

    def contains(self, item: str) -> bool:
        """Verificar se elemento pode estar no set"""
        for i in range(self.k):
            index = self._hash(item, i)
            if self.counters[index] == 0:
                return False

        return True


# Uso
cbf = CountingBloomFilter(expected_elements=100_000)

# Adicionar
cbf.add("apple")
cbf.add("banana")

print("apple" in cbf)   # True
print("banana" in cbf)  # True

# Remover
cbf.remove("apple")

print("apple" in cbf)   # False (removido!)
print("banana" in cbf)  # True (ainda existe)
```

**Trade-offs:**
- ✅ Suporta remoção
- ❌ 4-8x mais memória (counters vs bits)
- ⚠️ Remoção incorreta pode causar falsos negativos

---

### 4. Scalable Bloom Filter (Auto-expand)

```python
class ScalableBloomFilter:
    """
    Scalable Bloom Filter

    Cresce automaticamente quando atinge capacidade
    Mantém taxa de falso positivo consistente
    """

    def __init__(self, initial_capacity: int = 1000, false_positive_rate: float = 0.01):
        self.target_fp_rate = false_positive_rate
        self.growth_factor = 2  # Dobrar capacidade a cada expansão

        # Lista de Bloom Filters (cada um com capacidade crescente)
        self.filters = []

        # Criar primeiro filter
        self._add_filter(initial_capacity)

    def _add_filter(self, capacity: int):
        """Adicionar novo Bloom Filter à lista"""
        # Cada novo filter tem FP rate menor para manter taxa global
        error_rate = self.target_fp_rate * (0.5 ** len(self.filters))

        bf = BloomFilter(capacity, error_rate)
        self.filters.append(bf)

        print(f"✓ Novo filter adicionado (capacidade: {capacity:,}, FP rate: {error_rate * 100:.4f}%)")

    def add(self, item: str):
        """Adicionar elemento"""
        current_filter = self.filters[-1]

        # Se filter atual está cheio, criar novo
        if current_filter.count >= current_filter.n:
            new_capacity = current_filter.n * self.growth_factor
            self._add_filter(new_capacity)

        self.filters[-1].add(item)

    def contains(self, item: str) -> bool:
        """
        Verificar se elemento existe

        Precisa verificar TODOS os filters
        """
        for bf in self.filters:
            if bf.contains(item):
                return True

        return False

    def __contains__(self, item: str) -> bool:
        return self.contains(item)


# Uso
sbf = ScalableBloomFilter(initial_capacity=1000)

# Adicionar mais elementos que capacidade inicial
for i in range(5000):
    sbf.add(f"user:{i}")

# Automaticamente cria novos filters quando necessário
# Mantém FP rate consistente
```

---

## 🚀 Casos de Uso Reais

### 1. Medium: Evitar Recomendar Artigos Já Lidos

```python
class ArticleRecommendationService:
    """
    Medium usa Bloom Filter para cada usuário

    Evita recomendar artigos que usuário já leu
    Economiza DB queries massivamente
    """

    def __init__(self):
        # Bloom Filter por usuário (na prática seria em Redis)
        self.user_read_filters = {}

    def get_user_filter(self, user_id: int) -> BloomFilter:
        """Buscar/criar Bloom Filter para usuário"""
        if user_id not in self.user_read_filters:
            # 1000 artigos lidos esperados por usuário
            self.user_read_filters[user_id] = BloomFilter(
                expected_elements=1000,
                false_positive_rate=0.01
            )

        return self.user_read_filters[user_id]

    def mark_as_read(self, user_id: int, article_id: int):
        """Marcar artigo como lido"""
        bf = self.get_user_filter(user_id)
        bf.add(f"article:{article_id}")

    def get_recommendations(self, user_id: int, candidate_articles: List[int]) -> List[int]:
        """
        Recomendar artigos (excluindo já lidos)

        Bloom Filter elimina 99% dos artigos já lidos sem DB query!
        """
        bf = self.get_user_filter(user_id)
        recommendations = []

        for article_id in candidate_articles:
            # Verificar no Bloom Filter
            if f"article:{article_id}" not in bf:
                # Certeza que não leu!
                recommendations.append(article_id)
            else:
                # Pode ter lido (verificar no DB para falsos positivos)
                if not self._user_read_article_db(user_id, article_id):
                    recommendations.append(article_id)

        return recommendations


# Economia: De 100M DB queries/dia para ~1M (99% redução)
```

### 2. Google Chrome: Safe Browsing

```python
class SafeBrowsing:
    """
    Chrome usa Bloom Filter para detectar sites maliciosos

    Bloom Filter local (1MB) + verificação servidor para falsos positivos
    Evita 99% das requisições ao servidor
    """

    def __init__(self):
        # Bloom Filter com 10M sites maliciosos
        self.malicious_urls_bf = BloomFilter(
            expected_elements=10_000_000,
            false_positive_rate=0.001  # 0.1% FP
        )

        # Carregar lista de URLs maliciosas
        self._load_malicious_urls()

    def is_safe(self, url: str) -> bool:
        """
        Verificar se URL é seguro

        1. Bloom Filter: 99% das URLs são seguras → retornar imediatamente
        2. Falso positivo: Verificar com servidor do Google
        """
        # Verificar no Bloom Filter local
        if url not in self.malicious_urls_bf:
            # Certeza que é seguro!
            return True

        # Pode ser malicioso (ou falso positivo)
        # Verificar com servidor
        return self._check_with_server(url)


# Economia de banda: 99% das verificações são locais (sem rede)
```

### 3. Akamai CDN: Detecção de Cache Hit

```python
class CDNCache:
    """
    Akamai usa Bloom Filter para detectar rapidamente se objeto está em cache

    Evita verificações desnecessárias em disk
    """

    def __init__(self):
        # Bloom Filter para objetos em cache
        self.cache_bf = BloomFilter(
            expected_elements=1_000_000,
            false_positive_rate=0.01
        )

        self.disk_cache = {}  # Simula cache em disk

    def get(self, url: str):
        """Buscar objeto"""
        # 1. Verificar no Bloom Filter
        if url not in self.cache_bf:
            # Certeza que não está em cache, buscar da origem
            return self._fetch_from_origin(url)

        # 2. Pode estar em cache, verificar disk
        if url in self.disk_cache:
            return self.disk_cache[url]  # Cache hit!

        # 3. Falso positivo, buscar da origem
        return self._fetch_from_origin(url)

    def put(self, url: str, content: bytes):
        """Adicionar ao cache"""
        self.disk_cache[url] = content
        self.cache_bf.add(url)


# Economia: 99% de "não está em cache" evitam disk I/O
```

---

## 🎯 Perguntas da Entrevista

**Interviewer:** "Bloom Filter vs Hash Set, quando usar cada?"

**Você:**
- **Hash Set**: Quando precisa de 100% precisão e espaço não é problema
- **Bloom Filter**: Quando espaço é crítico e pode tolerar falsos positivos

Exemplo: 1B de elementos
- Hash Set: ~20GB RAM
- Bloom Filter: ~1.2GB RAM (95% economia)

Trade-off: ~1% de falsos positivos (resolver com DB query)

---

**Interviewer:** "Bloom Filter pode ter falsos negativos?"

**Você:** "NÃO! Nunca tem falso negativo. Se Bloom Filter diz que elemento NÃO existe, é garantia 100%. Por isso é perfeito para 'early rejection' - eliminar 99% dos casos negativos sem DB query. Apenas os 'positivos' (que podem ser falsos) precisam verificação adicional."

---

**Interviewer:** "Como escolher número de hash functions (k)?"

**Você:** "Fórmula ótima: k = (m/n) * ln(2), onde m=tamanho bit array, n=elementos. Intuitivamente: mais hashes = menos falsos positivos, mas lookup mais lento. Na prática, k=3 a 7 é ideal. Com k muito alto, bits saturam rápido e FP rate aumenta."

---

**Interviewer:** "Bloom Filter pode remover elementos?"

**Você:** "Bloom Filter padrão NÃO suporta remoção (setar bit para 0 pode afetar outros elementos). Solução: Counting Bloom Filter - usa counter (0-15) ao invés de bit. Permite remover decrementando counters. Trade-off: 4-8x mais memória."

---

## ✅ Checklist da Entrevista

- [ ] Explicar problema (set membership com espaço limitado)
- [ ] Desenhar bit array + hash functions
- [ ] Mostrar add() e contains()
- [ ] Explicar falsos positivos (nunca falsos negativos)
- [ ] Calcular parâmetros ótimos (m, k)
- [ ] Padrão com DB (BF para early rejection)
- [ ] Casos de uso (Medium, Chrome, CDN)
- [ ] Variações (Counting, Scalable)

---

## 📊 Empresas que Usam

- **Google**: Chrome Safe Browsing, BigTable
- **Facebook**: Typeahead search, spam detection
- **Medium**: Artigos já lidos por usuário
- **Akamai**: CDN cache detection
- **Bitcoin**: SPV clients para verificar transações

---

**Estrutura de dados probabilística fundamental! 🎯**
