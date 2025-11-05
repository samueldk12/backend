# 🚗 Projeto 8: Uber/Lyft (System Design)

> Location-based matching - aparece em 85% das entrevistas de big tech

---

## 📋 Problema

**Descrição:** Design de sistema de ride-sharing escalável para 100M usuários.

**Requisitos Funcionais:**
1. ✅ Passageiro solicita corrida
2. ✅ Matching automático com motorista próximo
3. ✅ Tracking em tempo real (GPS)
4. ✅ Cálculo de ETA e preço dinâmico (surge pricing)
5. ✅ Histórico de corridas
6. ✅ Avaliações (ratings)
7. ✅ Pagamento integrado

**Requisitos Não-Funcionais:**
1. 📊 **Escala**: 100M usuários, 10M corridas/dia
2. ⚡ **Latência**: Matching <5s, Location updates <1s
3. 💪 **Disponibilidade**: 99.99% uptime (SLA crítico!)
4. 🔄 **Consistência**: Strong consistency para matching
5. 📍 **Precisão**: GPS accuracy <10 metros

**Estimativas de Escala:**
```
Usuários: 100M total, 10M ativos/dia
Motoristas: 5M total, 1M ativos/dia
Corridas: 10M/dia = 115 corridas/segundo

Picos (rush hour): 3x média = 345 corridas/segundo

Location updates:
- 1M motoristas ativos * 1 update/3s = 333k updates/segundo
- 10M passageiros tracking * 1 update/5s = 2M updates/segundo
- Total: ~2.3M location updates/segundo (MASSIVO!)

Storage:
- Corridas: 10M/dia * 365 * 5 anos * 1KB = 18TB
- Location history: 2.3M/s * 3600*24 * 100 bytes = 19TB/dia (!)
  → Comprimir e archive para S3 após 30 dias

Bandwidth:
- Location updates: 2.3M/s * 100 bytes = 230 MB/s uplink
- Tracking: 10M clientes * 10 updates/s * 100 bytes = 10 GB/s downlink (!)
```

---

## 🏗️ High-Level Architecture

```
                       ┌─────────────┐
                       │   Cliente   │
                       │ (App Mobile)│
                       └──────┬──────┘
                              │
                          HTTPS/WSS
                              │
┌─────────────────────────────┼─────────────────────────────┐
│                             │                             │
│         ┌───────────────────▼──────────────┐             │
│         │  Load Balancer (NGINX/ALB)       │             │
│         └───────────────────┬──────────────┘             │
│                             │                             │
│         ┌───────────────────┴──────────────┐             │
│         │                                   │             │
│   ┌─────▼──────┐  ┌────────────┐  ┌───────▼────────┐    │
│   │   API      │  │  WebSocket │  │  Location      │    │
│   │  Gateway   │  │   Server   │  │   Service      │    │
│   └─────┬──────┘  └─────┬──────┘  └───────┬────────┘    │
│         │               │                  │             │
│         └───────────────┴──────────────────┘             │
│                         │                                │
│    ┌────────────────────┼────────────────────┐          │
│    │                    │                    │          │
│ ┌──▼─────────┐  ┌──────▼──────┐  ┌─────────▼──────┐   │
│ │   User     │  │   Matching  │  │    Pricing     │   │
│ │  Service   │  │   Service   │  │    Service     │   │
│ └──┬─────────┘  └──────┬──────┘  └─────────┬──────┘   │
│    │                   │                    │          │
└────┼───────────────────┼────────────────────┼──────────┘
     │                   │                    │
     ├───────────────────┴────────────────────┘
     │
┌────▼──────────────────────────────────────────────────┐
│                    DATA LAYER                         │
│                                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │  PostgreSQL  │  │    Redis     │  │  Kafka     │ │
│  │ (Users/Rides)│  │   (Cache)    │  │ (Events)   │ │
│  └──────────────┘  └──────────────┘  └────────────┘ │
│                                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │   Geohash    │  │  TimeSeries  │  │     S3     │ │
│  │ Index (Redis)│  │  DB (Influx) │  │  (Archive) │ │
│  └──────────────┘  └──────────────┘  └────────────┘ │
└───────────────────────────────────────────────────────┘

EXTERNAL SERVICES:
  - Google Maps API (ETA, routing)
  - Stripe/Payment Gateway
  - Twilio (SMS notifications)
  - Firebase (Push notifications)
```

