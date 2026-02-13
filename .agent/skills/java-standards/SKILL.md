---
name: java-standards
description: Java 21 LTS standards — modern features, Spring Boot patterns, testing with JUnit 5, build tools, and enterprise architecture
---

# Java Standards

## Version & Build
- **Java**: 21 LTS
- **Build**: Maven or Gradle (Kotlin DSL preferred)
- **Style**: Google Java Format or Checkstyle

---

## Project Structure (Maven)

```
src/
├── main/
│   ├── java/com/company/project/
│   │   ├── domain/
│   │   │   ├── model/          # Entities, Value Objects, Aggregates
│   │   │   ├── repository/     # Repository interfaces
│   │   │   └── service/        # Domain services
│   │   ├── application/
│   │   │   ├── dto/            # Request/Response DTOs
│   │   │   ├── mapper/         # Entity ↔ DTO mappers
│   │   │   └── usecase/        # Application services
│   │   ├── infrastructure/
│   │   │   ├── persistence/    # JPA repository implementations
│   │   │   ├── messaging/      # Kafka producers/consumers
│   │   │   └── config/         # Spring configurations
│   │   └── presentation/
│   │       ├── controller/     # REST controllers
│   │       └── exception/      # Exception handlers
│   └── resources/
│       ├── application.yml
│       ├── application-dev.yml
│       ├── application-prod.yml
│       └── db/migration/       # Flyway migrations
└── test/
    ├── java/
    │   ├── unit/
    │   ├── integration/
    │   └── e2e/
    └── resources/
        └── application-test.yml
```

---

## Naming Conventions

| Construct | Convention | Example |
|---|---|---|
| Packages | `lowercase.with.dots` | `com.company.project.domain` |
| Classes | `PascalCase` | `UserService` |
| Interfaces | `PascalCase` (no `I` prefix) | `UserRepository` |
| Methods | `camelCase` | `getUserById()` |
| Variables | `camelCase` | `maxRetryCount` |
| Constants | `UPPER_SNAKE_CASE` | `MAX_POOL_SIZE` |
| Type params | Single uppercase | `T`, `E`, `K`, `V` |

---

## Modern Java Features (21+)

### Records (Immutable DTOs)
```java
public record CreateUserRequest(
    @NotBlank @Size(min = 2, max = 100) String name,
    @NotBlank @Email String email,
    @NotBlank @Size(min = 8) String password
) {
    // Compact constructor for validation
    public CreateUserRequest {
        Objects.requireNonNull(name, "Name required");
        Objects.requireNonNull(email, "Email required");
    }
}
```

### Sealed Interfaces
```java
public sealed interface Shape permits Circle, Rectangle, Triangle {
    double area();
}

public record Circle(double radius) implements Shape {
    public double area() { return Math.PI * radius * radius; }
}

public record Rectangle(double width, double height) implements Shape {
    public double area() { return width * height; }
}
```

### Pattern Matching (switch)
```java
public String describe(Shape shape) {
    return switch (shape) {
        case Circle c when c.radius() > 100 -> "Large circle: r=" + c.radius();
        case Circle c -> "Circle: r=" + c.radius();
        case Rectangle r -> "Rectangle: %sx%s".formatted(r.width(), r.height());
        case Triangle t -> "Triangle: base=" + t.base();
    };
}
```

### Virtual Threads (Project Loom)
```java
// For I/O-bound workloads — use instead of thread pools
try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
    var futures = urls.stream()
        .map(url -> executor.submit(() -> fetchUrl(url)))
        .toList();

    return futures.stream()
        .map(f -> { try { return f.get(); } catch (Exception e) { throw new RuntimeException(e); } })
        .toList();
}
```

### Text Blocks
```java
String sql = """
    SELECT u.id, u.name, o.total
    FROM users u
    JOIN orders o ON u.id = o.user_id
    WHERE u.active = true
    AND o.created_at >= :since
    """;
```

