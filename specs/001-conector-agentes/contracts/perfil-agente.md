# Contrato: perfil de agente

Un perfil describe **cómo tratar a un agente**. Es dato, no lógica: agregar
soporte a un agente nuevo es agregar un perfil, sin tocar el motor
(Principio VII).

## Lo que declara un perfil

Ver [data-model.md](../data-model.md) §2 para la forma exacta de los campos.
En resumen: identificador, nombre legible, dónde vive su configuración por
sistema operativo, formato del archivo, dónde anidar la entrada, si admite
conexión directa con headers, si admite lanzar un programa local, y **la
fecha de su última verificación en vivo**.

## Obligaciones de todo perfil

1. **Detectar sin ejecutar**: la detección se hace por presencia del archivo o
   directorio de configuración, nunca ejecutando el agente ni buscándolo en
   el PATH (research §5).
2. **Preservar lo ajeno**: escribir la entrada de mpbot sin alterar ninguna
   otra clave del archivo, incluidos otros servidores MCP de la persona
   (FR-006).
3. **Respaldar antes de escribir**: siempre que el archivo ya exista (FR-005).
4. **Ser idempotente**: aplicar dos veces deja el archivo funcionalmente
   idéntico (FR-007 / SC-005).
5. **Rutas absolutas**: toda ruta escrita en la config del agente se resuelve
   a absoluta; varios agentes rechazan rutas relativas o con `~`.
6. **Declarar su verificación**: sin fecha de verificación en vivo, el perfil
   **no** se presenta como compatible (Principio II).

## Dos formas de conectar

Un perfil declara cuál o cuáles admite:

**Conexión directa** — el agente habla HTTPS con mpbot usando headers
propios. Preferida cuando está disponible (research §3). Implica que la API
key queda escrita en la configuración de ese agente: el conector **debe
advertirlo explícitamente antes de escribirla** (Principio IV).

**Programa local (stdio)** — el agente lanza `mpbot-mcp servir`. La key no
aparece en la configuración del agente: la toma el conector de su propio
almacenamiento (FR-015). Obligatoria para agentes sin soporte de headers.

## Estado de los perfiles de v1

Todos parten **sin verificar**. Ninguno puede anunciarse como compatible
hasta completar el protocolo de 3 pasos de research §6 (configurar → listar
tools → ejecutar una tool con datos reales) y registrar la fecha.

| Perfil | Conexión prevista | Estado |
|---|---|---|
| `claude-code` | Directa | ⏳ Por verificar |
| `claude-desktop` | Por confirmar en la verificación | ⏳ Por verificar |
| `hermes` | Directa | ⏳ Por verificar |
| `openclaw` | Directa | ⏳ Por verificar |

`opencode` queda fuera de v1 por no estar instalado en el equipo de
desarrollo: no se puede verificar y, por lo tanto, no se puede publicar
(Principio II). Se agrega cuando haya cómo probarlo.

## Regla de crecimiento

Agregar un agente = agregar un módulo de perfil + sus tests + su verificación
en vivo + su receta en la documentación. Si agregar un agente obliga a
modificar el motor, el motor está mal diseñado y se corrige ahí, no en el
perfil.
