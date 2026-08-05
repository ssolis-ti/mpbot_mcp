# Implementation Plan: Conector mpbot-mcp para agentes de IA

**Branch**: `001-conector-agentes` | **Date**: 2026-08-02 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-conector-agentes/spec.md`

## Summary

Construir `mpbot-mcp`: un ejecutable único, sin runtime previo, que (1)
detecta los agentes de IA instalados y les escribe la configuración para
hablar con el servidor MCP de mpbot, (2) diagnostica en lenguaje llano por
qué algo no funciona, y (3) puede actuar como servidor MCP local que
reexpone las tools remotas para agentes que no admiten credenciales en su
config. El conector no implementa lógica de negocio: descubre las tools por
protocolo y las transporta tal cual.

## Technical Context

**Language/Version**: Python 3.12+

**Primary Dependencies**: SDK oficial `mcp` (cliente Streamable HTTP y
servidor stdio), `httpx` (ya es dependencia transitiva del SDK), una
biblioteca de CLI/prompts interactivos, y `PyYAML` únicamente si un perfil de
agente lo exige (Hermes usa YAML)

**Storage**: un archivo de configuración propio en el directorio de
configuración del usuario, con permisos restringidos; sin base de datos

**Testing**: `pytest`, con el servidor MCP simulado; **cero** llamadas a
producción y **cero** API keys reales en la suite

**Target Platform**: Windows (verificado en v1); macOS y Linux contemplados
en el diseño, marcados como no verificados si no se prueban

**Project Type**: CLI + servidor MCP local, distribuido como ejecutable único

**Performance Goals**: el asistente completo (detección → key → escritura →
verificación) por debajo de 30 s en un equipo normal; el diagnóstico completo
por debajo de 10 s

**Constraints**: cero prerequisitos de instalación para el cliente final
(FR-009); la API key jamás completa en ninguna salida (FR-012); no
reimplementar lógica de negocio (FR-024)

**Scale/Scope**: 4 perfiles de agente en v1; 3 comandos de usuario
(`instalar`, `doctor`, `servir`); un catálogo de tools descubierto, no
declarado

## Constitution Check

*GATE: debe pasar antes de la Fase 0. Re-evaluado tras la Fase 1.*

- **I. El cliente final no es desarrollador** — PASA. La distribución
  primaria es un ejecutable sin prerequisitos (research §1); el camino feliz
  no exige editar archivos; todos los mensajes van en español llano con
  siguiente paso. **Riesgo declarado**: la advertencia de SmartScreen sin
  firma de código; mitigación y dependencia externa registradas en
  research §1, y tarea explícita en `tasks.md`.
- **II. Compatibilidad verificada, jamás declarada** — PASA. Ningún agente se
  declara compatible en esta fase: los cuatro están marcados "por verificar"
  (research §4) y la verificación en vivo es una tarea bloqueante de cada
  historia, con protocolo de 3 pasos definido (research §6).
- **III. Conducto delgado** — PASA. FR-016 y FR-024 prohíben lista propia de
  tools, caché o transformación; el diseño descubre por `tools/list` y
  transporta sin tocar el contenido.
- **IV. La API key es un secreto** — PASA. Almacenamiento único con permisos
  restringidos (research §2); enmascarado obligatorio (FR-012) con criterio
  de éxito verificable automáticamente (SC-004); advertencia explícita cuando
  un agente exige la credencial en su propia config.
- **V. Fallar explicando** — PASA. `doctor` es un comando de primera clase con
  siete verificaciones ordenadas (FR-010) y cuatro modos de falla
  distinguidos (FR-011), cada uno con criterio de aceptación propio.
- **VI. Simplicidad tecnológica y un solo stack** — PASA. Python, mismo stack
  que el servidor; sin GUI en v1; sin segundo stack (Node descartado con
  fundamento en research §1). Cada dependencia nueva queda justificada en
  Technical Context.
- **VII. Interoperabilidad sin favoritismos** — PASA. FR-019 obliga a
  documentar la conexión directa incluso cuando implique no usar el conector;
  los perfiles de agente son datos, no código, para que ningún agente sea
  ciudadano de segunda.

Sin violaciones — no aplica la sección Complexity Tracking.

**Re-evaluación post-diseño (tras Fase 1)**: sin cambios de conclusión. El
diseño de perfiles-como-datos refuerza VII; el modo `servir` no introduce
lógica de negocio (III); ningún artefacto de diseño requiere exponer la key
ni sumar stack.

## Project Structure

### Documentation (this feature)

```text
specs/001-conector-agentes/
├── plan.md              # Este archivo
├── spec.md              # Especificación (qué y por qué)
├── research.md          # Fase 0: decisiones técnicas fundamentadas
├── data-model.md        # Fase 1: entidades y su forma
├── quickstart.md        # Fase 1: cómo validar que funciona
├── contracts/           # Fase 1: contratos de CLI, config y transporte
│   ├── cli.md
│   ├── perfil-agente.md
│   └── servidor-mpbot.md
├── checklists/
│   └── requirements.md  # Calidad de la spec (superado)
└── tasks.md             # Fase 2 (/speckit-tasks) — no lo crea /speckit-plan
```

### Source Code (repository root)

```text
mpbot_mcp/
├── __init__.py
├── cli.py                  # punto de entrada: instalar | doctor | servir
├── config.py               # almacenamiento de la key y del endpoint (permisos, enmascarado)
├── cliente.py              # cliente MCP contra el servidor remoto (handshake, tools, errores tipados)
├── errores.py              # traducción de 401/403/429/red → mensaje en español + acción
├── doctor.py               # las 7 verificaciones ordenadas
├── puente.py               # modo `servir`: servidor MCP local que reexpone lo remoto
└── agentes/
    ├── __init__.py         # registro y detección
    ├── perfil.py           # estructura de un perfil (datos, no código)
    ├── claude_code.py
    ├── claude_desktop.py
    ├── hermes.py
    └── openclaw.py

tests/
├── conftest.py             # servidor MCP simulado; ninguna llamada real
├── test_config.py          # almacenamiento, permisos, enmascarado
├── test_errores.py         # los 4 modos de falla distinguidos
├── test_doctor.py          # orden y resultado de las verificaciones
├── test_agentes_<n>.py     # por perfil: detección, escritura, respaldo, idempotencia
└── test_puente.py          # el modo servir refleja exactamente las tools remotas

empaque/
└── (receta de construcción del ejecutable único)

docs/
├── README.md               # instalación y primeros pasos para el cliente final
└── agentes/                # una receta por agente, con su fecha de verificación
```

**Structure Decision**: un solo paquete Python con un subpaquete `agentes/`
donde cada perfil es un módulo de datos independiente. Esa separación es la
que permite agregar OpenCode (o cualquier agente futuro) sin tocar el motor
—exigencia directa del Principio VII— y mantener el estado de verificación
pegado al perfil que describe. `empaque/` aísla la construcción del binario
para que el código de aplicación no sepa nada de cómo se distribuye.

## Complexity Tracking

*Sin violaciones de la Constitution Check — sección no aplica.*
