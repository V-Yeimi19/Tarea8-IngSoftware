# Arquitectura del Sistema de Recompensas para Restaurantes

## 1. Características Clave
- **Event-Driven**: La comunicación entre servicios se realiza mediante eventos publicados en Apache Kafka
- **Desacoplamiento**: Los servicios no tienen dependencias directas entre sí
- **Escalabilidad**: Puede procesar múltiples transacciones concurrentemente
- **Resiliencia**: Incluye reintentos, DLQ (Dead Letter Queue) e idempotencia
- **Testing exhaustivo**: 98.9% cobertura de código con 150+ tests

---

## 2. Patrones Arquitectónicos

### 2.1 Arquitectura Hexagonal (Ports & Adapters)

Cada microservicio está organizado en tres capas:

```
┌─────────────────────────────────────────────────────────┐
│                 INFRASTRUCTURE LAYER                     │
│  FastAPI Routes │ SQLAlchemy │ Kafka Consumer/Producer   │
│  SMTP Client    │ HTTP Routers                           │
└─────────────────────────────────────────────────────────┘
                           △
                           │
┌─────────────────────────────────────────────────────────┐
│                 APPLICATION LAYER                        │
│  Use Cases (Orquestadores de lógica)                     │
│  - RegisterMealUseCase                                  │
│  - ProcessMealEventUseCase (con idempotencia)           │
│  - SendRewardNotificationUseCase                        │
└─────────────────────────────────────────────────────────┘
                           △
                           │
┌─────────────────────────────────────────────────────────┐
│                   DOMAIN LAYER                           │
│  Entidades │ Value Objects │ Puertos (Abstracciones)     │
│  Reglas de negocio puras (sin dependencias externas)    │
└─────────────────────────────────────────────────────────┘
```

#### Ventajas de esta arquitectura:
- **Independencia de frameworks**: El dominio no depende de FastAPI, SQLite ni Kafka
- **Testabilidad**: La lógica de negocio es fácil de testear sin mocks complejos
- **Flexibilidad**: Cambiar la implementación de Kafka o la BD no requiere cambios en el dominio
- **Mantenibilidad**: Cada capa tiene responsabilidades claras y limitadas

### 2.2 Event-Driven Architecture (EDA)

La comunicación entre microservicios ocurre mediante eventos publicados en Kafka:

```
restaurant_service
    │
    ├─ Publica: MealTransactionEvent
    │
    ▼
┌──────────────────────────┐
│  Kafka Topic             │
│  meal.transactions       │
│  (3 particiones)         │
└──────────────────────────┘
    │
    ├─ Consume: rewards_service
    │           (group_id: rewards-consumer-group)
    │
    ▼
rewards_service
    │
    ├─ Publica: RewardProcessedEvent
    │
    ▼
┌──────────────────────────┐
│  Kafka Topic             │
│  reward.processed        │
│  (3 particiones)         │
└──────────────────────────┘
    │
    ├─ Consume: notification_service
    │           (group_id: notification-consumer-group)
    │
    ▼
notification_service
    │
    └─ Envía email SMTP
```

#### Ventajas de EDA:
- **Desacoplamiento temporal**: Los servicios no necesitan estar up en el mismo momento
- **Escalabilidad**: Cada servicio escala independientemente según su carga
- **Resiliencia**: Los eventos se persisten en Kafka, garantizando entrega
- **Auditabilidad**: Cada evento es un registro de lo que sucedió en el sistema

### 2.3 CQRS Light (Separación de responsabilidades)

Aunque no es un CQRS completo, existe una separación clara:

- **Comando (Write)**: restaurant_service registra la transacción
- **Query (Read)**: rewards_service consulta la información de la transacción desde el evento
- **Evento (Read Model Update)**: notification_service lee el evento procesado para enviar email

---

## 4. Microservicios

### 4.1 Restaurant Service (Puerto 8000)

**Responsabilidad**: Registrar transacciones de clientes en restaurantes

#### Flujo de entrada
```
POST /api/v1/meals
│
├─ Validación de payload
├─ RegisterMealUseCase.execute()
│   ├─ Crear MealTransaction (dominio)
│   ├─ Guardar en repositorio
│   └─ Publicar MealTransactionEvent en Kafka
└─ Retornar HTTP 201 + transaction_id
```

