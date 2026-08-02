# Data Model: Conector mpbot-mcp

Cuatro entidades. Ninguna almacena datos de mercado (Principio III): el
contenido de negocio se transporta, nunca se persiste.

## 1. ConfiguracionConector

Lo único que el conector persiste. Un archivo por equipo, en el directorio de
configuración del usuario, con permisos restringidos al dueño.

| Campo | Tipo | Notas |
|---|---|---|
| `api_key` | texto (secreto) | `mpb_…`. Nunca se imprime completa (FR-012) |
| `url_servidor` | texto | Por defecto el endpoint de producción; sobreescribible para desarrollo |
| `creada_en` | fecha-hora | Para poder decirle al usuario desde cuándo está configurado |
| `ultima_verificacion` | fecha-hora \| nulo | Cuándo se comprobó por última vez que la conexión servía |

**Reglas**:
- Al escribirse, el archivo queda con permisos de solo-dueño.
- Al leerse para mostrar, `api_key` se enmascara siempre (`mpb_2f5…`).
- La key puede venir también del entorno; el entorno tiene precedencia sobre
  el archivo, para permitir automatización sin tocar el archivo.

## 2. PerfilAgente

Describe **cómo tratar a un agente**. Es dato, no lógica: agregar un agente
es agregar un perfil.

| Campo | Tipo | Notas |
|---|---|---|
| `id` | texto | Identificador estable (`claude-code`, `hermes`, …) |
| `nombre` | texto | Nombre legible para mostrarle a la persona |
| `rutas_config` | lista de rutas | Dónde vive su configuración, por sistema operativo |
| `formato` | enum | `json` \| `yaml` — cómo se lee y escribe su archivo |
| `ruta_en_archivo` | lista de claves | Dónde anidar la entrada (ej. `mcp` → `servers`) |
| `soporta_directo` | booleano | Si admite servidor remoto con headers propios |
| `soporta_stdio` | booleano | Si admite lanzar un programa local |
| `verificado_en` | fecha \| nulo | **Nulo = no verificado**: no se lista como compatible (Principio II) |

**Reglas**:
- Un perfil con `verificado_en` nulo puede existir en el código, pero la
  interfaz y la documentación deben mostrarlo como no verificado.
- `soporta_directo` falso obliga a usar el modo puente para ese agente.
- Las rutas se resuelven siempre a absolutas antes de escribirse en la config
  del agente (varios agentes rechazan rutas relativas o con `~`).

## 3. ReporteDiagnostico

Resultado del comando `doctor`. Existe solo en memoria y en la salida.

| Campo | Tipo | Notas |
|---|---|---|
| `pasos` | lista de `PasoDiagnostico` | En orden de ejecución |
| `todo_ok` | booleano | Verdadero solo si ningún paso falló |

### PasoDiagnostico

| Campo | Tipo | Notas |
|---|---|---|
| `nombre` | texto | Ej. "Conectividad con el servidor" |
| `estado` | enum | `ok` \| `falla` \| `omitido` |
| `detalle` | texto | Qué se observó, en lenguaje llano |
| `accion` | texto \| nulo | Qué hacer para arreglarlo; nulo si `ok` |

**Orden fijo de los pasos** (FR-010): key presente → conectividad →
autenticación → plan → cuota → tools disponibles → configuración de agentes
detectados.

**Regla**: un paso que falla no aborta el reporte; los siguientes se marcan
`omitido` con su motivo. Así la persona ve el cuadro completo de una sola vez
en lugar de arreglar-reintentar-arreglar.

## 4. RespaldoConfig

Copia de seguridad de la configuración de un agente antes de modificarla.

| Campo | Tipo | Notas |
|---|---|---|
| `ruta_original` | ruta | Archivo que se va a modificar |
| `ruta_respaldo` | ruta | Copia con marca de tiempo en el nombre |
| `creado_en` | fecha-hora | |

**Reglas**:
- Se crea **antes** de cualquier escritura sobre un archivo preexistente
  (FR-005) y su ubicación se le informa a la persona.
- Nunca se sobrescribe un respaldo anterior: la marca de tiempo lo evita.

---

## Lo que este modelo deliberadamente NO tiene

- **Ninguna entidad de negocio** (rubro, cotización, proveedor, tool): eso
  vive en el servidor y solo pasa de largo (Principio III).
- **Ningún catálogo de tools**: se descubre por protocolo en cada sesión; una
  lista propia se desactualizaría sola (lección heredada de `mpbot`).
- **Ninguna caché de respuestas**: agregaría el riesgo de mostrar datos de
  mercado obsoletos sin que el usuario lo sepa, contradiciendo la regla de
  mpbot de declarar siempre el período de corte.
- **Ningún registro de uso ni telemetría** (FR-023).