---

## 🗄️ Database Design

### 1. Schema SQL (PostgreSQL)

```sql
-- Usuários
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    phone VARCHAR(20) UNIQUE NOT NULL,
    email VARCHAR(255),
    name VARCHAR(100),
    user_type VARCHAR(20) NOT NULL, -- 'rider' ou 'driver'
    rating DECIMAL(3,2) DEFAULT 5.0,
    total_rides INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_phone (phone),
    INDEX idx_user_type (user_type)
);

-- Motoristas (estende users)
CREATE TABLE drivers (
    user_id BIGINT PRIMARY KEY REFERENCES users(id),
    vehicle_type VARCHAR(50), -- 'UberX', 'UberXL', 'Uber Black'
    vehicle_model VARCHAR(100),
    license_plate VARCHAR(20),
    documents_verified BOOLEAN DEFAULT FALSE,
    status VARCHAR(20) DEFAULT 'offline', -- 'offline', 'online', 'busy'
    current_lat DECIMAL(10,8),
    current_lng DECIMAL(11,8),
    last_location_update TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_location (current_lat, current_lng)
);

-- Corridas
CREATE TABLE rides (
    id BIGSERIAL PRIMARY KEY,
    rider_id BIGINT NOT NULL REFERENCES users(id),
    driver_id BIGINT REFERENCES users(id),

    -- Localização
    pickup_lat DECIMAL(10,8) NOT NULL,
    pickup_lng DECIMAL(11,8) NOT NULL,
    pickup_address TEXT,
    dropoff_lat DECIMAL(10,8),
    dropoff_lng DECIMAL(11,8),
    dropoff_address TEXT,

    -- Status
    status VARCHAR(20) NOT NULL, -- 'requested', 'matched', 'arrived', 'started', 'completed', 'cancelled'

    -- Pricing
    estimated_price DECIMAL(10,2),
    final_price DECIMAL(10,2),
    surge_multiplier DECIMAL(3,2) DEFAULT 1.0,

    -- Timestamps
    requested_at TIMESTAMP DEFAULT NOW(),
    matched_at TIMESTAMP,
    arrived_at TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,

    -- Ratings
    rider_rating INTEGER CHECK (rider_rating BETWEEN 1 AND 5),
    driver_rating INTEGER CHECK (driver_rating BETWEEN 1 AND 5),

    INDEX idx_rider (rider_id),
    INDEX idx_driver (driver_id),
    INDEX idx_status (status),
    INDEX idx_requested_at (requested_at)
);

-- Location history (particionada por tempo)
CREATE TABLE location_history (
    id BIGSERIAL,
    user_id BIGINT NOT NULL,
    lat DECIMAL(10,8) NOT NULL,
    lng DECIMAL(11,8) NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, timestamp)
) PARTITION BY RANGE (timestamp);

-- Partições mensais
CREATE TABLE location_history_2024_01 PARTITION OF location_history
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

CREATE TABLE location_history_2024_02 PARTITION OF location_history
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');
-- ...
```

---

## 🌍 Geospatial Indexing (CRÍTICO!)

### Problema: Encontrar motoristas próximos RÁPIDO

**Abordagem Ingênua (ERRADA):**
```sql
-- ❌ HORRÍVEL: Escaneia TODOS motoristas
SELECT * FROM drivers
WHERE status = 'online'
  AND SQRT(POW(current_lat - ?, 2) + POW(current_lng - ?, 2)) < 0.01
ORDER BY distance
LIMIT 10;

-- Complexidade: O(N) onde N = todos motoristas
-- Com 1M motoristas: ~500ms (INACEITÁVEL!)
```

### Solução 1: Geohash (RECOMENDADO)

