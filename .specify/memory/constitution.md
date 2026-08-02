<!--
Sync Impact Report
- Version change: (template) → 1.0.0
- Modified principles: n/a (adopción inicial)
- Added sections: Core Principles (I–VII), Contrato con el servidor mpbot,
  Seguridad y privacidad, Flujo de desarrollo y compuertas, Governance
- Removed sections: ninguna
- Templates requiring updates:
  ✅ .specify/templates/plan-template.md (Constitution Check genérico; compatible sin cambios)
  ✅ .specify/templates/spec-template.md (compatible sin cambios)
  ✅ .specify/templates/tasks-template.md (compatible sin cambios)
- Follow-up TODOs: ninguno
-->

# mpbot-mcp Constitution

Conector oficial que permite a cualquier agente de IA (Claude Code, Claude
Desktop, Hermes, OpenClaw, OpenCode y los que vengan) conectarse al servidor
MCP de mpbot (`https://app.mpbot.cl/mcp/`) y usar sus tools de inteligencia
de mercado sobre Compra Ágil (Mercado Público, Chile).

Este repo es **independiente** de `mpbot/` (el producto SaaS y su servidor
MCP), pero está **atado por contrato** a él. Esta constitución gobierna toda
spec, plan, tarea e implementación de este proyecto.

## Core Principles

### I. El cliente final no es desarrollador (NON-NEGOTIABLE)

El usuario objetivo es un **proveedor del Estado con plan Empresa**: sabe de
su negocio, no de JSON, YAML, rutas absolutas ni variables de entorno. Toda
decisión de diseño se juzga contra "¿puede completarlo alguien que nunca
instaló una herramienta de línea de comandos?".

Consecuencias obligatorias:
- **Cero prerequisitos**: el camino principal NO puede exigir que el usuario
  instale Node, Python, uv, pip ni ningún runtime previo.
- **Cero edición manual de archivos de configuración** en el camino feliz: la
  herramienta detecta los agentes instalados y escribe la configuración por
  él, respaldando lo que ya existía.
- Todo mensaje de error se escribe en español de Chile, en lenguaje llano, y
  dice **qué hacer a continuación** — nunca un stack trace desnudo.
- El camino técnico (instalar por gestor de paquetes, editar la config a
  mano) se documenta y se soporta, pero es el camino secundario.

### II. Compatibilidad verificada, jamás declarada (NON-NEGOTIABLE)

Una receta de configuración para un agente **solo puede publicarse si se
probó en vivo contra ese agente real**, conectando al servidor real y
listando sus tools. Está prohibido inferir el formato de config de un agente
a partir de un ejemplo suelto, de su documentación o del parecido con otro
agente.

Origen de la regla (error real, 2026-08-02): se afirmó que Hermes no
soportaba headers HTTP porque el único servidor `url:` de su config viva no
los declaraba. La documentación del propio Hermes
(`cli-config.yaml.example`) sí los soporta explícitamente. La inferencia era
cómoda, plausible y falsa — y estuvo a punto de justificar un producto
entero sobre una premisa equivocada.

Cada agente soportado declara en la documentación su **estado de
verificación** (`verificado en vivo AAAA-MM-DD` / `no verificado`), y los no
verificados se marcan como tales frente al usuario. Un agente que no se pudo
probar NO se lista como compatible.

### III. Conducto delgado: cero lógica de negocio en el cliente

Este proyecto transporta, configura y diagnostica. **Nunca** interpreta,
transforma, resume, cachea ni reimplementa el dato de mercado: eso vive en el
catálogo de tools del servidor mpbot, única fuente de verdad (constitución IV
de mpbot: capa de servicio canal-agnóstica).

Prohibido en este repo: consultas SQL, réplicas de los marts, "mejoras" al
resultado de una tool, cachés de respuestas de negocio, tools propias que no
existan en el servidor. Si falta una capacidad de datos, se agrega en
`mpbot/`, no acá.

### IV. La API key es un secreto, y se trata como tal

La API key (`mpb_…`) da acceso a datos de un plan pagado y consume cuota.

- **Un solo lugar de almacenamiento** por máquina, con permisos restrictivos;
  jamás copiada a los archivos de configuración de cada agente si existe
  alternativa.
- **Nunca** se imprime completa: en pantalla, logs y diagnósticos va siempre
  enmascarada (`mpb_2f5…`).
- **Nunca** se envía a otro destino que `https://app.mpbot.cl` (o el
  `MPBOT_URL` que el propio usuario configure explícitamente).
- Prohibido en el repo: keys reales en código, tests, ejemplos, fixtures o
  documentación. Los ejemplos usan `mpb_TU_API_KEY`.
- La herramienta guía a revocar/rotar en `/config` de mpbot; nunca inventa un
  canal paralelo de credenciales.

### V. Fallar explicando (diagnóstico antes que soporte humano)

Cada modo de falla conocido tiene un mensaje propio que nombra la causa y el
remedio. Como mínimo los que el servidor ya distingue: `401` (key ausente o
inválida), `403` (plan sin `api_datos`), `429` (cuota mensual superada), más
los de red (DNS, TLS, proxy corporativo, timeout).

