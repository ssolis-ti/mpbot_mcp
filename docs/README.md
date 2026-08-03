# mpbot-mcp

Conector oficial que conecta agentes de IA (Claude Code, Claude Desktop,
Hermes, OpenClaw) al servidor MCP de [mpbot](https://app.mpbot.cl), sin que
la persona tenga que editar ningún archivo de configuración a mano.

**Estado**: en desarrollo. Este documento se completa en la fase de
distribución (ver `specs/001-conector-agentes/tasks.md`, Fase 6).

## Qué hace

- `mpbot-mcp instalar`: detecta tus agentes, pide tu API key y deja tu agente
  conectado a mpbot.
- `mpbot-mcp doctor`: diagnostica en lenguaje llano por qué algo no funciona.
- `mpbot-mcp servir`: modo puente para agentes que no admiten credenciales en
  su configuración (lo usan los agentes, no las personas).

## Desarrollo

```bash
pip install -e ".[dev]"
python -m pytest
```

La suite de tests nunca usa una API key real ni golpea producción: el
servidor MCP se simula.