```python
import geohash2

class GeohashIndex:
    """
    Geohash: Divide mundo em grid hierárquico

    Exemplo:
    geohash("37.7749, -122.4194", precision=6) → "9q8yy"

    Precision:
    1 = ±2500km (continente)
    2 = ±630km  (estado)
    3 = ±78km   (cidade)
    4 = ±20km
    5 = ±2.4km
    6 = ±610m   ← IDEAL para Uber
    7 = ±76m
    8 = ±19m
    """

    def __init__(self, redis_client):
        self.redis = redis_client
        self.precision = 6  # ~610m per cell

    def index_driver(self, driver_id: int, lat: float, lng: float):
        """
        Indexar motorista no geohash

        Redis: geohash:{hash} → Set[driver_id]
        """
        gh = geohash2.encode(lat, lng, precision=self.precision)
        key = f"geohash:{gh}"

        # Adicionar ao set
        self.redis.sadd(key, driver_id)

        # TTL de 5 minutos (motorista precisa enviar location update)
        self.redis.expire(key, 300)

        # Salvar metadata do motorista
        self.redis.setex(
            f"driver:{driver_id}:location",
            300,
            f"{lat},{lng}"
        )

    def find_nearby_drivers(
        self,
        lat: float,
        lng: float,
        radius_km: float = 5,
        limit: int = 10
    ) -> List[int]:
        """
        Buscar motoristas próximos

        Algoritmo:
        1. Calcular geohash do rider
        2. Buscar na célula atual + 8 células vizinhas
        3. Filtrar por distância real (Haversine)
        4. Ordenar por distância
        """
        gh_center = geohash2.encode(lat, lng, precision=self.precision)

        # Buscar célula atual + vizinhos
        geohashes_to_check = [gh_center] + geohash2.neighbors(gh_center)

        driver_ids = set()

        for gh in geohashes_to_check:
            key = f"geohash:{gh}"
            ids = self.redis.smembers(key)
            driver_ids.update([int(id_) for id_ in ids])

        # Filtrar por distância real
        nearby_drivers = []

        for driver_id in driver_ids:
            location = self.redis.get(f"driver:{driver_id}:location")

            if not location:
                continue

            driver_lat, driver_lng = map(float, location.decode().split(','))

            distance = haversine_distance(lat, lng, driver_lat, driver_lng)

            if distance <= radius_km:
                nearby_drivers.append({
                    'driver_id': driver_id,
                    'distance_km': distance,
                    'lat': driver_lat,
                    'lng': driver_lng
                })

        # Ordenar por distância
        nearby_drivers.sort(key=lambda d: d['distance_km'])

        return nearby_drivers[:limit]

    def remove_driver(self, driver_id: int, lat: float, lng: float):
        """Remover motorista (quando vai offline ou aceita corrida)"""
        gh = geohash2.encode(lat, lng, precision=self.precision)
        key = f"geohash:{gh}"

        self.redis.srem(key, driver_id)
        self.redis.delete(f"driver:{driver_id}:location")


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Calcular distância entre 2 pontos (Haversine formula)

    Retorna: distância em KM
    """
    from math import radians, sin, cos, sqrt, atan2

    R = 6371  # Raio da Terra em km

    lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])

    dlat = lat2 - lat1
    dlng = lng2 - lng1

    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))

    return R * c
```

**Complexidade:**
- Indexar: O(1)
- Buscar: O(9 * k) onde k = motoristas por célula (~10-50)
- **Total: O(1) na prática!**

**Benchmark:**
```
1M motoristas online
Query radius: 5km

Geohash: 5-10ms ✅
Brute force: 500ms ❌

Speedup: 50-100x!
```

### Solução 2: Redis GEO (Alternativa Simples)