#### Eventos producidos
- **Topic**: `meal.transactions`
- **Evento**: `MealTransactionEvent`
  ```json
  {
    "transaction_id": "550e8400-e29b-41d4-a716-446655440000",
    "card_number": "4532-XXXX-XXXX-1234",
    "restaurant_code": "REST-001",
    "amount": "150.00",
    "currency": "PEN",
    "timestamp": "2026-05-29T14:30:00Z"
  }
  ```

#### Endpoints
| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/api/v1/meals` | Registra una nueva transacción |
| `GET` | `/api/v1/meals/{transaction_id}` | Consulta una transacción por ID |
| `GET` | `/health` | Estado del servicio |

#### Dependencias externas
- **Kafka** (productor): Publica eventos
- **In-Memory Repository**: Almacena transacciones en memoria (stateless)

---

### 4.2 Rewards Service (Puerto 8001)

**Responsabilidad**: Consumir eventos de transacciones y calcular recompensas

#### Flujo de procesamiento
```
Kafka Consumer (meal.transactions)
│
├─ Recibe MealTransactionEvent
├─ ProcessMealEventUseCase.execute()
│   ├─ Validar idempotencia (¿ya procesada?)
│   ├─ Cargar CustomerAccount desde BD
│   ├─ RewardCalculator.calculate()
│   │   ├─ Determinar tier según monto
│   │   ├─ Calcular puntos: monto × factor_tier
│   │   ├─ Calcular cashback: monto × porcentaje_tier
│   │   └─ Retornar cálculo
│   ├─ Actualizar CustomerAccount
│   ├─ Guardar en SQLite
│   ├─ Publicar RewardProcessedEvent
│   └─ Commit manual del offset Kafka
└─ Si error: reintento exponencial → DLQ
```

#### Reglas de negocio (Tiers)

| Tier | Monto (PEN) | Puntos/PEN | Cashback | Lógica |
|------|-------------|-----------|----------|--------|
| **Standard** | 0 – 49.99 | 0.5 | 2.5% | Cliente nuevo o bajo gasto |
| **Silver** | 50 – 149.99 | 1.0 | 3.0% | Gasto medio |
| **Gold** | 150 – 299.99 | 1.5 | 4.0% | Gasto alto |
| **Platinum** | 300+ | 2.0 | 5.0% | Cliente VIP |

#### Eventos consumidos y producidos
| Dirección | Topic | Evento | Descripción |
|-----------|-------|--------|-------------|
| **↓ Consume** | `meal.transactions` | `MealTransactionEvent` | Transacción registrada |
| **↑ Produce** | `reward.processed` | `RewardProcessedEvent` | Recompensa calculada |
| **↑ Produce (fallos)** | `meal.transactions.dlq` | `DLQEvent` | Mensaje irrecuperable |

#### Evento producido
```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440001",
  "transaction_id": "550e8400-e29b-41d4-a716-446655440000",
  "card_number": "4532-XXXX-XXXX-1234",
  "customer_email": "cliente@ejemplo.com",
  "points_earned": 300,
  "cashback_amount": "6.00",
  "total_points_balance": 450,
  "total_cashback_balance": "9.00",
  "restaurant_code": "REST-001",
  "processed_at": "2026-05-29T14:31:00Z"
}
```

#### Dependencias externas
- **Kafka** (consumidor + productor): Lee transacciones, publica recompensas
- **SQLite**: Persiste CustomerAccount e histórico
- **SQLAlchemy ORM**: Manejo de datos

#### Características de resiliencia
- **Idempotencia**: Usa `transaction_id` como clave única. Si llega duplicado, no lo procesa.
- **Reintentos**: 3 intentos con backoff exponencial (500ms → 1s → 2s)
- **DLQ**: Mensajes fallidos se envían a `meal.transactions.dlq`
- **Manual offset commit**: Solo confirma después de procesar exitosamente

---

### 4.3 Notification Service (Puerto 8002)

**Responsabilidad**: Enviar notificaciones por correo a clientes tras recompensa

#### Flujo de envío
```
Kafka Consumer (reward.processed)
│
├─ Recibe RewardProcessedEvent
├─ SendRewardNotificationUseCase.execute()
│   ├─ Crear NotificationRequest
│   ├─ SMTPEmailSender.send()
│   │   ├─ Conectar a servidor SMTP
│   │   ├─ Construir email HTML
│   │   ├─ Enviar con STARTTLS
│   │   └─ Cerrar conexión
│   └─ Commit manual del offset Kafka
└─ Si error: reintento exponencial → DLQ
```

#### Email template (HTML)
```html
Asunto: ¡Recompensas acreditadas!

