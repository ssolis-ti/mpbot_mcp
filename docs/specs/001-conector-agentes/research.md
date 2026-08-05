# Research: Conector mpbot-mcp para agentes de IA

Decisiones técnicas que la spec dejó abiertas a propósito, resueltas acá con
su fundamento y las alternativas descartadas.

---

## 1. Stack y forma de distribución (la decisión rectora)

**Pregunta del usuario**: *"¿Cómo sería lo más sencillo para el cliente
final? Tenemos que pensar que quizás desconoce la instalación."*

**Decisión**: **Python 3.12+ empaquetado como ejecutable único sin runtime**
(`mpbot-mcp.exe` en Windows) como camino principal para el cliente final, más
`pipx` / `uvx` como camino secundario para quien es técnico.

**Rationale**:

El criterio no es qué stack es más popular en el ecosistema MCP, sino qué le
pide al cliente **antes** de poder empezar. Comparación de lo que exige cada
opción a una persona que "quizás desconoce la instalación":

| Opción | Lo que el cliente debe hacer primero | Veredicto |
|---|---|---|
| **Ejecutable único** | Nada. Descargar un archivo y ejecutarlo. | ✅ Cumple Principio I |
| `npx …` (Node) | Instalar Node.js (instalador aparte, ~40 MB) | ❌ Prerequisito |
| `uvx …` (uv) | Instalar uv (comando de PowerShell que debe pegar) | ❌ Prerequisito, y uv es menos conocido que Node |
| `pip install …` | Instalar Python, entender PATH, entornos, `pip` | ❌ El peor para el público objetivo |

El ejecutable único es la **única** opción que satisface FR-009 y el
Principio I sin excepciones. Todo lo demás traslada al cliente un problema de
instalación que precisamente venimos a eliminar.

Elegido **Python** y no Node para construirlo, por tres razones concretas:

1. **Un solo stack en la organización** (constitución VI, heredada de mpbot):
   el servidor MCP, la app web y el pipeline de datos ya son Python. Node
   sería un segundo stack que mantener para un solo binario.
2. **Reuso directo de conocimiento y contrato**: el servidor usa el SDK
   oficial `mcp` de Python; el cliente usa el mismo SDK, del otro lado del
   protocolo. Los modos de falla (401/403/429, transporte streamable HTTP,
   protección anti DNS-rebinding) ya son terreno conocido del equipo.
3. **La ventaja de Node es irrelevante aquí**: `npx` es la lingua franca de
   los *ejemplos de configuración* de servidores MCP, pero eso solo importa
   si el usuario escribe la config a mano. En nuestro camino principal la
   config la escribe el conector, apuntando a la ruta del ejecutable — el
   usuario nunca ve `npx` ni lo necesita.

**Alternatives considered**:

- **Node + `npx`**: descartado por lo anterior. Se reevaluaría solo si
  apareciera evidencia de que una masa relevante de clientes ya tiene Node y
  prefiere el camino `npx`; en ese caso el port es aditivo, no un reemplazo.
- **Ambos stacks desde v1**: descartado por YAGNI (constitución VI): duplica
  superficie de mantención y de verificación en vivo antes de tener un solo
  cliente usándolo.
- **Interfaz gráfica (GUI) de instalación**: descartada para v1 — mucho más
  costosa de construir y verificar; un asistente de línea de comandos
  interactivo, lanzado desde un ejecutable, ya cumple SC-001. Queda como
  iteración futura si la evidencia de uso la pide.

**Riesgo asumido y cómo se mitiga** (honestidad requerida por el Principio I):
un `.exe` **sin firmar** dispara la advertencia de SmartScreen en Windows
("Windows protegió tu PC") y ocasionales falsos positivos de antivirus — una
pantalla roja que, para el público objetivo, es tan bloqueante como un error
técnico. Por lo tanto:

- La **firma de código** (certificado Authenticode) no es un lujo posterior:
  es parte del costo real de cumplir el Principio I y queda registrada como
  dependencia externa del plan (compra del certificado por el usuario).
- Mientras no exista firma, la documentación debe explicar la advertencia con
  honestidad y decir exactamente qué botón apretar; y esa limitación se
  declara abiertamente, no se esconde.

**Dependencia registrada con `mpbot/`** (no se construye acá): lo ideal es que
el ejecutable se descargue desde el propio producto, en la página donde el
cliente Empresa ya está autenticado sacando su API key (`/config` o `/docs`).
Eso exige una feature en `mpbot/` con su propio ciclo Spec Kit; acá solo se
deja anotada la dependencia (constitución, sección Governance).

---

## 2. Dónde se guarda la API key

**Decisión**: un único archivo de configuración propio del conector, en el
directorio de configuración de usuario del sistema operativo, con permisos
restringidos al dueño. La key **no** se copia a los archivos de configuración
de cada agente cuando existe alternativa; cuando el agente exige la
credencial en su propia config (conexión directa), se advierte explícitamente
al usuario antes de escribirla.

**Rationale**: Principio IV. Un solo lugar que proteger, rotar y revocar.
Evita el escenario real de tener la misma credencial repetida en tres
archivos distintos, alguno de ellos sincronizado a la nube o versionado por
error.

**Alternatives considered**:

- **Llavero del sistema operativo** (Windows Credential Manager, Keychain,
  Secret Service): más seguro, pero agrega una dependencia nativa por
  plataforma y complica el empaquetado en un solo binario. Registrado como
  mejora posterior, no como requisito de v1.
- **Solo variable de entorno**: descartado como mecanismo principal —
  configurar variables de entorno persistentes es exactamente el tipo de
  tarea que el Principio I prohíbe exigirle al cliente. Se soporta igual como
  vía secundaria para automatización.

---

## 3. Conexión directa vs. puente local: cuándo se usa cada uno

**Decisión**: el conector **prefiere la conexión directa** (el agente habla
HTTPS con `app.mpbot.cl` usando headers) cuando el agente la soporta, y usa
el **puente local** (el agente lanza el ejecutable por stdio) solo cuando (a)
el agente no admite headers propios, o (b) el usuario elige explícitamente no
dejar su key en la config del agente.

**Rationale**: Principio VII prohíbe ocultar el camino directo para
justificar el producto. Además, la conexión directa tiene menos piezas
móviles: sin proceso local intermedio, sin un salto extra de latencia, y sin
un binario que pueda quedar desactualizado respecto del servidor.

**Hallazgo que sustenta esta decisión** (y que corrigió una premisa falsa):
los tres agentes obligatorios de v1 soportan headers propios en servidores
MCP remotos:

- **Claude Code**: transporte HTTP con headers (config de proyecto/usuario).
- **Hermes**: `mcp_servers:` admite `url` + `headers` — está documentado
  textualmente en su propio `cli-config.yaml.example` instalado en este
  equipo: *"HTTP servers (connect to a URL): url: the MCP server endpoint /
  headers: HTTP headers (e.g., for authentication)"*.
- **OpenClaw**: `mcp.servers.<nombre>` con `transport: "streamable-http"` y
  bloque `headers` (documentación oficial).

Antes de este research se había afirmado lo contrario sobre Hermes, por
inferir de un único ejemplo de su config viva que no usaba headers. Era falso.
Ese error quedó codificado como el Principio II de la constitución.

**Consecuencia de alcance**: el puente deja de ser la pieza central del
producto y baja a US3 (P3). El MVP (US1) puede entregarse **sin** puente.

---

## 4. Perfiles de agente: formatos y estado de verificación

Formatos recopilados para el diseño. **Ninguno cuenta como compatible hasta
su verificación en vivo** (Principio II); esa verificación es una tarea
explícita del plan, no un supuesto.

| Agente | Forma de declarar un servidor MCP | ¿Headers propios? | Estado |
|---|---|---|---|
| Claude Code | Config JSON de proyecto/usuario; también comando dedicado para agregar servidores | Sí | ⏳ Por verificar en vivo |
| Claude Desktop | Config JSON de escritorio; históricamente orientada a servidores locales (stdio) | A confirmar | ⏳ Por verificar en vivo |
| Hermes | `mcp_servers:` en su YAML de configuración (`url` + `headers`, o `command`/`args`/`env`) | Sí (documentado en su propio ejemplo) | ⏳ Por verificar en vivo |
| OpenClaw | `mcp.servers.<nombre>` en su JSON (`url` + `transport` + `headers`, o `command`/`args`/`env`) | Sí (documentación oficial) | ⏳ Por verificar en vivo |
| OpenCode | Por confirmar | Por confirmar | ❌ Fuera de v1 (no instalado acá) |

**Decisión de diseño**: los perfiles de agente son **datos, no código**. Cada
perfil declara cómo detectar el agente, dónde vive su config, en qué formato
escribir la entrada, si admite conexión directa, y su fecha de verificación.
Agregar un agente nuevo es agregar un perfil, no modificar la lógica.

**Rationale**: es la única forma de que la superficie crezca (OpenCode y los
que vengan) sin reescribir el motor, y de que el estado de verificación viva
junto al dato que describe.

---

## 5. Detección de agentes instalados

**Decisión**: detectar por **presencia del archivo o directorio de
configuración del agente**, no por buscar su ejecutable en el PATH.

**Rationale**: un agente puede estar instalado de muchas formas (instalador,
gestor de paquetes, portable) pero siempre termina teniendo su directorio de
configuración en una ubicación conocida. Además, es lo que realmente importa:
lo que vamos a escribir es esa configuración.

**Caso borde ya identificado**: si el agente está instalado pero nunca se
ejecutó, puede que su config aún no exista. En ese caso se ofrece crearla,
advirtiendo que se está creando desde cero.

---

## 6. Estrategia de verificación en vivo (compuerta del Principio II)

**Decisión**: cada agente soportado se verifica con el mismo protocolo de
tres pasos, y el resultado (con fecha) se registra en la documentación y en
su perfil:

1. Configurar el agente con el conector (camino automático).
2. Desde el agente real, listar las tools de mpbot.
3. Ejecutar al menos una tool y comprobar que devuelve datos reales.

**Rationale**: listar tools prueba el handshake y la autenticación; ejecutar
una tool prueba el camino completo, incluido el manejo de respuesta. Sin el
paso 3, un servidor que autentica pero falla al ejecutar pasaría por
compatible.

**Nota operativa**: durante estas verificaciones se usa una API key real. Al
terminar la ronda de verificación, esa key se revoca desde `/config` de
mpbot — práctica ya aplicada en el proyecto hermano y que evita dejar
credenciales vivas de pruebas.