```python
class RedisGeoIndex:
    """
    Redis GEO commands (usa Geohash internamente)

    Mais simples mas menos flexível
    """

    def __init__(self, redis_client):
        self.redis = redis_client

    def index_driver(self, driver_id: int, lat: float, lng: float):
        """Adicionar motorista"""
        self.redis.geoadd('drivers:online', lng, lat, driver_id)
        # Nota: Redis GEO usa (lng, lat) não (lat, lng)!

    def find_nearby_drivers(
        self,
        lat: float,
        lng: float,
        radius_km: float = 5,
        limit: int = 10
    ):
        """Buscar motoristas próximos"""
        results = self.redis.georadius(
            'drivers:online',
            lng, lat,
            radius_km,
            unit='km',
            withdist=True,  # Incluir distância
            sort='ASC',     # Ordenar por distância
            count=limit
        )

        nearby = [
            {
                'driver_id': int(driver_id),
                'distance_km': float(distance)
            }
            for driver_id, distance in results
        ]

        return nearby

    def remove_driver(self, driver_id: int):
        """Remover motorista"""
        self.redis.zrem('drivers:online', driver_id)
```

**Quando usar cada:**
- **Geohash manual**: Mais controle, suporta sharding complexo
- **Redis GEO**: Simples, suficiente para 80% dos casos

---

## 🎯 Core Features

### 1. Solicitar Corrida (Ride Request)

```python
from fastapi import FastAPI, WebSocket, HTTPException
from pydantic import BaseModel
import uuid

app = FastAPI()

class RideRequest(BaseModel):
    rider_id: int
    pickup_lat: float
    pickup_lng: float
    dropoff_lat: float
    dropoff_lng: float


@app.post("/rides/request")
async def request_ride(request: RideRequest):
    """
    Solicitar corrida

    Workflow:
    1. Validar request
    2. Calcular preço estimado
    3. Buscar motoristas próximos
    4. Criar ride no DB (status='requested')
    5. Enviar matching request assíncrono
    """
    # 1. Validar
    rider = get_user(request.rider_id)

    if not rider or rider.user_type != 'rider':
        raise HTTPException(400, "Invalid rider")

    # 2. Calcular preço estimado (ver seção Pricing)
    estimated_price, surge_multiplier = calculate_price(
        pickup_lat=request.pickup_lat,
        pickup_lng=request.pickup_lng,
        dropoff_lat=request.dropoff_lat,
        dropoff_lng=request.dropoff_lng
    )

    # 3. Buscar motoristas próximos
    geo_index = GeohashIndex(redis_client)

    nearby_drivers = geo_index.find_nearby_drivers(
        lat=request.pickup_lat,
        lng=request.pickup_lng,
        radius_km=5,
        limit=20
    )

    if not nearby_drivers:
        raise HTTPException(404, "No drivers available nearby")

    # 4. Criar ride
    ride_id = create_ride(
        rider_id=request.rider_id,
        pickup_lat=request.pickup_lat,
        pickup_lng=request.pickup_lng,
        dropoff_lat=request.dropoff_lat,
        dropoff_lng=request.dropoff_lng,
        estimated_price=estimated_price,
        surge_multiplier=surge_multiplier,
        status='requested'
    )

    # 5. Matching assíncrono (Kafka)
    kafka_producer.send('ride_matching', {
        'ride_id': ride_id,
        'rider_id': request.rider_id,
        'pickup_lat': request.pickup_lat,
        'pickup_lng': request.pickup_lng,
        'nearby_drivers': [d['driver_id'] for d in nearby_drivers]
    })

    return {
        'ride_id': ride_id,
        'estimated_price': estimated_price,
        'surge_multiplier': surge_multiplier,
        'status': 'searching_for_driver'
    }
```

### 2. Matching Algorithm

