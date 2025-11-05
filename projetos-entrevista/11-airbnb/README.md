# 🏠 Projeto 11: Airbnb (System Design)

> Booking system - aparece em 70% das entrevistas de transactional systems

---

## 📋 Problema

**Design de plataforma de reservas para 150M usuários e 7M listings.**

**Estimativas:**
```
Usuários: 150M total, 10M bookings/mês
Listings: 7M propriedades globalmente
Buscas: 500M searches/dia = 5,800 searches/segundo

Peak (véspera de feriado): 10x média = 58k searches/segundo

Storage:
- Listings: 7M * 5KB (metadata) = 35GB
- Fotos: 7M * 20 fotos * 500KB = 70TB
- Bookings: 120M/ano * 2KB = 240GB/ano

Revenue: $1B+ em comissões (10-15% por booking)
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  SEARCH & BOOKING FLOW                  │
│                                                         │
│  Search → Results → Details → Reserve → Payment        │
│     │        │         │         │          │          │
│  ElasticSearch  Cache  PostgreSQL  Lock   Stripe      │
│  (Geo + filters)       (listings)  (ACID)  (payment)  │
└─────────────────────────────────────────────────────────┘

SERVICES:
- Search Service: ElasticSearch + geospatial
- Listing Service: CRUD de propriedades
- Booking Service: Reservas (transactional)
- Calendar Service: Disponibilidade
- Payment Service: Stripe integration
- Review Service: Ratings e comentários
- Recommendation: ML-based
```

---

## 🗄️ Database Schema

```sql
-- Propriedades
CREATE TABLE listings (
    id BIGSERIAL PRIMARY KEY,
    host_id BIGINT NOT NULL REFERENCES users(id),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    property_type VARCHAR(50), -- 'apartment', 'house', 'room'

    -- Localização
    latitude DECIMAL(10,8) NOT NULL,
    longitude DECIMAL(11,8) NOT NULL,
    address TEXT,
    city VARCHAR(100),
    country VARCHAR(100),

    -- Capacidade
    max_guests INTEGER,
    bedrooms INTEGER,
    beds INTEGER,
    bathrooms INTEGER,

    -- Pricing
    base_price DECIMAL(10,2),
    cleaning_fee DECIMAL(10,2),
    currency VARCHAR(3) DEFAULT 'USD',

    -- Amenities (JSON)
    amenities JSONB, -- ["wifi", "kitchen", "parking", ...]

    -- Stats
    rating DECIMAL(3,2),
    review_count INTEGER DEFAULT 0,

    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_location (latitude, longitude),
    INDEX idx_city (city),
    INDEX idx_price (base_price)
);

-- Fotos
CREATE TABLE listing_photos (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    caption TEXT,
    position INTEGER DEFAULT 0,
    INDEX idx_listing (listing_id)
);

-- Reservas (CRITICAL: transactional integrity!)
CREATE TABLE bookings (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT NOT NULL REFERENCES listings(id),
    guest_id BIGINT NOT NULL REFERENCES users(id),

    -- Datas
    check_in DATE NOT NULL,
    check_out DATE NOT NULL,

    -- Pricing
    num_guests INTEGER NOT NULL,
    num_nights INTEGER NOT NULL,
    price_per_night DECIMAL(10,2),
    cleaning_fee DECIMAL(10,2),
    service_fee DECIMAL(10,2),
    total_price DECIMAL(10,2) NOT NULL,

    -- Status
    status VARCHAR(20) NOT NULL, -- 'pending', 'confirmed', 'cancelled'

    -- Payment
    payment_intent_id VARCHAR(255), -- Stripe payment intent

    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_listing (listing_id),
    INDEX idx_guest (guest_id),
    INDEX idx_dates (check_in, check_out),
    INDEX idx_status (status),

    -- CRITICAL: Prevent double booking
    CONSTRAINT unique_listing_dates UNIQUE (listing_id, check_in, check_out)
);

-- Calendário (disponibilidade)
CREATE TABLE calendar (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    available BOOLEAN DEFAULT TRUE,
    price DECIMAL(10,2), -- Dynamic pricing (pode variar por dia)
    min_nights INTEGER DEFAULT 1,

    PRIMARY KEY (listing_id, date),
    INDEX idx_listing_date (listing_id, date)
);

-- Reviews
CREATE TABLE reviews (
    id BIGSERIAL PRIMARY KEY,
    booking_id BIGINT NOT NULL REFERENCES bookings(id),
    listing_id BIGINT NOT NULL REFERENCES listings(id),
    guest_id BIGINT NOT NULL REFERENCES users(id),

    rating INTEGER CHECK (rating BETWEEN 1 AND 5),
    comment TEXT,

    -- Ratings por categoria
    cleanliness INTEGER CHECK (cleanliness BETWEEN 1 AND 5),
    communication INTEGER CHECK (communication BETWEEN 1 AND 5),
    check_in INTEGER CHECK (check_in BETWEEN 1 AND 5),
    accuracy INTEGER CHECK (accuracy BETWEEN 1 AND 5),
    location INTEGER CHECK (location BETWEEN 1 AND 5),
    value INTEGER CHECK (value BETWEEN 1 AND 5),

    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_listing (listing_id),
    INDEX idx_guest (guest_id)
);
```