---

## Error Handling

### Exception Hierarchy
```java
public class AppException extends RuntimeException {
    private final String code;
    private final int statusCode;

    public AppException(String message, String code, int statusCode) {
        super(message);
        this.code = code;
        this.statusCode = statusCode;
    }

    public AppException(String message, String code, int statusCode, Throwable cause) {
        super(message, cause);
        this.code = code;
        this.statusCode = statusCode;
    }
}

public class NotFoundException extends AppException {
    public NotFoundException(String resource, Object id) {
        super("%s not found: %s".formatted(resource, id), "NOT_FOUND", 404);
    }
}

public class ConflictException extends AppException {
    public ConflictException(String message) {
        super(message, "CONFLICT", 409);
    }
}
```

### Global Exception Handler (Spring)
```java
@RestControllerAdvice
@Slf4j
public class GlobalExceptionHandler {

    @ExceptionHandler(NotFoundException.class)
    public ResponseEntity<ErrorResponse> handleNotFound(NotFoundException ex) {
        log.warn("Resource not found: {}", ex.getMessage());
        return ResponseEntity.status(404)
            .body(new ErrorResponse(ex.getCode(), ex.getMessage(), Instant.now()));
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ErrorResponse> handleValidation(MethodArgumentNotValidException ex) {
        var errors = ex.getBindingResult().getFieldErrors().stream()
            .collect(Collectors.toMap(
                FieldError::getField,
                e -> Objects.requireNonNullElse(e.getDefaultMessage(), "Invalid")
            ));
        return ResponseEntity.badRequest()
            .body(new ErrorResponse("VALIDATION_ERROR", "Validation failed", errors, Instant.now()));
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ErrorResponse> handleUnexpected(Exception ex) {
        log.error("Unexpected error", ex);
        return ResponseEntity.status(500)
            .body(new ErrorResponse("INTERNAL_ERROR", "An unexpected error occurred", Instant.now()));
    }
}
```

### Rules
- **Never catch `Throwable`** — only `Exception` and its subtypes.
- **Never swallow** — always log or propagate.
- **Use try-with-resources** for all `AutoCloseable`.
- **Chain exceptions** with `cause` parameter.

---

## Testing with JUnit 5

### Unit Tests
```java
@ExtendWith(MockitoExtension.class)
class UserServiceTest {

    @Mock UserRepository userRepository;
    @Mock PasswordEncoder passwordEncoder;
    @InjectMocks UserService userService;

    @Test
    @DisplayName("should create user with valid data")
    void shouldCreateUserWithValidData() {
        // Given
        var request = new CreateUserRequest("John", "john@test.com", "password123");
        when(userRepository.existsByEmail("john@test.com")).thenReturn(false);
        when(passwordEncoder.encode("password123")).thenReturn("hashed");
        when(userRepository.save(any())).thenAnswer(inv -> {
            User u = inv.getArgument(0);
            return u.toBuilder().id(1L).build();
        });

        // When
        var result = userService.createUser(request);

        // Then
        assertThat(result.getId()).isEqualTo(1L);
        assertThat(result.getName()).isEqualTo("John");
        verify(userRepository).save(argThat(u -> u.getName().equals("John")));
    }

    @ParameterizedTest
    @ValueSource(strings = {"", "   ", "x"})
    @DisplayName("should reject invalid names")
    void shouldRejectInvalidNames(String name) {
        var request = new CreateUserRequest(name, "test@test.com", "password123");
        assertThatThrownBy(() -> userService.createUser(request))
            .isInstanceOf(ValidationException.class);
    }
}
```