El comando `doctor` es ciudadano de primera clase, no un extra: verifica en
orden key → conectividad → autenticación → plan → cuota → tools →
configuración de agentes detectados, y reporta cada paso con ✔/✘ y una acción
concreta. Si un usuario necesita escribirle a un humano para entender un
fallo previsible, el diagnóstico falló.

### VI. Simplicidad tecnológica y un solo stack

Python 3.12+ y el SDK oficial `mcp`, mismo stack que el servidor
(constitución VI de mpbot). Distribución primaria como **ejecutable único sin
runtime** para el cliente final; gestores de paquetes para el técnico.

Incorporar cualquier tecnología o dependencia nueva exige documentar en la
spec: la necesidad concreta que el stack actual no cubre, el costo de
mantención asumido y la condición de reversa. YAGNI: lo que no exige el plan
vigente no se construye.

### VII. Interoperabilidad sin favoritismos

El conector no privilegia a un agente sobre otro: todo agente que hable MCP es
ciudadano de primera clase. Las capacidades expuestas son idénticas en todos
(las mismas tools del servidor); lo único que varía por agente es el formato
de su configuración.

Cuando un agente soporta el servidor remoto **directamente** (HTTP con
headers), la documentación DEBE decirlo y ofrecer esa vía como opción — aun
cuando eso signifique que el usuario no necesite este conector. Ocultar el
camino directo para justificar la existencia del producto está prohibido.

## Contrato con el servidor mpbot

- **Endpoint**: `https://app.mpbot.cl/mcp/` (configurable por `MPBOT_URL`
  para desarrollo o staging).
- **Transporte**: MCP Streamable HTTP, modo *stateless* con respuesta JSON.
- **Autenticación**: header `Authorization: Bearer mpb_…` (equivalente:
  `X-API-Key`).
- **Requisito de plan**: `api_datos` (plan Empresa). Sin él: `403`.
- **Cuota**: mensual por key; cada request HTTP cuenta 1, incluido el
  handshake. Excedida: `429`.
- **Errores**: cuerpo JSON `{"error": "<mensaje en español>"}` en 401/403/429.
- El conector **no versiona ni congela** la lista de tools: la descubre por
  protocolo (`tools/list`). Si el servidor agrega, cambia o retira una tool,
  el conector lo refleja sin cambios de código. Está prohibido mantener una
  lista de tools escrita a mano (lección heredada de `mpbot`: la doc a mano se
  desactualiza sola; allá mordió tres veces).
- Cambios incompatibles del servidor se absorben acá; el contrato hacia los
  agentes se mantiene estable.

## Seguridad y privacidad

- El conector **no recolecta telemetría** del usuario ni de sus consultas.
  Cualquier futura métrica exige consentimiento explícito y opt-in, y se
  documenta en la spec que la introduzca.
- Los logs locales nunca contienen la API key completa ni el contenido de
  negocio de las respuestas; solo metadatos operativos (tool invocada,
  latencia, código de resultado).
- El conector solo escribe en su propio directorio de configuración y en los
  archivos de configuración de agentes que el usuario autorice explícitamente.
  Toda escritura sobre un archivo ajeno preexistente exige respaldo previo con
  marca de tiempo.
- Ninguna acción destructiva (sobrescribir la config de un agente, revocar una
  key) ocurre sin confirmación explícita.

## Flujo de desarrollo y compuertas

- Fases Spec Kit por feature: `constitution → specify → plan → tasks →
  implement`, con `clarify`/`analyze` cuando el riesgo lo amerite. Specs y
  código viven en el mismo repo; si la implementación contradice la spec, se
  corrige la spec en el mismo cambio.
- **Compuerta de compatibilidad**: ninguna feature que agregue soporte a un
  agente se considera completa sin una verificación en vivo registrada
  (agente real, servidor real, fecha) — Principio II.
- **Testing**: `pytest` obligatorio para la lógica de configuración (parseo,
  escritura, respaldo, detección de agentes) y para el manejo de errores del
  transporte. Los tests **nunca** usan una API key real ni golpean producción:
  el servidor se simula, salvo en las verificaciones manuales en vivo, que se
  registran aparte.
- Bug reproducido = test primero, fix después.
- **Git**: commits atómicos en español; rama por feature; `main` siempre
  distribuible.
- Español de Chile en toda la interfaz, mensajes y documentación de usuario.

## Governance

Esta constitución prevalece sobre cualquier otra práctica del repo. Las
enmiendas se hacen por commit que actualice este archivo con versionado
semántico (MAYOR: eliminación o redefinición incompatible de principios;
MENOR: principio o sección nueva o guía materialmente expandida; PARCHE:
clarificaciones), fecha de enmienda y nota en el Sync Impact Report.

Toda spec y todo plan incluyen un "Constitution Check" contra los principios
I–VII; una violación debe justificarse en la sección de complejidad del plan o
corregirse antes de implementar.

Relación con `mpbot/`: este repo NO modifica el servidor. Si una necesidad de
este conector exige un cambio en el servidor MCP, se abre la feature
correspondiente en `mpbot/` con su propio ciclo Spec Kit, y acá se registra la
dependencia.

**Version**: 1.0.0 | **Ratified**: 2026-08-02 | **Last Amended**: 2026-08-02