---

## 🔍 Search (Geospatial + Filters)

```python
from elasticsearch import Elasticsearch

es = Elasticsearch(['es1', 'es2', 'es3'])


def index_listing(listing: dict):
    """
    Indexar listing no ElasticSearch

    Executar quando:
    - Novo listing criado
    - Listing atualizado
    - Review adicionada (atualizar rating)
    """
    doc = {
        'id': listing['id'],
        'title': listing['title'],
        'description': listing['description'],
        'property_type': listing['property_type'],

        # Geolocation (formato especial)
        'location': {
            'lat': listing['latitude'],
            'lon': listing['longitude']
        },

        'city': listing['city'],
        'country': listing['country'],

        'max_guests': listing['max_guests'],
        'bedrooms': listing['bedrooms'],
        'base_price': listing['base_price'],
        'amenities': listing['amenities'],

        'rating': listing['rating'],
        'review_count': listing['review_count']
    }

    es.index(index='listings', id=listing['id'], document=doc)


@app.get("/search")
async def search_listings(
    # Localização
    lat: float = None,
    lng: float = None,
    city: str = None,
    radius_km: int = 10,

    # Datas
    check_in: date = None,
    check_out: date = None,

    # Capacidade
    guests: int = 1,

    # Filters
    min_price: float = None,
    max_price: float = None,
    property_type: str = None,
    amenities: List[str] = None,
    min_rating: float = None,

    # Pagination
    page: int = 1,
    per_page: int = 20
):
    """
    Buscar listings

    Query complexa: geo + filters + availability + sorting
    """
    # Construir query ElasticSearch
    must_clauses = []
    filter_clauses = []

    # 1. Geospatial (CRITICAL!)
    if lat and lng:
        filter_clauses.append({
            'geo_distance': {
                'distance': f'{radius_km}km',
                'location': {'lat': lat, 'lon': lng}
            }
        })
    elif city:
        must_clauses.append({
            'match': {'city': city}
        })

    # 2. Capacidade
    filter_clauses.append({
        'range': {'max_guests': {'gte': guests}}
    })

    # 3. Price range
    if min_price or max_price:
        price_range = {}
        if min_price:
            price_range['gte'] = min_price
        if max_price:
            price_range['lte'] = max_price

        filter_clauses.append({
            'range': {'base_price': price_range}
        })

    # 4. Property type
    if property_type:
        filter_clauses.append({
            'term': {'property_type': property_type}
        })

    # 5. Amenities
    if amenities:
        for amenity in amenities:
            must_clauses.append({
                'term': {'amenities': amenity}
            })

    # 6. Rating
    if min_rating:
        filter_clauses.append({
            'range': {'rating': {'gte': min_rating}}
        })

    # Query completa
    query = {
        'bool': {
            'must': must_clauses,
            'filter': filter_clauses
        }
    }

    # Sorting
    sort = [
        {'_geo_distance': {
            'location': {'lat': lat, 'lon': lng},
            'order': 'asc',
            'unit': 'km'
        }} if lat and lng else {'rating': {'order': 'desc'}}
    ]

    # Execute search
    results = es.search(
        index='listings',
        body={
            'query': query,
            'sort': sort,
            'from': (page - 1) * per_page,
            'size': per_page
        }
    )

    # Parse results
    listings = [hit['_source'] for hit in results['hits']['hits']]

    # 7. Filter por disponibilidade (check DB)
    if check_in and check_out:
        available_listings = []

        for listing in listings:
            if is_available(listing['id'], check_in, check_out):
                # Calcular preço total para essas datas
                listing['total_price'] = calculate_total_price(
                    listing['id'],
                    check_in,
                    check_out,
                    guests
                )
                available_listings.append(listing)

        listings = available_listings

    return {
        'listings': listings,
        'total': len(listings),
        'page': page
    }


def is_available(listing_id: int, check_in: date, check_out: date) -> bool:
    """
    Verificar disponibilidade no calendário

    Verifica:
    1. Nenhum dia está marcado como indisponível
    2. Não há booking conflitante
    """
    # Verificar calendário
    query = """
        SELECT COUNT(*) FROM calendar
        WHERE listing_id = ?
          AND date BETWEEN ? AND ?
          AND available = FALSE
    """
    unavailable_days = db.execute(query, (listing_id, check_in, check_out)).scalar()

    if unavailable_days > 0:
        return False

    # Verificar bookings conflitantes
    query = """
        SELECT COUNT(*) FROM bookings
        WHERE listing_id = ?
          AND status IN ('confirmed', 'pending')
          AND (
            (check_in <= ? AND check_out > ?) OR
            (check_in < ? AND check_out >= ?) OR
            (check_in >= ? AND check_out <= ?)
          )
    """
    conflicting = db.execute(
        query,
        (listing_id, check_in, check_in, check_out, check_out, check_in, check_out)
    ).scalar()

    return conflicting == 0
```

