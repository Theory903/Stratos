FROM eclipse-temurin:21-jdk-alpine AS builder
WORKDIR /app
COPY engines/java/ .
RUN ./mvnw -B package -DskipTests 2>/dev/null || mvn -B package -DskipTests

FROM eclipse-temurin:21-jre-alpine
WORKDIR /app
COPY --from=builder /app/target/*.jar app.jar
EXPOSE 8002
CMD ["java", "-jar", "app.jar"]