### Integration Tests with Testcontainers
```java
@Testcontainers
@SpringBootTest
@AutoConfigureTestDatabase(replace = Replace.NONE)
class UserRepositoryIT {

    @Container
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16-alpine")
        .withDatabaseName("testdb");

    @DynamicPropertySource
    static void configure(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", postgres::getJdbcUrl);
        registry.add("spring.datasource.username", postgres::getUsername);
        registry.add("spring.datasource.password", postgres::getPassword);
    }

    @Autowired UserRepository repo;

    @Test
    void shouldPersistAndRetrieveUser() {
        var user = User.builder().name("John").email("john@test.com").build();
        var saved = repo.save(user);

        assertThat(repo.findById(saved.getId()))
            .isPresent()
            .get()
            .extracting(User::getEmail)
            .isEqualTo("john@test.com");
    }
}
```

### Assertions: AssertJ
```java
// Fluent, readable assertions
assertThat(users)
    .hasSize(3)
    .extracting(User::getName)
    .containsExactly("Alice", "Bob", "Charlie");

assertThat(result)
    .isNotNull()
    .satisfies(r -> {
        assertThat(r.status()).isEqualTo("SUCCESS");
        assertThat(r.data()).isNotEmpty();
    });
```

---

## Build Configuration

### Maven (pom.xml essentials)
```xml
<properties>
    <java.version>21</java.version>
    <spring-boot.version>3.3.0</spring-boot.version>
</properties>

<dependencies>
    <!-- Spring Boot Starters -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-data-jpa</artifactId>
    </dependency>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-validation</artifactId>
    </dependency>

    <!-- Lombok -->
    <dependency>
        <groupId>org.projectlombok</groupId>
        <artifactId>lombok</artifactId>
        <scope>provided</scope>
    </dependency>

    <!-- Testing -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-test</artifactId>
        <scope>test</scope>
    </dependency>
    <dependency>
        <groupId>org.testcontainers</groupId>
        <artifactId>postgresql</artifactId>
        <scope>test</scope>
    </dependency>
</dependencies>
```

### Gradle (Kotlin DSL)
```kotlin
plugins {
    java
    id("org.springframework.boot") version "3.3.0"
    id("io.spring.dependency-management") version "1.1.5"
    jacoco
}

java { sourceCompatibility = JavaVersion.VERSION_21 }

tasks.test {
    useJUnitPlatform()
    finalizedBy(tasks.jacocoTestReport)
}

tasks.jacocoTestReport {
    reports { xml.required.set(true); html.required.set(true) }
}
```

---

## Documentation (Javadoc)

Required for all public classes, interfaces, and methods:
```java
/**
 * Service for user lifecycle management.
 *
 * <p>Handles creation, retrieval, update, and deactivation of users.
 * All mutations are transactional and publish domain events.
 *
 * @author STRATOS Team
 * @since 1.0.0
 */
@Service
@RequiredArgsConstructor
public class UserService {

    /**
     * Creates a new user account.
     *
     * @param request validated user creation request
     * @return the created user with generated ID
     * @throws ConflictException if email is already registered
     */
    @Transactional
    public User createUser(CreateUserRequest request) { ... }
}
```

---

## Key Libraries

| Domain | Library | Notes |
|---|---|---|
| Web | Spring Boot 3.3+ | Web, Security, Data JPA |
| ORM | Hibernate 6.x | Via Spring Data JPA |
| Migrations | Flyway | SQL-based, versioned |
| Validation | Jakarta Bean Validation | Annotations + custom |
| JSON | Jackson | Auto-configured by Spring |
| Testing | JUnit 5 + AssertJ + Mockito | Standard stack |
| Integration testing | Testcontainers | Real databases in Docker |
| Logging | SLF4J + Logback | Structured JSON in prod |
| Metrics | Micrometer + Prometheus | Via Spring Boot Actuator |
| Messaging | Spring Kafka | Event-driven |
| Caching | Spring Cache + Redis | Caffeine for local cache |
| Security | Spring Security + OAuth2 | JWT resource server |
| Resilience | Resilience4j | Circuit breaker, retry |
| Mapping | MapStruct | Compile-time mappers |
