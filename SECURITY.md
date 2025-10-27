# Consideraciones de Seguridad

## Autenticación
- **JWT** firmado con `HS256`.
- El token incluye: `sub` (username), `user_id` (int), `iat` (emitido), `exp` (caducidad).
- **Política de expiración**: `JWT_EXPIRES_MIN` (por defecto 1440 = 24h). Recomendación prod: 60–120 min.

## Contraseñas
- **Hash** con `passlib[bcrypt]`, sin almacenar en claro.
- **Política**: mínimo 8 caracteres, 1 mayúscula y 1 número (validada en el registro).

## Rate Limiting
- Implementado con **slowapi** por IP.
- **Límites sugeridos por endpoint**:
  - `/api/v1/auth/*`: 10 req/min (mitigar fuerza bruta).
  - `/api/v1/pokemon/search`: 30 req/min (proteger PokeAPI).
  - `/api/v1/pokemon/{id_or_name}`: 60 req/min.
  - `/api/v1/pokedex/*`: 60 req/min por usuario.
- **Justificación**: prevenir abuso, scraping y DoS; proteger terceros.

## CORS
- **Orígenes permitidos** configurables en `CORS_ORIGINS` (p. ej., `http://localhost:3000`, `http://localhost:5173`).
- **Por qué es necesario**: limitar quién puede consumir la API desde el navegador; defensa básica contra usos no autorizados.

## Variables de Entorno
- **Sensible**: `JWT_SECRET`, `DATABASE_URL`, `CORS_ORIGINS`.
- **Protección**:
  - Mantener en `.env` (excluido con `.gitignore`).
  - En producción, usar secret manager/variables del sistema y rotación periódica.

## Vulnerabilidades Conocidas
- **OWASP Top 10 consideradas**:
  - A01 Broken Access Control: dependencias de auth en rutas protegidas, `owner_id`.
  - A02 Cryptographic Failures: JWT con expiración, bcrypt, TLS recomendado.
  - A03 Injection: SQLModel/SQLAlchemy con consultas parametrizadas.
  - A05 Security Misconfiguration: CORS restringido, errores genéricos, logging sin secretos.
  - A07 Identification & Authentication Failures: política de contraseñas, límites en `/auth`, verificación JWT.
  - A08 Software & Data Integrity Failures: dependencias fijadas en `requirements.txt`.
- **Mitigaciones**: validación de inputs, manejo controlado de errores de upstream, rate limiting, CORS, logging de acceso/errores.