---

## 🔒 Booking (ACID Transaction)

```python
from sqlalchemy.exc import IntegrityError
import stripe

stripe.api_key = STRIPE_SECRET_KEY


@app.post("/bookings")
async def create_booking(
    guest_id: int,
    listing_id: int,
    check_in: date,
    check_out: date,
    num_guests: int
):
    """
    Criar reserva

    CRITICAL: ACID transaction para evitar double booking

    Flow:
    1. Verificar disponibilidade (com lock)
    2. Calcular preço
    3. Criar payment intent (Stripe)
    4. Criar booking (DB transaction)
    5. Marcar datas como indisponíveis
    """
    # Validar datas
    if check_in >= check_out:
        raise HTTPException(400, "Invalid dates")

    if check_in < date.today():
        raise HTTPException(400, "Check-in date must be in the future")

    num_nights = (check_out - check_in).days

    # Calcular preço
    total_price = calculate_total_price(listing_id, check_in, check_out, num_guests)

    # Adquirir distributed lock (Redis)
    lock_key = f"booking_lock:{listing_id}:{check_in}:{check_out}"
    lock = redis_client.set(lock_key, guest_id, nx=True, ex=10)

    if not lock:
        raise HTTPException(409, "Listing is being booked by someone else, try again")

    try:
        # Verificar disponibilidade (dentro do lock)
        if not is_available(listing_id, check_in, check_out):
            raise HTTPException(409, "Listing not available for these dates")

        # Criar payment intent (Stripe)
        payment_intent = stripe.PaymentIntent.create(
            amount=int(total_price * 100),  # cents
            currency='usd',
            metadata={
                'listing_id': listing_id,
                'guest_id': guest_id,
                'check_in': str(check_in),
                'check_out': str(check_out)
            }
        )

        # ACID transaction
        with db.begin():
            # Criar booking
            booking = Booking(
                listing_id=listing_id,
                guest_id=guest_id,
                check_in=check_in,
                check_out=check_out,
                num_guests=num_guests,
                num_nights=num_nights,
                total_price=total_price,
                status='pending',
                payment_intent_id=payment_intent.id
            )

            db.add(booking)
            db.flush()  # Get booking.id

            # Marcar datas como indisponíveis
            current_date = check_in

            while current_date < check_out:
                db.execute("""
                    UPDATE calendar
                    SET available = FALSE
                    WHERE listing_id = ? AND date = ?
                """, (listing_id, current_date))

                current_date += timedelta(days=1)

            db.commit()

        # Liberar lock
        redis_client.delete(lock_key)

        return {
            'booking_id': booking.id,
            'status': 'pending',
            'payment_client_secret': payment_intent.client_secret,
            'total_price': total_price
        }

    except IntegrityError:
        # Constraint violation (unique_listing_dates)
        db.rollback()
        redis_client.delete(lock_key)
        raise HTTPException(409, "Listing already booked for these dates")

    except Exception as e:
        db.rollback()
        redis_client.delete(lock_key)
        raise


@app.post("/bookings/{booking_id}/confirm")
async def confirm_booking(booking_id: int, payment_method_id: str):
    """
    Confirmar booking após pagamento

    Webhook do Stripe chama este endpoint
    """
    booking = get_booking(booking_id)

    if booking.status != 'pending':
        raise HTTPException(400, "Booking already processed")

    # Confirmar payment intent
    try:
        stripe.PaymentIntent.confirm(
            booking.payment_intent_id,
            payment_method=payment_method_id
        )

        # Atualizar status
        booking.status = 'confirmed'
        db.commit()

        # Notificar host
        send_notification(
            booking.listing.host_id,
            f"New booking for {booking.listing.title}!"
        )

        # Notificar guest
        send_notification(
            booking.guest_id,
            f"Booking confirmed! Check-in on {booking.check_in}"
        )

        return {'status': 'confirmed'}

    except stripe.error.CardError:
        # Payment falhou
        booking.status = 'cancelled'
        db.commit()

        # Liberar datas no calendário
        release_calendar(booking.listing_id, booking.check_in, booking.check_out)

        raise HTTPException(400, "Payment failed")
```