Estimado cliente,
Se han acreditado tus recompensas:
- Puntos: 300
- Cashback: PEN 6.00
- Saldo total: 450 puntos

Gracias por tu preferencia.
```

#### Eventos consumidos
| Topic | Evento | Descripción |
|-------|--------|-------------|
| `reward.processed` | `RewardProcessedEvent` | Recompensa calculada |

#### Dependencias externas
- **Kafka** (consumidor): Lee eventos de recompensas
- **SMTP**: Envía correos (Gmail STARTTLS)

#### Características de resiliencia
- **Reintentos**: 3 intentos con backoff exponencial
- **DLQ**: Emails que no se pueden enviar se persisten
- **Manual offset commit**: Solo confirma después de enviar

---

## 5. Flujo de Datos y Comunicación

### 5.1 Flujo Completo End-to-End

```
┌────────────────────────────────────────────────────────────────────────┐
│                         FLUJO COMPLETO DEL SISTEMA                     │
└────────────────────────────────────────────────────────────────────────┘

                        Cliente HTTP
                             │
                             │ POST /api/v1/meals
                             │
                             ▼
            ┌─────────────────────────────────────┐
            │  RESTAURANT_SERVICE :8000           │
            │  ├─ Validar payload                 │
            │  ├─ Crear MealTransaction           │
            │  └─ Guardar + Publicar evento       │
            └─────────────────────────────────────┘
                             │
                             │ MealTransactionEvent
                             │ {"transaction_id": "...", "amount": 150.00, ...}
                             │
                             ▼
            ┌─────────────────────────────────────┐
            │     KAFKA BROKER :9092              │
            │     Topic: meal.transactions         │
            │     (3 particiones)                  │
            └─────────────────────────────────────┘
                             │
                             │ Partition assignment
                             │ (round-robin)
                             │
                             ▼
            ┌─────────────────────────────────────┐
            │  REWARDS_SERVICE :8001              │
            │  Consumer Group: rewards-group      │
            │  ├─ Recibir evento                  │
            │  ├─ Verificar idempotencia          │
            │  ├─ Calcular recompensas            │
            │  ├─ Actualizar BD SQLite            │
            │  └─ Publicar RewardProcessedEvent   │
            └─────────────────────────────────────┘
                             │
                             │ RewardProcessedEvent
                             │ {"points_earned": 300, "cashback": "6.00", ...}
                             │
                             ▼
            ┌─────────────────────────────────────┐
            │     KAFKA BROKER :9092              │
            │     Topic: reward.processed          │
            │     (3 particiones)                  │
            └─────────────────────────────────────┘
                             │
                             │ Partition assignment
                             │ (round-robin)
                             │
                             ▼
            ┌─────────────────────────────────────┐
            │ NOTIFICATION_SERVICE :8002          │
            │ Consumer Group: notification-group  │
            │ ├─ Recibir evento                   │
            │ ├─ Construir email HTML             │
            │ ├─ Enviar via SMTP (Gmail)          │
            │ └─ Confirmar offset                 │
            └─────────────────────────────────────┘
                             │
                             │ Email SMTP
                             │ To: cliente@ejemplo.com
                             │ Subject: ¡Recompensas acreditadas!
                             │
                             ▼
                        Cliente Email
```

#### Garantías de entrega

- **At-least-once delivery**: Los mensajes se procesan al menos una vez
- **Idempotencia**: Para garantizar exactamente-una-vez (exactly-once), usamos:
  - `transaction_id` como clave única en rewards_service
  - Chequeo antes de procesar: `if transaction_id already exists → skip`

---

## 6. Patrones de Resiliencia

### 6.1 Reintentos con Backoff Exponencial

Cada servicio implementa reintentos para fallos transitorios:

```
Intento 1: Esperar 500ms
├─ Éxito → Continuar
└─ Fallo → Intento 2

Intento 2: Esperar 1s
├─ Éxito → Continuar
└─ Fallo → Intento 3

