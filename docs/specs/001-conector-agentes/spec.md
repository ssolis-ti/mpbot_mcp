# Feature Specification: Conector mpbot-mcp para agentes de IA

**Feature Branch**: `001-conector-agentes`

**Created**: 2026-08-02

**Status**: Draft

**Input**: Diseñar el "MCP cliente" de mpbot para que agentes (Claude Code,
Claude Desktop, Hermes, OpenClaw, OpenCode y otros) puedan conectarse y usar
el servidor MCP de mpbot. Decisiones del usuario: entregable = puente +
diagnóstico + recetas ("producto completo"); agentes obligatorios en v1 =
Claude Code / Claude Desktop, Hermes, OpenClaw; el criterio rector de stack y
distribución es **la simplicidad para un cliente final que quizás no sabe
instalar nada**.

## Contexto y problema

mpbot expone hoy 21 tools de inteligencia de mercado por MCP en
`https://app.mpbot.cl/mcp/`, protegidas por API key (`mpb_…`) y plan Empresa.
El servidor funciona: verificado en vivo por protocolo real, 21/21 tools
respondiendo.

El problema **no** es el servidor: es la última milla hasta el agente del
cliente. Hoy, para usar mpbot desde su agente, una persona debe saber (a) que
existe la API key y dónde sacarla, (b) cuál de los múltiples archivos de
configuración de su agente tocar, (c) el formato exacto que ese agente
espera, distinto en cada uno (JSON anidado, YAML, claves con nombres
diferentes), (d) usar rutas absolutas, y (e) interpretar por su cuenta un
`401`/`403`/`429` cuando algo falla.

Evidencia real de que esta fricción existe y muerde: en una sesión de prueba
del propio equipo, con el servidor funcionando perfecto, no se logró conectar
el MCP Inspector oficial por no encontrar dónde poner el header de
autenticación — se terminó recurriendo a un script propio. Si le pasa a quien
construyó el servidor, le pasa al cliente.

**Hallazgo que acota el alcance** (verificado, no supuesto): los tres agentes
obligatorios de v1 **sí** soportan servidores MCP remotos por HTTP con
headers propios — Claude Code (`.mcp.json` / `claude mcp add`), Hermes
(`mcp_servers:` con `url` + `headers`, documentado en su
`cli-config.yaml.example`) y OpenClaw (`mcp.servers` con `transport:
streamable-http` + `headers`). Por lo tanto **la conexión directa es posible
hoy y esta feature no la reemplaza: la automatiza, la diagnostica y la
documenta**. El puente stdio deja de ser la pieza central y pasa a cubrir dos
casos concretos y acotados (agentes sin soporte de headers, y no dejar la key
en texto plano en varios archivos).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Conectar mi agente sin saber configurar nada (Priority: P1) 🎯 MVP

Una persona con plan Empresa, que usa un agente de IA pero nunca editó un
archivo de configuración, quiere que su agente pueda consultar los datos de
mpbot. Ejecuta una sola cosa, pega su API key cuando se la piden, elige de
una lista los agentes que tiene instalados, y al terminar su agente ya puede
usar las tools de mpbot.

**Why this priority**: Es la razón de existir del proyecto y el único
escenario que, por sí solo, entrega valor completo al cliente final. Sin
esto, lo demás es accesorio.

**Independent Test**: En una máquina con al menos un agente soportado
instalado, ejecutar el conector, entregar una API key válida, aceptar los
agentes detectados, y verificar que ese agente lista las tools de mpbot sin
que la persona haya abierto ningún archivo.

**Acceptance Scenarios**:

1. **Given** un equipo con uno o más agentes soportados instalados, **When**
   la persona ejecuta el conector por primera vez, **Then** el conector le
   muestra qué agentes encontró y le pide confirmación antes de tocar nada.
2. **Given** que la persona confirma, **When** el conector escribe la
   configuración, **Then** respalda cualquier configuración previa con marca
   de tiempo y le informa dónde quedó el respaldo.
3. **Given** una API key válida de plan Empresa, **When** termina la
   configuración, **Then** el conector verifica la conexión de punta a punta
   y le informa cuántas tools quedaron disponibles.
4. **Given** una API key inválida, de plan insuficiente o con cuota agotada,
   **When** la persona la ingresa, **Then** el conector se lo dice en lenguaje
   llano y **no** escribe ninguna configuración.
