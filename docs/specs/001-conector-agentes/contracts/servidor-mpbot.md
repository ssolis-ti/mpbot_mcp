# Contrato: servidor MCP de mpbot (dependencia externa)

Lo que este conector puede dar por sentado del servidor, y lo que no. Refleja
la sección "Contrato con el servidor mpbot" de la constitución.

**Este repo no modifica el servidor.** Si algo de acá exige un cambio allá,
se abre feature en `mpbot/` con su propio ciclo Spec Kit.

## Conexión

| Aspecto | Valor |
|---|---|
| Endpoint | `https://app.mpbot.cl/mcp/` (sobreescribible para desarrollo) |
| Transporte | MCP Streamable HTTP, *stateless*, respuesta JSON |
| Autenticación | `Authorization: Bearer mpb_…` (equivalente: `X-API-Key`) |
| Plan requerido | `api_datos` (Empresa) |
| Cuota | Mensual por key; **cada request HTTP cuenta 1, incluido el handshake** |

**Consecuencia de diseño de la cuota**: como el handshake consume cuota, el
conector no debe abrir conexiones ociosas ni reconectar en bucle. `doctor`
hace una sola sesión para todas sus verificaciones.

## Respuestas de error que el conector debe distinguir

| Código | Significado | Qué debe decirle el conector a la persona |
|---|---|---|
| `401` | API key ausente o inválida | La key no sirve o fue revocada → generar una nueva en `/config` |
| `403` | El plan no incluye el servidor MCP | Está disponible desde el plan Empresa |
| `429` | Cuota mensual superada | Cuántas van y cuándo se renueva |
| red/TLS | No se llegó al servidor | Problema de conexión, proxy o red — **no** es problema de credenciales |

El cuerpo de 401/403/429 es JSON: `{"error": "<mensaje en español>"}`. El
conector puede mostrar ese mensaje, pero **debe** agregar la acción sugerida:
el servidor explica la causa, el conector explica el remedio.

## Descubrimiento de tools

- Las tools se descubren **siempre** por protocolo (`tools/list`).
- Está **prohibido** mantener una lista propia, un conteo fijo o un caché de
  tools en este repo (Principio III; lección heredada de `mpbot`, donde la
  documentación escrita a mano se desactualizó tres veces).
- Al momento de escribir este contrato el servidor expone 21 tools. **Ese
  número es informativo, no un supuesto**: ningún código ni test de este repo
  puede depender de él.

## Estabilidad

- El conector tolera que el servidor agregue, cambie o retire tools sin
  requerir cambios de código.
- Cambios incompatibles del servidor se absorben en este repo; el contrato
  hacia los agentes se mantiene estable.
- El conector no asume orden ni nombres específicos de tools.

## Restricciones de seguridad heredadas

- El servidor aplica protección anti DNS-rebinding: valida el host de la
  petición. En desarrollo local esto importa — apuntar a un host o puerto no
  contemplado devuelve `421 Misdirected Request` (observado en pruebas
  reales). El conector debe traducir ese caso a "el servidor no reconoce esta
  dirección", no a un error de credenciales.
- El conector nunca envía la API key a un destino distinto del configurado
  (FR-022).