Intento 3: Esperar 2s
├─ Éxito → Continuar
└─ Fallo → Enviar a DLQ (Dead Letter Queue)
```
### 6.2 Dead Letter Queue (DLQ)

Mensajes que fallan después de agotar reintentos se envían a un tópico especial:

```
meal.transactions.dlq
├─ original_topic: "meal.transactions"
├─ original_message: { ... }
├─ error: "SMTP connection timeout"
├─ retry_count: 3
└─ failed_at: "2026-05-29T14:35:00Z"
```

**Ventajas**:
- No bloquea el procesamiento de otros mensajes
- Permite análisis posterior de fallos
- Posibilidad de reintento manual

### 6.3 Idempotencia

La idempotencia evita procesar el mismo evento dos veces:

```
IF transaction_id ya existe en BD
  THEN: Skip (ya procesado)
  ELSE: Procesar normalmente
```

---

## 7. Decisiones Arquitectónicas

### 7.1 ¿Por qué Arquitectura Hexagonal?

| Aspecto | Hexagonal | Alternativas |
|--------|-----------|--------------|
| **Testabilidad** | ✓ Excelente | Monolito (difícil) |
| **Flexibilidad** | ✓ Fácil cambiar adapters | Layered (menos) |
| **Escalabilidad** | ✓ Por capa | MVC (acoplado) |
| **Dependencias** | ✓ Inversión clara | CRUD (acopladas) |

**Decisión**: Hexagonal permite cambiar Kafka por RabbitMQ o SQLite por PostgreSQL sin tocar la lógica de dominio.

### 7.2 ¿Por qué Event-Driven?

**Problemas con comunicación síncrona REST**:
- Si rewards_service cae, restaurant_service falla
- Acoplamiento temporal (ambos deben estar up)
- Escalabilidad limitada por velocidad de procesamiento

**Ventajas de EDA con Kafka**:
- Desacoplamiento temporal: restaurant_service publica y continúa
- Persistencia: Si rewards_service cae, Kafka retiene los eventos
- Escalabilidad: rewards_service puede procesar a su velocidad
- Auditabilidad: Cada evento es un registro histórico

```
EDA (Actual):              REST (Alternativa):
POST → 201 ✓             POST → Wait → 500 ✗
       │                        │
       └─ Kafka              └─ Falla del otro
```

### 7.3 ¿Por qué 3 Particiones en Kafka?

```
Partición 0: Mensajes con transaction_id terminados en 0, 3, 6, 9...
Partición 1: Mensajes con transaction_id terminados en 1, 4, 7...
Partición 2: Mensajes con transaction_id terminados en 2, 5, 8...
```

**Ventajas**:
- Permite 3 consumers en paralelo
- Escalabilidad horizontal: Si aumenta carga, agregar particiones
- Order por partition key (transaction_id) garantizado

### 7.4 ¿Por qué SQLite en rewards_service?

| BD | Pros | Contras |
|----|------|---------|
| **SQLite** | Desarrollo rápido, cero setup, cobertura fácil | Single file, no escalable |
| **PostgreSQL** | Escalable, transacciones ACID | Setup, infraestructura |
| **MongoDB** | Schema-flexible | Replicación compleja |

**Decisión**: SQLite es suficiente para una tarea académica. En producción sería PostgreSQL.

### 7.5 ¿Por qué SMTP, no API de terceros?

| Opción | Pros | Contras |
|--------|------|---------|
| **SMTP Gmail** | Bajo costo, simple | Rate limiting, no tracking |
| **SendGrid API** | Tracking, reliability | Costo, dependencia |
| **AWS SES** | Escalable | Setup AWS, costo |

**Decisión**: SMTP es suficiente para demostración. SendGrid sería mejor en producción.

---

## 8. Conclusión

Esta arquitectura implementa **patrones empresariales probados** (Hexagonal + EDA) garantizando:

1. **Escalabilidad**: Servicios independientes que escalan según demanda
2. **Resiliencia**: Reintentos, DLQ, idempotencia, manual commit
3. **Testabilidad**: 98.9% cobertura con tests unitarios, integración y E2E
4. **Mantenibilidad**: Capas claras, responsabilidades bien definidas
5. **Auditabilidad**: Cada evento es un registro de lo que sucedió

El sistema es apto para:
- Entender patrones modernos de arquitectura
- Escalar a millones de transacciones con agregación de particiones Kafka
- Servir como referencia para proyectos reales de software empresarial
