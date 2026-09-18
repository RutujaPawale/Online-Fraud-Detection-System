# API Service (`api-service`)

A Java 21+ and Spring Boot 3.3 microservice that orchestrates transaction ingestion, calls the Python `ml-service` to retrieve real-time fraud probability scores, enforces business decision thresholds (`APPROVE`, `FLAGGED`, `BLOCK`), manages human-in-the-loop analyst reviews, and persists transaction audits to PostgreSQL.

---

## Architecture Role & Responsibilities
- **Transaction Ingestion**: Exposes `POST /api/v1/transactions` to receive incoming checkouts.
- **ML Integration**: Forwards IEEE-CIS transaction features to `ml-service` (`POST /api/v1/score`).
- **Threshold Decision Engine**:
  - Score `< 0.30` $\rightarrow$ `APPROVE`
  - Score `[0.30 - 0.75)` $\rightarrow$ `FLAGGED` (auto-creates a review case in `review_cases`)
  - Score `\ge 0.75` $\rightarrow$ `BLOCK`
- **Review Workflow**: Exposes `PATCH /api/v1/reviews/transactions/{id}` for fraud analysts to resolve flagged cases with `CONFIRMED_FRAUD` or `FALSE_POSITIVE`.
- **Metrics Aggregation**: Exposes `GET /api/v1/metrics` proxying ML validation metrics to the frontend dashboard.
- **PostgreSQL Persistence**: Stores relational records using Spring Data JPA.

---

## Directory Structure
```
api-service/
├── src/
│   ├── main/
│   │   ├── java/com/fraud/detection/
│   │   │   ├── config/          # CORS & RestClient configuration
│   │   │   ├── controller/      # REST API Controllers
│   │   │   ├── dto/             # Inbound & Outbound Data Transfer Objects
│   │   │   ├── entity/          # JPA Hibernate Entities & Enums
│   │   │   ├── repository/      # Spring Data JPA Repositories
│   │   │   ├── service/         # Business logic & ML client
│   │   │   └── FraudDetectionApplication.java
│   │   └── resources/
│   │       ├── application.yml
│   │       └── db/migration/V1__init_schema.sql
├── Dockerfile
├── pom.xml
└── README.md
```

---

## Configuration & Environment Variables

| Variable | Default Value | Description |
|---|---|---|
| `SERVER_PORT` | `8080` | HTTP port |
| `DB_HOST` | `localhost` | PostgreSQL host |
| `DB_PORT` | `5432` | PostgreSQL port |
| `DB_NAME` | `fraud_detection_db` | Database name |
| `DB_USER` | `postgres` | Database username |
| `DB_PASSWORD` | `postgres` | Database password |
| `ML_SERVICE_URL` | `http://localhost:8000` | ML Service base endpoint |

---

## Local Development

### 1. Requirements
- JDK 21 or JDK 24
- PostgreSQL 15+ running locally (or via Docker Compose)

### 2. Build & Run
```bash
# Clean & package
mvn clean package -DskipTests

# Run Spring Boot application
java -jar target/api-service-0.1.0-SNAPSHOT.jar
```
Or run directly via your IDE (IntelliJ IDEA, Eclipse, VS Code) by launching `FraudDetectionApplication.java`.
