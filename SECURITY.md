# 🔐 Consideraciones de Seguridad — Pokédex API

Este documento describe las medidas de seguridad implementadas en la Pokédex API y justifica las decisiones adoptadas en relación con autenticación, protección de datos, mitigación de ataques y mejores prácticas.

---

## 1. Autenticación

### ✔ JWT (JSON Web Tokens)
La API utiliza **JWT** firmados con `HS256`.  
Cada token incluye los siguientes *claims*:

- `sub`: nombre de usuario (identidad principal)
- `user_id`: identificador interno del usuario
- `iat`: fecha/hora de emisión
- `exp`: fecha/hora de expiración
- `type`: `access` o `refresh`

### ✔ Duración de tokens
- Access token → **24 horas**
- Refresh token → **7 días**

### ✔ Justificación
- Los access tokens tienen duración corta para limitar el riesgo si son robados.
- Los refresh tokens permiten renovar la sesión sin pedir credenciales cada vez.

---

## 2. Contraseñas

### ✔ Almacenamiento seguro
Las contraseñas **NO se almacenan en texto plano**.  
Se emplea:

- `passlib[bcrypt]`
- Salt automático
- Hash resistente a ataques de fuerza bruta

### ✔ Política de contraseñas
Validación obligatoria en el registro:

- mínimo **8 caracteres**
- al menos **1 mayúscula**
- al menos **1 número**

**Justificación:**  
Evita contraseñas débiles y reduce riesgo de ataques de diccionario.

---

## 3. Rate Limiting

### ✔ Implementado con slowapi
La API aplica límites basados en IP para evitar abuso:

| Endpoint | Límite | Justificación |
|---------|--------|---------------|
| `/auth/register` | 5/hora | evitar bots creando cuentas |
| `/auth/login` | 10/min | evitar fuerza bruta |
| `/pokemon/search` | 30/min | proteger PokeAPI (servicio externo) |
| Rutas autenticadas | 60/min | proteger recursos del backend |

### ✔ Modo testing
Durante ejecución con pytest:

- El rate limiting se **desactiva automáticamente** para evitar falsos positivos en tests.

---

## 4. CORS

Configuración recomendada:

- Dominios permitidos:  
  `http://localhost:3000`, `http://localhost:5173`
- Métodos permitidos: `GET, POST, PUT, PATCH, DELETE`
- Headers permitidos: `Authorization, Content-Type`

### ✔ Justificación
CORS evita que sitios no autorizados consuman la API desde el navegador.

---

## 5. Variables de Entorno

Variables sensibles almacenadas en `.env`:

- `SECRET_KEY`
- `DATABASE_URL`
- `CORS_ORIGINS`
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `REFRESH_TOKEN_EXPIRE_MINUTES`

### ✔ Protección
- `.env` está excluido por `.gitignore`
- En producción deben cargarse mediante variables del sistema o secret managers

---

## 6. Manejo de errores

La API devuelve errores controlados y sin revelar información interna:

- `401` → credenciales inválidas  
- `403` → recurso no autorizado  
- `404` → pokemon o entrada inexistente  
- `409` → duplicados  
- `422` → validación Pydantic  
- `500` → errores no controlados

### ✔ PokeAPI
Errores externos se traducen a respuestas limpias:

- Timeout → `504`
- Error de conexión → `503`
- Estado HTTP → propagado como excepción controlada

---

## 7. Logging

La API registra:

- Método y URL de cada request
- Código de estado
- Duración de ejecución
- Errores de autenticación
- Fallos de validación
- Llamadas a PokeAPI
- Rate limit excedido

**Justificación:**  
Permite auditoría, debugging y detección temprana de abusos.

---

## 8. Protección frente a vulnerabilidades comunes (OWASP API Top 10)

### ✔ A01 Broken Access Control
- Validación del `owner_id` al acceder a Pokédex y equipos  
- JWT obligatorio en endpoints privados  
- No se permite modificar recursos de otros usuarios

### ✔ A02 Cryptographic Failures
- Hash seguro bcrypt  
- JWT firmado con clave secreta  
- Recomendación de usar HTTPS en producción

### ✔ A03 Injection
- Uso de SQLModel/SQLAlchemy → consultas parametrizadas  
- Sanitización de inputs por Pydantic

### ✔ A05 Security Misconfiguration
- CORS restringido  
- Rate limiter activo  
- Logging de seguridad  
- Errores no detallan el backend

### ✔ A07 Authentication Failures
- Política estricta de contraseñas  
- Límite de intentos de login  
- Refresh token seguro  
- Validación de `type: access|refresh`

### ✔ A08 Integrity & Dependency Failures
- Dependencias fijadas en `requirements.txt`  
- Uso de versiones actualizadas  
- Validación de tiempo de vida del token

---

## 9. Recomendaciones para Producción

- Usar HTTPS obligatorio (TLS)
- Mover SECRET_KEY a un secret manager
- Configurar logs en un servicio centralizado
- Deshabilitar modo debug
- Añadir rotación de tokens y revocación manual

---

## 10. Resumen

La API implementa:

- Autenticación robusta  
- Seguridad basada en estándares  
- Protección contra abuso  
- Gestión segura de sesiones  
- Logging profesional  
- Validación exhaustiva de datos  

Cumpliendo con los criterios de evaluación del módulo de Seguridad de APIs.