5. **Given** que la persona no tiene ningún agente soportado instalado,
   **When** ejecuta el conector, **Then** se lo informa y le ofrece las
   instrucciones manuales, sin fallar con un error técnico.
6. **Given** una configuración de mpbot ya existente de una corrida anterior,
   **When** la persona vuelve a ejecutar el conector, **Then** la actualiza
   de forma idempotente sin duplicar entradas ni romper otros servidores MCP
   que la persona tuviera configurados.

---

### User Story 2 - Entender por qué no funciona, sin pedir ayuda (Priority: P2)

Algo dejó de funcionar (la key fue revocada, se acabó la cuota del mes, el
plan cambió, hay un proxy corporativo, se cayó la red). La persona ejecuta el
diagnóstico y obtiene, paso a paso, qué está bien, qué está mal y qué hacer
para arreglarlo — sin escribirle a nadie.

**Why this priority**: Es lo que convierte al conector en algo mantenible en
manos del cliente. Depende de que exista una configuración (US1), pero se
prueba por separado.

**Independent Test**: Con una configuración existente, provocar cada modo de
falla conocido (key inválida, plan sin acceso, cuota excedida, servidor
inalcanzable) y verificar que el diagnóstico identifica exactamente cuál es y
propone la acción correcta.

**Acceptance Scenarios**:

1. **Given** todo correcto, **When** la persona ejecuta el diagnóstico,
   **Then** ve una verificación paso a paso (key presente → servidor
   alcanzable → autenticación → plan → cuota → tools → agentes configurados)
   con resultado explícito en cada paso.
2. **Given** una key revocada o inválida, **When** ejecuta el diagnóstico,
   **Then** el reporte señala ese paso como el que falla y le indica dónde
   generar una key nueva.
3. **Given** una cuota mensual agotada, **When** ejecuta el diagnóstico,
   **Then** distingue ese caso de una key inválida y le informa cuándo se
   renueva.
4. **Given** un plan sin acceso a la capacidad, **When** ejecuta el
   diagnóstico, **Then** lo distingue de los dos anteriores y le indica qué
   plan lo incluye.
5. **Given** que la API key aparece en cualquier salida del diagnóstico,
   **When** la persona la comparte para pedir ayuda, **Then** la key va
   siempre enmascarada y nunca completa.
6. **Given** un problema de red, TLS o proxy corporativo, **When** ejecuta el
   diagnóstico, **Then** lo identifica como problema de conectividad y no lo
   confunde con un problema de credenciales.

---

### User Story 3 - Conectar agentes que no aceptan credenciales en su configuración (Priority: P3)

Existen agentes y herramientas que solo saben lanzar un programa local
(stdio) y no permiten declarar headers HTTP propios — o la persona
simplemente no quiere dejar su API key escrita en texto plano en los archivos
de configuración de tres agentes distintos. En ambos casos, el agente lanza
el conector como programa local, y el conector se encarga de hablar con el
servidor remoto poniendo la credencial que él guarda de forma segura.

**Why this priority**: Cubre dos necesidades reales y verificadas (una
funcional, una de seguridad), pero ninguno de los tres agentes obligatorios
de v1 la requiere para funcionar — por eso no bloquea el MVP.

**Independent Test**: Configurar un agente (o el MCP Inspector, caso real ya
documentado) para lanzar el conector como programa local sin ninguna
credencial en su configuración, y verificar que las tools quedan disponibles
igual que por conexión directa.

**Acceptance Scenarios**:

1. **Given** un agente configurado para lanzar el conector como programa
   local, **When** el agente inicia, **Then** obtiene exactamente las mismas
   tools que por conexión directa, sin diferencias de resultado.
2. **Given** esa configuración, **When** alguien inspecciona los archivos de
   configuración del agente, **Then** la API key **no** aparece en ellos.
3. **Given** que el servidor responde un error de autenticación, plan o
   cuota, **When** el agente hace una llamada, **Then** el mensaje que ve la
   persona explica la causa en lenguaje llano, sin perderse dentro del
   protocolo.
4. **Given** una caída temporal de red durante una llamada, **When** ocurre,
   **Then** el conector lo reporta como fallo de conexión sin dejar al agente
   colgado indefinidamente.

---

### User Story 4 - Configurar a mano, para quien sí sabe (Priority: P4)

Una persona técnica (o alguien con un agente aún no soportado
automáticamente) quiere la instrucción exacta para su caso, incluida la
opción de conectarse **directo** al servidor sin usar este conector.