```python
import time
from typing import Optional

def matching_worker():
    """
    Worker de matching (Kafka Consumer)

    Algoritmo:
    1. Receber ride request
    2. Tentar match com motoristas próximos (em ordem de distância)
    3. Enviar notificação para motorista via push
    4. Esperar 15s por aceitação
    5. Se timeout, tentar próximo motorista
    6. Repetir até match ou timeout total (2 minutos)
    """
    from kafka import KafkaConsumer

    consumer = KafkaConsumer('ride_matching', bootstrap_servers=['kafka:9092'])

    for message in consumer:
        data = message.value

        ride_id = data['ride_id']
        rider_id = data['rider_id']
        nearby_drivers = data['nearby_drivers']

        # Tentar match
        matched = try_match_ride(ride_id, nearby_drivers)

        if not matched:
            # Nenhum motorista aceitou
            update_ride_status(ride_id, 'no_drivers_available')
            notify_rider(rider_id, 'No drivers available, please try again')


def try_match_ride(ride_id: int, nearby_drivers: List[int]) -> bool:
    """
    Tentar match com motoristas

    Retorna True se matched, False se timeout
    """
    MAX_ATTEMPTS = 5
    TIMEOUT_PER_DRIVER = 15  # segundos

    for i, driver_id in enumerate(nearby_drivers[:MAX_ATTEMPTS]):
        # Verificar se motorista ainda está online
        driver_status = redis_client.get(f"driver:{driver_id}:status")

        if driver_status != b'online':
            continue  # Pular

        # Lock: Garantir que motorista não receba múltiplos requests
        lock_key = f"driver_lock:{driver_id}"
        acquired = redis_client.set(lock_key, ride_id, nx=True, ex=TIMEOUT_PER_DRIVER)

        if not acquired:
            continue  # Motorista já tem request pendente

        # Enviar notificação para motorista
        send_push_notification(
            driver_id,
            title="New ride request!",
            body="Pickup in 5 minutes",
            data={
                'ride_id': ride_id,
                'pickup_lat': '...',
                'pickup_lng': '...'
            }
        )

        # Marcar como pending
        redis_client.setex(
            f"ride:{ride_id}:pending_driver",
            TIMEOUT_PER_DRIVER,
            driver_id
        )

        # Esperar aceitação (com timeout)
        start_time = time.time()

        while time.time() - start_time < TIMEOUT_PER_DRIVER:
            # Verificar se motorista aceitou
            accepted = redis_client.get(f"ride:{ride_id}:accepted")

            if accepted:
                # Match sucesso!
                finalize_match(ride_id, driver_id)
                return True

            time.sleep(0.5)

        # Timeout, liberar lock e tentar próximo
        redis_client.delete(lock_key)

    # Nenhum motorista aceitou
    return False


@app.post("/rides/{ride_id}/accept")
async def accept_ride(ride_id: int, driver_id: int):
    """
    Motorista aceitar corrida

    Operações atômicas para evitar double-booking
    """
    # Verificar se request ainda está pending para esse motorista
    pending_driver = redis_client.get(f"ride:{ride_id}:pending_driver")

    if not pending_driver or int(pending_driver) != driver_id:
        raise HTTPException(400, "Ride request expired or already accepted")

    # Atômico: Marcar como accepted (CAS)
    accepted = redis_client.set(
        f"ride:{ride_id}:accepted",
        driver_id,
        nx=True,  # Apenas se não existir
        ex=60
    )

    if not accepted:
        raise HTTPException(409, "Ride already accepted by another driver")

    # Finalizar match
    finalize_match(ride_id, driver_id)

    return {"status": "accepted", "ride_id": ride_id}


def finalize_match(ride_id: int, driver_id: int):
    """
    Finalizar match (atualizar DB, notificar, etc)
    """
    # Atualizar DB
    db.execute("""
        UPDATE rides
        SET driver_id = ?, status = 'matched', matched_at = NOW()
        WHERE id = ?
    """, (driver_id, ride_id))

    # Atualizar status do motorista
    db.execute("""
        UPDATE drivers
        SET status = 'busy'
        WHERE user_id = ?
    """, (driver_id,))

    # Remover motorista do geohash index
    driver_location = get_driver_location(driver_id)
    geo_index.remove_driver(driver_id, driver_location['lat'], driver_location['lng'])

    # Notificar rider
    ride = get_ride(ride_id)
    notify_rider(
        ride.rider_id,
        f"Driver matched! ETA: 5 minutes",
        data={'driver_id': driver_id, 'ride_id': ride_id}
    )

    # Notificar driver
    notify_driver(
        driver_id,
        f"Ride confirmed! Navigate to pickup location",
        data={'ride_id': ride_id}
    )
```

