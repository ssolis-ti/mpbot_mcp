# mpbot-mcp

**Un comando. Tus agentes. Los datos de Compra Ágil en tu chat.**

[![tests](https://img.shields.io/badge/tests-112%20passed-brightgreen)](https://github.com/ssolis-ti/mpbot_mcp/actions)
[![python](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![licencia](https://img.shields.io/badge/licencia-MIT-green)](LICENSE)

Conecta cualquier agente de IA (Claude Code, Hermes, OpenClaw, el que uses) al
servidor MCP de [mpbot](https://app.mpbot.cl) y accede a los datos reales de
**Compra Ágil — Mercado Público Chile** directamente desde tu chat. Sin APIs,
sin código, sin abrir un archivo de configuración.

```bash
$ mpbot-mcp instalar
```

Eso es todo. Tu agente ahora tiene acceso a **todas las tools** de
inteligencia de mercado que el servidor de mpbot declare en ese momento
(hoy son 25) — buscar rubros, analizar competencia, descubrir nichos
rentables, detectar licitaciones desiertas y mucho más, con datos frescos de
Compra Ágil.

---

## En 30 segundos

```bash
# 1. Instala (todavía no está publicado en PyPI: se instala desde el repo)
pip install git+https://github.com/ssolis-ti/mpbot_mcp.git

# 2. Conecta tus agentes (te pide la API key cuando la ejecutes)
mpbot-mcp instalar

# 3. Pregúntale a tu agente
# "¿Cómo está el mercado de neumáticos en Aysén?"
# "¿Qué nicho es rentable en la Araucanía?"
# "¿Quién me está ganando las licitaciones de software?"
```

> ¿Algo no funciona? `mpbot-mcp doctor` te dice exactamente qué falla y cómo
> arreglarlo, en español y sin stack traces.

> **¿Cómo obtener tu API key?**
> 1. Ve a [app.mpbot.cl/config](https://app.mpbot.cl/config) e inicia sesión con tu cuenta de Compra Ágil.
> 2. En la sección "API Keys", genera una nueva key (comienza con `mpb_...`).
> 3. Cópiala y pégala cuando el asistente `mpbot-mcp instalar` te la pida.
> 4. Si la pierdes, puedes revocarla y generar otra desde la misma página.

---

## Los 4 comandos

| Comando | Qué hace |
|---|---|
| `mpbot-mcp instalar` | Detecta tus agentes, guarda tu key, los conecta. Listo. |
| `mpbot-mcp doctor` | Diagnostica en español: key, conexión, autenticación, plan, cuota, tools, agentes configurados. |
| `mpbot-mcp listar-agentes` | Muestra los agentes soportados y su estado de verificación. |
| `mpbot-mcp servir` | Modo puente por stdio para agentes sin soporte HTTP (lo lanza el agente, no vos). |

---

## Las tools que tu agente va a tener

```
estado                ·  buscar_rubro          ·  buscar_producto
mercado_rubro         ·  oportunidades         ·  oportunidades_pyme
curva_precio          ·  demanda_esperada      ·  perfil_organismo
perfil_proveedor      ·  ranking_nichos        ·  perfil_competencia
competidores_rubro    ·  cohorte_entrantes     ·  curva_perseverancia
primera_apuesta       ·  backtest_rubro        ·  resumen_mensual
listar_regiones       ·  tasa_desercion        ·  ranking_desercion
licitaciones_desiertas·  nichos_adyacentes     ·  ranking_crecimiento
ventaja_local
```

Todas funcionan con datos reales de **Compra Ágil — Mercado Público Chile**.
Tu agente las descubre solo por protocolo: no hay que configurar nada, y
esta lista es solo referencial (verificada en vivo 2026-09-08, hoy son 25) —
**el conector nunca depende de un catálogo fijo**, así que si mpbot agrega,
cambia o retira una tool, la ves reflejada sin actualizar nada acá.

---

## Agentes soportados

| Agente | Conexión | Probado en vivo |
|---|---|---|
| Hermes | directa + puente | Agosto 2026 |
| Claude Code | directa + puente | Agosto 2026 |
| Claude Desktop | puente | — |
| OpenClaw | directa + puente | — |

¿Usas otro agente? Copiá `mpbot_mcp/agentes/_template.py`, completá 4 datos y
el registro lo descubre solo. No se toca el core.

---

## Tu API key, segura

- Se guarda en un solo archivo con permisos de solo-dueño.
- Nunca se imprime completa (siempre enmascarada: `mpb_46…`).
- Nunca se copia a la configuración de cada agente si hay alternativa.
- Antes de escribir en la config de un agente, respaldamos lo que había.

---

## Licencia

MIT · [mpbot](https://app.mpbot.cl) · Compra Ágil Chile