**Why this priority**: Amplía cobertura más allá de los agentes detectados y
cumple el principio de no ocultar el camino directo. No bloquea a nadie del
público principal.

**Independent Test**: Seguir la receta publicada de cada agente soportado, a
mano, en un equipo limpio, y verificar que el agente queda funcionando.

**Acceptance Scenarios**:

1. **Given** un agente soportado, **When** la persona busca su receta,
   **Then** encuentra la configuración exacta, la ubicación del archivo y la
   fecha en que esa receta fue verificada en vivo.
2. **Given** un agente que soporta conexión directa al servidor remoto,
   **When** la persona lee la documentación, **Then** esa opción está
   explícita, aunque implique no usar este conector.
3. **Given** un agente no verificado, **When** aparece en la documentación,
   **Then** está marcado como no verificado y no se presenta como compatible.

### Edge Cases

- ¿Qué pasa si la persona ejecuta el conector dos veces seguidas? Debe ser
  idempotente: no duplica entradas ni pierde configuración previa.
- ¿Qué pasa si el archivo de configuración del agente está corrupto o tiene
  formato inválido? No se sobrescribe a ciegas: se avisa, se respalda y se
  pide confirmación.
- ¿Qué pasa si la persona tiene otros servidores MCP configurados? Nunca se
  tocan: el conector agrega o actualiza únicamente su propia entrada.
- ¿Qué pasa si el equipo no tiene permisos de escritura en la ubicación de
  configuración del agente? Se informa el problema de permisos y se entrega
  la instrucción manual como alternativa.
- ¿Qué pasa si el servidor cambia su lista de tools (agrega o retira)? El
  conector lo refleja automáticamente; no mantiene una lista propia.
- ¿Qué pasa si la persona pierde su API key? El conector nunca la puede
  mostrar completa; se la guía a generar una nueva.
- ¿Qué pasa si hay varias cuentas o keys en el mismo equipo? Fuera de alcance
  en v1: una configuración activa por equipo (documentado en Assumptions).

## Requirements *(mandatory)*

### Functional Requirements

**Configuración asistida (US1)**

- **FR-001**: El sistema DEBE detectar automáticamente qué agentes
  soportados están instalados en el equipo.
- **FR-002**: El sistema DEBE solicitar la API key de forma interactiva
  cuando no esté ya configurada, y aceptarla también desde el entorno para
  usos automatizados.
- **FR-003**: El sistema DEBE validar la API key contra el servidor real
  **antes** de escribir cualquier configuración.
- **FR-004**: El sistema DEBE pedir confirmación explícita antes de modificar
  el archivo de configuración de cualquier agente.
- **FR-005**: El sistema DEBE respaldar todo archivo de configuración
  preexistente, con marca de tiempo, antes de modificarlo, e informar la
  ubicación del respaldo.
- **FR-006**: El sistema DEBE preservar intactas las demás entradas de
  configuración del agente (otros servidores MCP y cualquier otro ajuste).
- **FR-007**: La configuración DEBE ser idempotente: ejecutarla de nuevo
  actualiza la entrada existente sin duplicarla.
- **FR-008**: Al terminar, el sistema DEBE verificar la conexión de punta a
  punta e informar cuántas tools quedaron disponibles.
- **FR-009**: El sistema DEBE poder ejecutarse en el equipo del cliente final
  **sin exigir la instalación previa de ningún runtime, gestor de paquetes ni
  dependencia** (Principio I).

**Diagnóstico (US2)**

- **FR-010**: El sistema DEBE ofrecer un diagnóstico que verifique, en orden
  y con resultado explícito por paso: presencia de key, conectividad con el
  servidor, autenticación, plan, cuota, disponibilidad de tools y estado de
  configuración de los agentes detectados.
- **FR-011**: El diagnóstico DEBE distinguir entre credencial inválida, plan
  insuficiente, cuota agotada y problema de conectividad, con un mensaje y
  una acción sugerida distintos para cada uno.
- **FR-012**: El sistema NUNCA DEBE mostrar la API key completa en ninguna
  salida (pantalla, log, reporte, mensaje de error): siempre enmascarada.
- **FR-013**: El diagnóstico DEBE poder ejecutarse y ser útil aunque no haya
  ninguna configuración de agente aún.

**Conexión por programa local (US3)**

- **FR-014**: El sistema DEBE poder operar como servidor MCP local (lanzado
  por el agente) que reexpone las tools del servidor remoto de mpbot.
