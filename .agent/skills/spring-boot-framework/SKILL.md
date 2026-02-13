---
name: spring-boot-framework
description: Spring Boot 3.2+ standards — layered architecture, JPA/Hibernate, Spring Security, Kafka, Flyway, caching, Testcontainers
---

# Spring Boot Framework

See `java-standards` skill for Java language rules.

## Version
- **Spring Boot**: 3.2+ | **Java**: 21

---

## Layered Architecture

```
presentation/   → Controllers, exception handlers, DTOs
application/    → Use cases, application services, mappers
domain/         → Entities, value objects, repositories (interfaces)
infrastructure/ → JPA repos, Kafka, external APIs, config
```

**Rule: Dependencies only flow inward (presentation → application → domain ← infrastructure).**

---

## REST Controller Pattern

```java
@RestController
@RequestMapping("/api/v1/users")
@RequiredArgsConstructor
@Validated
public class UserController {

    private final UserService userService;

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public UserResponse create(@RequestBody @Valid CreateUserRequest request) {
        return userService.create(request);
    }

    @GetMapping
    public Page<UserResponse> list(
        @RequestParam(defaultValue = "0") int page,
        @RequestParam(defaultValue = "20") int size,
        @RequestParam(defaultValue = "createdAt,desc") String sort
    ) {
        return userService.list(PageRequest.of(page, size, Sort.by(sort)));
    }
}
```

---

## Spring Security (JWT + OAuth2)

```java
@Configuration
@EnableWebSecurity
public class SecurityConfig {
    @Bean
    SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        return http
            .csrf(AbstractHttpConfigurer::disable)
            .sessionManagement(s -> s.sessionCreationPolicy(STATELESS))
            .authorizeHttpRequests(a -> a
                .requestMatchers("/api/v1/auth/**").permitAll()
                .requestMatchers("/api/v1/admin/**").hasRole("ADMIN")
                .anyRequest().authenticated()
            )
            .oauth2ResourceServer(o -> o.jwt(Customizer.withDefaults()))
            .build();
    }
}
```

---

## JPA Best Practices

- Use **`@Transactional`** at service layer, not controller.
- Prefer **projections** over full entity loads for read queries.
- Use **`@EntityGraph`** to prevent N+1 queries.
- Use **`@Version`** for optimistic locking.
- **Never expose entities in API responses** — use DTOs + MapStruct.

---

## Kafka Integration

```java
@Service @RequiredArgsConstructor
public class EventPublisher {
    private final KafkaTemplate<String, Object> kafka;

    @Transactional
    public void publishUserCreated(User user) {
        kafka.send("user.events", user.getId().toString(),
            new UserCreatedEvent(user.getId(), user.getEmail(), Instant.now()));
    }
}

@KafkaListener(topics = "user.events", groupId = "notification-service")
public void handleUserCreated(UserCreatedEvent event) {
    notificationService.sendWelcome(event.email());
}
```

---

## Configuration

```yaml
# application.yml
spring:
  datasource:
    url: jdbc:postgresql://localhost:5432/stratos
    hikari:
      maximum-pool-size: 20
  jpa:
    open-in-view: false   # CRITICAL: disable OSIV
    hibernate.ddl-auto: validate
  flyway:
    enabled: true
    locations: classpath:db/migration

management:
  endpoints.web.exposure.include: health,info,prometheus
  metrics.tags.application: stratos
```

---

## Key Libraries

| Library | Purpose |
|---|---|
| Spring Boot Starter Web | REST APIs |
| Spring Data JPA | Repository pattern |
| Spring Security | Auth + authz |
| Spring Kafka | Event messaging |
| Resilience4j | Circuit breaker, retry |
| Flyway | Database migrations |
| MapStruct | DTO mapping |
| Testcontainers | Integration testing |
| Caffeine | Local caching |
| Micrometer | Metrics / Prometheus |