---

## 💰 Dynamic Pricing

```python
def calculate_dynamic_price(
    listing_id: int,
    date: date,
    base_price: float
) -> float:
    """
    Calcular preço dinâmico

    Fatores:
    - Demanda (ocupancy rate da região)
    - Sazonalidade (high season, holidays)
    - Eventos locais (concerts, conferences)
    - Day of week (weekend +20%)
    """
    multiplier = 1.0

    # Weekend
    if date.weekday() in [5, 6]:  # Sat, Sun
        multiplier *= 1.2

    # High season (summer)
    if date.month in [6, 7, 8]:
        multiplier *= 1.3

    # Holiday
    if is_holiday(date):
        multiplier *= 1.5

    # Demanda da região
    city = get_listing_city(listing_id)
    occupancy = get_occupancy_rate(city, date)

    if occupancy > 0.8:  # >80% ocupado
        multiplier *= 1.4
    elif occupancy > 0.6:
        multiplier *= 1.2

    # Eventos locais
    if has_events_nearby(listing_id, date):
        multiplier *= 1.5

    return round(base_price * multiplier, 2)
```

---

## 🎯 Perguntas da Entrevista

**Interviewer:** "Como prevenir double booking?"

**Você:** "Múltiplas camadas de proteção:

1. **Distributed lock (Redis)**: Adquirir lock antes de booking
2. **DB constraint**: `UNIQUE (listing_id, check_in, check_out)`
3. **Transaction isolation**: `SERIALIZABLE` para reads
4. **Optimistic locking**: Version field no booking

Se 2 users tentam booking simultâneo:
- Primeiro adquire lock → cria booking → comita
- Segundo espera lock → tenta criar → constraint violation → retry

Importante: Lock TTL curto (10s) para não bloquear indefinidamente"

---

**Interviewer:** "Como escalar search para 58k queries/segundo?"

**Você:** "ElasticSearch cluster:

1. **Sharding**: Particionar por cidade (NYC, SF, LA = shards separados)
2. **Replica factor 3**: Distribuir read load
3. **Caching**: Redis cache para searches populares (NYC, próximo weekend)
4. **Query optimization**:
   - Filters antes de geo query
   - Limit results (top 100)
   - Use filter context (cacheable)
5. **CDN**: Cache search results por localização"

---

## ✅ Checklist

- [ ] Geospatial search (ElasticSearch)
- [ ] Booking com ACID guarantees
- [ ] Disponibilidade (calendar)
- [ ] Payment integration (Stripe)
- [ ] Dynamic pricing
- [ ] Reviews e ratings
- [ ] Distributed locks para concorrência

---

**Booking system design fundamental! 🏠**