- **FR-015**: En ese modo, la API key DEBE provenir del almacenamiento propio
  del conector o del entorno, y **no** ser requerida en la configuración del
  agente.
- **FR-016**: En ese modo, las tools expuestas DEBEN ser exactamente las que
  el servidor remoto declare en ese momento, sin lista propia ni filtrado.
- **FR-017**: Los errores del servidor (autenticación, plan, cuota, red)
  DEBEN llegar al agente como mensajes comprensibles y no como fallas mudas.

**Documentación (US4)**

- **FR-018**: La documentación DEBE incluir, por cada agente soportado, la
  configuración exacta, la ubicación del archivo y la fecha de su última
  verificación en vivo.
- **FR-019**: La documentación DEBE ofrecer explícitamente la opción de
  conexión directa al servidor para los agentes que la soporten, aunque eso
  implique no usar este conector (Principio VII).
- **FR-020**: Todo agente no verificado en vivo DEBE aparecer marcado como no
  verificado y no contarse como compatible (Principio II).

**Transversales**

- **FR-021**: Toda la interfaz, mensajes y documentación de usuario DEBEN
  estar en español de Chile y en lenguaje llano, indicando siempre el
  siguiente paso ante un error.
- **FR-022**: El sistema NO DEBE enviar la API key ni ningún dato del usuario
  a ningún destino distinto del servidor mpbot configurado.
- **FR-023**: El sistema NO DEBE recolectar telemetría.
- **FR-024**: El sistema NO DEBE implementar lógica de negocio sobre los
  datos de mercado: solo transporta lo que el servidor entrega (Principio
  III).

### Key Entities

- **Configuración del conector**: la API key y la dirección del servidor,
  guardadas una sola vez por equipo en un lugar propio con permisos
  restrictivos.
- **Perfil de agente**: descripción de un agente soportado — cómo detectar si
  está instalado, dónde vive su configuración, en qué formato se declara un
  servidor MCP, si admite conexión directa con credenciales, y la fecha de su
  última verificación en vivo.
- **Reporte de diagnóstico**: resultado ordenado de las verificaciones, cada
  una con estado y, si falla, causa y acción sugerida.
- **Respaldo de configuración**: copia con marca de tiempo del archivo de un
  agente antes de ser modificado.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Una persona sin conocimientos técnicos conecta su agente a
  mpbot en menos de 5 minutos desde que obtiene su API key, sin abrir ningún
  archivo de configuración.
- **SC-002**: El 100% de los agentes listados como compatibles cuenta con una
  verificación en vivo registrada con fecha.
- **SC-003**: El 100% de los modos de falla conocidos (credencial inválida,
  plan insuficiente, cuota agotada, problema de conectividad) es identificado
  correctamente y por separado por el diagnóstico.
- **SC-004**: La API key nunca aparece completa en ninguna salida del
  sistema, verificable de forma automatizada.
- **SC-005**: Ejecutar la configuración dos veces seguidas deja el archivo
  del agente funcionalmente idéntico (idempotencia) y sin perder ninguna otra
  entrada preexistente.
- **SC-006**: El conjunto de tools disponibles a través del conector es
  idéntico al que el servidor declara, sin diferencia alguna.
- **SC-007**: El camino principal del cliente final no requiere instalar
  ningún runtime ni dependencia previa.

## Assumptions

- El cliente ya tiene una cuenta mpbot con plan Empresa y sabe obtener su API
  key desde `/config` del producto web; generar o comprar el plan está fuera
  de alcance de este conector.
- Una configuración activa por equipo (una key, un servidor). Múltiples
  cuentas o perfiles simultáneos en la misma máquina quedan fuera de v1.
- El sistema operativo objetivo de v1 es Windows (el del cliente y el equipo
  de desarrollo actual); macOS y Linux se contemplan en el diseño pero su
  verificación en vivo puede quedar fuera de v1 y, en ese caso, se marcan
  como no verificados (Principio II).
- Los agentes obligatorios de v1 son Claude Code, Claude Desktop, Hermes y
  OpenClaw. OpenCode y otros quedan como extensión posterior, no como
  omisión.
- El servidor MCP de mpbot se mantiene disponible con el contrato descrito en
  la constitución; cambios en él se absorben en este repo.
- No se construye interfaz gráfica en v1: la asistencia es por línea de
  comandos guiada e interactiva, ejecutable sin instalar nada. Una interfaz
  gráfica es una posible iteración futura si la evidencia de uso la pide.
