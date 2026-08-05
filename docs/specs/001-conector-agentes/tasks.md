# Tasks: Conector mpbot-mcp para agentes de IA

**Input**: Documentos de diseño en `/specs/001-conector-agentes/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: Incluidos — obligatorios por constitución (sección "Flujo de
desarrollo y compuertas"). Ningún test usa API key real ni golpea producción.

**Organization**: Agrupadas por historia de usuario para poder entregar y
verificar cada una por separado.

## Format: `[ID] [P?] [Story] Descripción`

- **[P]**: paralelizable (archivo distinto, sin dependencia pendiente)
- **[Story]**: US1 · US2 · US3 · US4

---

## Phase 1: Setup

- [X] T001 Crear el esqueleto del paquete en `mpbot_mcp/` y `tests/` según el árbol de [plan.md](plan.md), con `pyproject.toml` declarando Python 3.12+, el SDK `mcp` y la biblioteca de CLI interactiva
- [X] T002 [P] Configurar `pytest` en `pyproject.toml` y crear `tests/conftest.py` con el **servidor MCP simulado** compartido (handshake, `tools/list`, `tools/call`, y los 4 modos de falla 401/403/429/red) — ninguna llamada real
- [X] T003 [P] Crear `.gitignore` (excluyendo config local, binarios de `empaque/`, y cualquier archivo que pueda contener una key) y `README.md` inicial

---

## Phase 2: Foundational (bloquea todas las historias)

**⚠️ Ninguna historia puede empezar hasta terminar esta fase.**

- [X] T004 Implementar `mpbot_mcp/config.py`: lectura/escritura de `ConfiguracionConector` ([data-model.md](data-model.md) §1) en el directorio de configuración del usuario, con permisos de solo-dueño, precedencia del entorno sobre el archivo, y **función de enmascarado** de la key
- [X] T005 [P] Tests de `config.py` en `tests/test_config.py`: permisos del archivo, precedencia del entorno, y que el enmascarado nunca deje pasar la key completa (base de SC-004)
- [X] T006 Implementar `mpbot_mcp/errores.py`: traducción de los 4 modos de falla a mensaje en español + acción sugerida, según [contracts/servidor-mpbot.md](contracts/servidor-mpbot.md), incluido el caso `421` (host no reconocido) que NO debe confundirse con credenciales
- [X] T007 [P] Tests de `errores.py` en `tests/test_errores.py`: los 4 modos se distinguen entre sí y ninguno produce un mensaje genérico (FR-011)
- [X] T008 Implementar `mpbot_mcp/cliente.py`: cliente MCP contra el servidor remoto (handshake, `tools/list`, `tools/call`) usando el SDK oficial, con los errores de T006 y **una sola sesión reutilizable** (la cuota cuenta cada request, incluido el handshake)
- [X] T009 [P] Tests de `cliente.py` contra el servidor simulado: descubre tools sin lista propia, y propaga cada error tipado correctamente
- [X] T010 Implementar `mpbot_mcp/agentes/perfil.py` (estructura de `PerfilAgente`, [data-model.md](data-model.md) §2) y `mpbot_mcp/agentes/__init__.py` (registro + detección por presencia de archivo de config, research §5)
- [X] T011 [P] Implementar el mecanismo de respaldo (`RespaldoConfig`, [data-model.md](data-model.md) §4): copia con marca de tiempo antes de toda escritura, sin sobrescribir respaldos previos
- [X] T012 [P] Tests del respaldo y de la detección en `tests/test_agentes_base.py`

**Checkpoint**: base lista — US1 y US2 pueden avanzar en paralelo.

---

## Phase 3: User Story 1 — Conectar mi agente sin saber configurar nada (P1) 🎯 MVP

**Goal**: una persona sin conocimientos técnicos ejecuta una cosa, pega su
key, y su agente queda funcionando.

**Independent Test**: en un equipo con un agente soportado, ejecutar
`instalar`, entregar una key válida, y verificar que el agente lista las
tools de mpbot sin que la persona haya abierto un archivo.

### Tests (escribir primero, deben fallar)

- [X] T013 [P] [US1] Tests de escritura de config por perfil en `tests/test_agentes_claude_code.py`: preserva otras entradas, respalda, es idempotente (FR-005/006/007, SC-005)
- [X] T014 [P] [US1] Mismos tests para Hermes (formato YAML) en `tests/test_agentes_hermes.py`
- [X] T015 [P] [US1] Mismos tests para OpenClaw (JSON anidado) en `tests/test_agentes_openclaw.py`
- [X] T016 [P] [US1] Mismos tests para Claude Desktop en `tests/test_agentes_claude_desktop.py`
- [X] T017 [P] [US1] Test del flujo `instalar` en `tests/test_instalar.py`: con key inválida **no escribe ningún archivo** (FR-003), y sin agentes detectados no falla con error técnico

### Implementación

- [X] T018 [P] [US1] Implementar el perfil `mpbot_mcp/agentes/claude_code.py` (conexión directa con headers)
- [X] T019 [P] [US1] Implementar el perfil `mpbot_mcp/agentes/hermes.py` (YAML, `mcp_servers:` con `url` + `headers`)
- [X] T020 [P] [US1] Implementar el perfil `mpbot_mcp/agentes/openclaw.py` (JSON, `mcp.servers` con `transport: streamable-http` + `headers`)
- [X] T021 [P] [US1] Implementar el perfil `mpbot_mcp/agentes/claude_desktop.py` (forma de conexión a confirmar en la verificación en vivo T024) — **soporte directo desactivado por defecto** (`soporta_directo=False`, solo modo stdio) hasta que T024 confirme si acepta headers
- [X] T022 [US1] Implementar el comando `instalar` en `mpbot_mcp/cli.py` siguiendo el flujo de 7 pasos de [contracts/cli.md](contracts/cli.md), incluida la **advertencia explícita** cuando un agente exige la key en su propia config (Principio IV)
- [X] T023 [US1] Verificación de conexión de punta a punta al final del asistente, informando cuántas tools quedaron disponibles (FR-008)

**Nota de esta corrida (2026-08-02)**: T001–T023 implementados y con 71 tests verdes (`python -m pytest`, cero red, cero keys reales). T024 (verificación en vivo) y las Fases 4–7 quedan explícitamente pendientes para una corrida futura: requieren una API key real de mpbot y agentes reales instalados, ninguno de los cuales está disponible en este entorno de desarrollo. Las rutas de configuración de Hermes/OpenClaw/Claude Desktop usadas en los perfiles son las de research.md §4 (razonables, no verificadas); T024 debe confirmarlas o corregirlas antes de publicar cualquier agente como compatible (Principio II).

### Compuerta de compatibilidad (Principio II — bloqueante)

- [ ] T024 [US1] **Verificar en vivo** los 4 agentes con el protocolo de 3 pasos (research §6: configurar → listar tools → ejecutar una tool con datos reales) y registrar la fecha en cada perfil. Los que no se puedan verificar quedan marcados como no verificados y **no se publican como compatibles**

**Checkpoint**: US1 entregable — el cliente final ya puede conectar su agente.

---

## Phase 4: User Story 2 — Entender por qué no funciona (P2)

**Goal**: la persona resuelve sola los fallos previsibles.

**Independent Test**: provocar cada modo de falla y verificar que el
diagnóstico identifica exactamente cuál es y propone la acción correcta.

### Tests (escribir primero, deben fallar)

- [X] T025 [P] [US2] Tests de `doctor` en `tests/test_doctor.py`: los 7 pasos se ejecutan **en el orden fijo** de [data-model.md](data-model.md) §3, y un paso fallido marca los siguientes como `omitido` sin abortar el reporte
- [X] T026 [P] [US2] Test por cada modo de falla: credencial inválida, plan insuficiente, cuota agotada y conectividad producen mensajes **distintos** (FR-011)
- [X] T027 [P] [US2] Test de seguridad: la key literal **no aparece** en ninguna salida de `doctor`, en ningún modo (SC-004)
- [X] T028 [P] [US2] Test de que `doctor` es útil **sin** configuración previa (FR-013)

### Implementación

- [X] T029 [US2] Implementar `mpbot_mcp/doctor.py` con las 7 verificaciones ordenadas, reusando `cliente.py` en **una sola sesión** (economía de cuota)
- [X] T030 [US2] Implementar la presentación del reporte (✔/✘/‑ con acción sugerida) y el código de salida distinto de cero ante fallo, según [contracts/cli.md](contracts/cli.md)
- [X] T031 [US2] Incluir en el paso "Agentes" el estado de configuración de cada agente detectado

**Nota de esta corrida (2026-08-05)**: T025–T031 implementados con 27 tests
nuevos (registro dinámico + `listar-agentes` + `doctor`), suite total 104
verdes + 1 skipped (permisos POSIX en Windows). De paso se corrigió un bug
real de dependencias: `mcp>=1.27` resolvía a `mcp==2.0.0` (eliminó
`mcp.server.fastmcp`) — el rango quedó fijado a `<2.0` en `pyproject.toml`
con nota de migración futura. La verificación en vivo T024 sigue pendiente
(requiere key real de mpbot y agentes instalados).

**Checkpoint**: US1 + US2 funcionando de forma independiente.

---

## Phase 5: User Story 3 — Agentes que no aceptan credenciales en su config (P3)

**Goal**: el agente lanza el conector como programa local; la key no queda en
su configuración.

**Independent Test**: configurar un agente (o el MCP Inspector) para lanzar
`servir` sin credenciales en su config y verificar que obtiene las mismas
tools.

### Tests (escribir primero, deben fallar)

- [ ] T032 [P] [US3] Test de equivalencia en `tests/test_puente.py`: el conjunto de tools expuesto por `servir` es **idéntico** al del servidor remoto, sin filtrar ni transformar (FR-016, SC-006)
- [ ] T033 [P] [US3] Test de que los errores del servidor llegan como mensajes comprensibles y no como fallas mudas (FR-017)
- [ ] T034 [P] [US3] Test de que una caída de red no deja el proceso colgado indefinidamente

### Implementación

- [ ] T035 [US3] Implementar `mpbot_mcp/puente.py`: servidor MCP local por stdio que reexpone dinámicamente las tools remotas (descubiertas por protocolo, jamás listadas a mano)
- [ ] T036 [US3] Añadir el comando `servir` a `mpbot_mcp/cli.py`, tomando la credencial del almacenamiento propio o del entorno (FR-015)
- [ ] T037 [US3] Extender `instalar` para ofrecer el modo puente cuando el perfil no soporte conexión directa, o cuando la persona prefiera no dejar la key en la config del agente
- [ ] T038 [US3] **Verificar en vivo** el modo puente con al menos un agente real y con el MCP Inspector (el caso que originó esta historia), registrando la fecha

**Checkpoint**: las tres historias funcionales completas.

---

## Phase 6: User Story 4 — Configurar a mano (P4)

**Goal**: quien sabe (o tiene un agente no soportado) encuentra la
instrucción exacta, incluida la conexión directa sin este conector.

- [ ] T039 [P] [US4] Escribir `docs/agentes/<agente>.md` por cada agente verificado: configuración exacta, ubicación del archivo y **fecha de verificación en vivo** (FR-018)
- [ ] T040 [P] [US4] Documentar explícitamente la **conexión directa al servidor sin usar el conector** para los agentes que la soporten (FR-019, Principio VII)
- [ ] T041 [P] [US4] Marcar en la documentación todo agente no verificado como tal, y no contarlo como compatible (FR-020, Principio II)
- [ ] T042 [P] [US4] Escribir `docs/README.md`: qué es, cómo obtener la API key en mpbot, instalación en 3 pasos para el cliente final, y qué hacer si algo falla (remite a `doctor`)

---

## Phase 7: Distribución y cierre

- [ ] T043 Construir el **ejecutable único** en `empaque/` (research §1) y verificar en un equipo **sin Python instalado** que `instalar` y `doctor` funcionan (SC-007) — esta prueba es la que valida el Principio I, no basta con que compile
- [ ] T044 Documentar honestamente la advertencia de SmartScreen mientras el binario no esté firmado, indicando exactamente qué botón apretar (research §1)
- [ ] T045 **Dependencia externa del usuario**: obtener el certificado de firma de código y firmar el binario. Hasta que ocurra, T044 es la mitigación vigente
- [ ] T046 Ejecutar la validación completa de [quickstart.md](quickstart.md) de punta a punta
- [ ] T047 Revocar la API key usada en las verificaciones en vivo desde `app.mpbot.cl/config` (research §6)
- [ ] T048 [P] Registrar en `README.md` el estado real de compatibilidad por agente, con fechas de verificación

---

## Dependencies & Execution Order

### Fases

- **Setup (1)** → **Foundational (2)** → historias
- **US1 (3)** y **US2 (4)** pueden ir en paralelo tras la fase 2
- **US3 (5)** puede ir en paralelo, pero T037 toca `instalar` (T022): coordinar
- **US4 (6)** depende de T024 (no se documenta como compatible lo no verificado)
- **Fase 7** depende de todas las historias que se decidan entregar

### Dentro de cada historia

- Tests antes de la implementación (deben fallar primero)
- Perfiles antes del comando que los usa
- Implementación antes de la verificación en vivo

### Paralelizables

- T002, T003 · T005, T007, T009 · T011, T012
- T013–T017 (tests de perfiles, archivos distintos)
- T018–T021 (perfiles, archivos distintos)
- T025–T028 · T032–T034 · T039–T042

---

## Implementation Strategy

### MVP primero (solo US1)

1. Fases 1 y 2 completas
2. Fase 3 (US1), incluida la compuerta T024
3. **Parar y validar** con [quickstart.md](quickstart.md) §1 y §4
4. Con eso, un cliente Empresa ya conecta su agente sin tocar un archivo

### Entrega incremental

Fase 2 → US1 (MVP) → US2 (diagnóstico) → US3 (puente) → US4 (recetas) →
Fase 7 (binario y firma). Cada historia agrega valor sin romper la anterior.

---

## Notas

- **Nada en este repo puede depender del número de tools del servidor** (hoy
  21): se descubre por protocolo. Un test que lo fije está mal escrito
  (Principio III).
- **Ningún agente se publica como compatible sin verificación en vivo con
  fecha** (Principio II) — es la regla que nació del error real documentado
  en la constitución.
- Si algo de este conector exige cambiar el servidor MCP, se abre feature en
  `mpbot/` con su propio ciclo Spec Kit; acá solo se registra la dependencia
  (ej. publicar la descarga del binario desde el área de cliente, research §1).