### 3. Real-Time Tracking (WebSocket)

```python
from typing import Dict
import json

class TrackingManager:
    """Gerenciar tracking de corridas"""

    def __init__(self):
        # ride_id -> Set[WebSocket]
        self.active_rides: Dict[int, set] = {}

    async def connect(self, websocket: WebSocket, ride_id: int):
        """Conectar cliente (rider ou driver) ao tracking"""
        await websocket.accept()

        if ride_id not in self.active_rides:
            self.active_rides[ride_id] = set()

        self.active_rides[ride_id].add(websocket)

    async def disconnect(self, websocket: WebSocket, ride_id: int):
        """Desconectar"""
        if ride_id in self.active_rides:
            self.active_rides[ride_id].discard(websocket)

    async def broadcast_location(self, ride_id: int, location: dict):
        """Broadcast location update para todos conectados à corrida"""
        if ride_id not in self.active_rides:
            return

        disconnected = set()

        for websocket in self.active_rides[ride_id]:
            try:
                await websocket.send_json(location)
            except:
                disconnected.add(websocket)

        # Limpar conexões mortas
        self.active_rides[ride_id] -= disconnected


tracking_manager = TrackingManager()


@app.websocket("/rides/{ride_id}/track")
async def track_ride(websocket: WebSocket, ride_id: int):
    """
    WebSocket para tracking em tempo real

    Cliente recebe location updates do motorista
    """
    await tracking_manager.connect(websocket, ride_id)

    try:
        while True:
            # Heartbeat (manter conexão viva)
            await websocket.receive_text()
    except:
        await tracking_manager.disconnect(websocket, ride_id)


@app.post("/drivers/location")
async def update_driver_location(
    driver_id: int,
    lat: float,
    lng: float
):
    """
    Motorista enviar location update (a cada 3-5 segundos)

    Atualiza:
    1. Geohash index (para matching)
    2. Current ride tracking (se em corrida)
    3. Location history (para analytics)
    """
    # 1. Atualizar geohash index
    driver = get_driver(driver_id)

    if driver.status == 'online':
        geo_index.index_driver(driver_id, lat, lng)

    # 2. Se em corrida, broadcast para tracking
    current_ride = get_driver_current_ride(driver_id)

    if current_ride:
        await tracking_manager.broadcast_location(
            current_ride.id,
            {
                'driver_lat': lat,
                'driver_lng': lng,
                'timestamp': time.time()
            }
        )

    # 3. Salvar location history (assíncrono)
    kafka_producer.send('location_history', {
        'user_id': driver_id,
        'lat': lat,
        'lng': lng,
        'timestamp': time.time()
    })

    return {"status": "ok"}
```

### 4. Dynamic Pricing (Surge Pricing)

