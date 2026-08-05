# mpbot-mcp

Conector oficial que conecta **agentes de IA** (Claude Code, Claude Desktop,
Hermes, OpenClaw y cualquiera que hable MCP) al servidor MCP de
[mpbot](https://app.mpbot.cl), sin que tengas que editar ningún archivo de
configuración a mano.

El conector detecta los agentes que tienes instalados, guarda tu API key en
un solo lugar (con permisos de solo-dueño) y escribe la configuración por ti,
respetando lo que ya existía y respaldando antes de tocar nada.

**Estado**: en desarrollo (v0.1.0). Ver estado de compatibilidad por agente
en [Agentes soportados](#agentes-soportados).

---

## Qué hace

| Comando | Para qué |
|---|---|
| `mpbot-mcp instalar` | Detecta tus agentes, pide tu API key y los deja conectados a mpbot. Es todo lo que necesita la mayoría de la gente. |
| `mpbot-mcp doctor` | Diagnostica en lenguaje llano por qué algo no funciona (key, conectividad, autenticación, plan, cuota, tools, agentes). |
| `mpbot-mcp listar-agentes` | Muestra los agentes soportados y su estado de verificación. |
| `mpbot-mcp servir` | Modo puente para agentes que no admiten credenciales en su configuración (lo usan los agentes, no las personas). *Próximamente.* |

---

## Instalación en 3 pasos

Para el cliente final, el camino principal es el **ejecutable único** (sin
necesidad de Python). Mientras se publica, el camino técnico es:

```bash
# 1. Instala el conector
pip install mpbot-mcp

# 2. Conecta tus agentes (te pide la API key de app.mpbot.cl)
mpbot-mcp instalar

# 3. Verifica que todo quedó bien
mpbot-mcp doctor
```

> **¿No funciona algo?** Ejecuta `mpbot-mcp doctor`: te dice exactamente
> qué falla y qué hacer, sin que tengas que leer archivos de configuración.

---

## Agentes soportados

| Agente | Formato | Conexión | Estado |
|---|---|---|---|
| Claude Code | JSON | directa + puente | no verificado |
| Claude Desktop | JSON | puente | no verificado |
| Hermes | YAML | directa + puente | no verificado |
| OpenClaw | JSON | directa + puente | no verificado |

Los agentes marcados como **no verificado** no se declaran compatibles hasta
pasar la verificación en vivo contra el agente real (constitución,
Principio II). Ejecuta `mpbot-mcp listar-agentes` para ver el estado actual.

### Agregar un agente nuevo

Copia `mpbot_mcp/agentes/_template.py` a
`mpbot_mcp/agentes/<id-del-agente>.py` y completa las funciones. El registro
lo descubre solo: **no hay que tocar ningún otro archivo** (ver
`agentes/__init__.py`, `_construir_registro`).

---

## Desarrollo

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate   |   Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest
```

La suite de tests **nunca usa una API key real ni golpea producción**: el
servidor MCP se simula en memoria (SDK oficial vía ASGI), reproduciendo los
cuatro modos de falla del contrato real (401/403/429/421).

> **Nota**: el `pyproject.toml` fija `mcp>=1.27,<2.0` porque la API de
> `mcp` 2.0 eliminó `mcp.server.fastmcp` (usado por la suite de tests).
> Migrar a la API 2.x es trabajo futuro.

---

## Documentación interna

- [Constitución del proyecto](constitution.md) — los 7 principios que gobiernan el diseño.
- [Spec del conector](specs/001-conector-agentes/spec.md) y [plan](specs/001-conector-agentes/plan.md) — diseño completo.
- [Contratos](specs/001-conector-agentes/contracts/) — CLI, perfiles de agente y servidor mpbot.

---

## Licencia

MIT. Ver [LICENSE](LICENSE).
