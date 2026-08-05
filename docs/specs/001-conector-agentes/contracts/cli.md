# Contrato: interfaz de línea de comandos

Tres comandos. El cliente final solo necesita el primero; el tercero lo
invocan los agentes, no las personas.

Todo texto va en español de Chile. Todo error indica el siguiente paso.

---

## `mpbot-mcp instalar`

Asistente interactivo. Es el camino principal del cliente final (US1).

**Flujo**:

1. Detecta agentes instalados y los muestra.
2. Pide la API key si no hay una configurada (entrada oculta, no se hace eco).
3. **Valida la key contra el servidor real antes de escribir nada** (FR-003).
4. Muestra qué archivos va a modificar y pide confirmación explícita (FR-004).
5. Respalda cada archivo preexistente e informa dónde quedó (FR-005).
6. Escribe la entrada de mpbot preservando todo lo demás (FR-006).
7. Verifica la conexión de punta a punta e informa cuántas tools quedaron
   disponibles (FR-008).

**Salidas relevantes**:

| Situación | Comportamiento |
|---|---|
| Key inválida / plan insuficiente / cuota agotada | Mensaje específico por caso; **no escribe nada** |
| Ningún agente detectado | Lo informa y ofrece las instrucciones manuales; no es un error |
| Sin permiso de escritura | Informa el problema de permisos y entrega la instrucción manual |
| Ya configurado | Actualiza sin duplicar (idempotente, FR-007) |

**Opciones no interactivas** (para automatización; no las necesita el cliente
final): permitir indicar la key por entorno, elegir agentes explícitamente, y
un modo que no pregunte nada.

---

## `mpbot-mcp doctor`

Diagnóstico (US2). Debe ser útil incluso sin ninguna configuración previa
(FR-013).

**Ejecuta siempre los 7 pasos en orden fijo** y muestra cada uno con su
estado. Un paso que falla no aborta el reporte: los siguientes quedan
`omitido` con su motivo.

```
mpbot-mcp · diagnóstico

  ✔ API key            configurada (mpb_2f5…)
  ✔ Conectividad       app.mpbot.cl responde (142 ms)
  ✔ Autenticación      key válida
  ✔ Plan               Empresa · acceso al servidor MCP
  ✔ Cuota              47 de 10.000 usadas este mes
  ✔ Tools              21 disponibles
  ✔ Agentes            Claude Code, Hermes configurados

Todo en orden.
```

Ante una falla, el paso muestra qué pasó y qué hacer:

```
  ✘ Autenticación      la key fue revocada o no existe
                       → genera una nueva en app.mpbot.cl/config
  ‑ Plan               omitido (depende de la autenticación)
```

**Distinciones obligatorias** (FR-011): credencial inválida, plan
insuficiente, cuota agotada y problema de conectividad son cuatro mensajes
distintos, nunca uno genérico.

**Salida**: código de salida cero si todo pasó; distinto de cero si algo
falló, para poder usarlo en scripts.

---

## `mpbot-mcp servir`

Modo puente (US3). **Lo lanza el agente, no la persona.**

- Habla MCP por stdio con el agente que lo lanzó.
- Habla MCP por HTTPS con el servidor de mpbot, poniendo la credencial que
  toma de su propia configuración o del entorno (FR-015).
- Reexpone **exactamente** las tools que el servidor declara en ese momento,
  sin lista propia, sin filtrar y sin transformar (FR-016).
- Traduce los errores del servidor a mensajes comprensibles para el agente
  (FR-017) y no queda colgado ante una caída de red.

**Contrato de equivalencia** (verificable): el conjunto de tools y el
resultado de cada llamada a través de `servir` debe ser idéntico al obtenido
por conexión directa al servidor (SC-006).

---

## Reglas transversales de la interfaz

- La API key **nunca** se imprime completa, en ningún comando, ni siquiera en
  modo detallado (FR-012 / SC-004).
- Ningún comando escribe en archivos ajenos sin respaldo previo y sin
  confirmación.
- Ningún comando envía datos a un destino distinto del servidor configurado
  (FR-022) ni recolecta telemetría (FR-023).