```python
def calculate_price(
    pickup_lat: float,
    pickup_lng: float,
    dropoff_lat: float,
    dropoff_lng: float
) -> tuple[float, float]:
    """
    Calcular preço dinâmico

    Fatores:
    1. Distância (Google Maps API)
    2. Tempo estimado (ETA)
    3. Demanda vs Oferta (surge multiplier)
    4. Horário (rush hour +20%)
    5. Clima (chuva +30%)
    """
    # 1. Calcular distância e tempo
    distance_km, duration_min = get_route_info(
        pickup_lat, pickup_lng,
        dropoff_lat, dropoff_lng
    )

    # 2. Preço base
    BASE_FARE = 5.00  # USD
    PER_KM = 2.00
    PER_MIN = 0.50

    base_price = BASE_FARE + (distance_km * PER_KM) + (duration_min * PER_MIN)

    # 3. Calcular surge multiplier
    surge_multiplier = calculate_surge_multiplier(pickup_lat, pickup_lng)

    # 4. Ajustes adicionais
    hour = datetime.now().hour

    # Rush hour (7-9am, 5-7pm)
    if hour in [7, 8, 17, 18]:
        surge_multiplier *= 1.2

    # Clima (verificar API)
    if is_raining(pickup_lat, pickup_lng):
        surge_multiplier *= 1.3

    # 5. Preço final
    final_price = base_price * surge_multiplier

    # Min/max
    final_price = max(final_price, 8.00)  # Mínimo $8
    final_price = min(final_price, 500.00)  # Máximo $500

    return round(final_price, 2), round(surge_multiplier, 2)


def calculate_surge_multiplier(lat: float, lng: float) -> float:
    """
    Calcular surge baseado em demanda/oferta

    Surge = Demand / Supply

    Usa geohash para agregar métricas por região
    """
    gh = geohash2.encode(lat, lng, precision=5)  # ~2.4km cell

    # Contar rides requested (últimos 10 minutos)
    demand_key = f"demand:{gh}"
    demand = int(redis_client.get(demand_key) or 0)

    # Contar drivers online
    supply = len(geo_index.find_nearby_drivers(lat, lng, radius_km=3))

    if supply == 0:
        return 2.0  # Surge máximo

    # Fórmula surge
    ratio = demand / supply

    if ratio < 1.0:
        return 1.0  # Sem surge
    elif ratio < 2.0:
        return 1.5
    elif ratio < 3.0:
        return 2.0
    else:
        return 2.5  # Surge máximo


# Worker para atualizar métricas de demanda
def demand_tracking_worker():
    """
    Consumir ride requests e incrementar contador de demanda por região
    """
    consumer = KafkaConsumer('ride_matching', bootstrap_servers=['kafka:9092'])

    for message in consumer:
        data = message.value

        lat = data['pickup_lat']
        lng = data['pickup_lng']

        gh = geohash2.encode(lat, lng, precision=5)
        demand_key = f"demand:{gh}"

        # Incrementar (TTL 10 minutos)
        redis_client.incr(demand_key)
        redis_client.expire(demand_key, 600)
```

---

## 🎯 Perguntas da Entrevista

**Interviewer:** "Como você garante que 2 motoristas não aceitam a mesma corrida?"

**Você:** "Distributed lock com Redis:
1. Quando matching tenta driver, adquire lock: `SET driver_lock:{driver_id} {ride_id} NX EX 15`
2. Quando motorista aceita, usa CAS (Compare-And-Set): `SET ride:{ride_id}:accepted {driver_id} NX`
3. Se CAS falha = outro motorista já aceitou (409 Conflict)
4. Lock expira em 15s se motorista não responde"

---

**Interviewer:** "Como escalar location updates (2M/segundo)?"

**Você:** "Estratégias:
1. **Batch updates**: Cliente envia 3-5 locations de uma vez (reduz HTTP overhead)
2. **Adaptive rate**: Se motorista parado, reduzir rate (1 update/10s). Se em movimento, aumentar (1 update/3s)
3. **UDP ao invés de HTTP**: Para location updates (tolerar packet loss)
4. **Sharding**: Particionar motoristas por geohash prefix (SF=9q8, NYC=dr5)
5. **Sampling**: Archive apenas 1 em 10 locations para history (analytics não precisa de todas)"

---

**Interviewer:** "Geohash vs Quadtree, qual é melhor?"

**Você:** "Depende:

**Geohash**: ✅ Simples, ✅ Funciona em Redis, ⚠️ Células fixas (pode ter hotspots em áreas densas)

**Quadtree**: ✅ Adaptativo (subdivide células densas), ❌ Complexo de implementar, ❌ Não tem suporte nativo em Redis

Para Uber: Geohash é suficiente. Quadtree só vale se tiver hotspots extremos (ex: Times Square no NYE)"

---

## ✅ Checklist da Entrevista

- [ ] Estimar escala (QPS, location updates, storage)
- [ ] Desenhar arquitetura high-level
- [ ] Explicar geospatial indexing (Geohash)
- [ ] Implementar matching algorithm
- [ ] Real-time tracking (WebSocket)
- [ ] Dynamic pricing (surge)
- [ ] Concorrência (distributed locks)
- [ ] Sharding strategy
- [ ] Otimizações (caching, batching)

---

**System design extremamente comum em entrevistas! 🚗**
