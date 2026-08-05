# Quickstart: validar que el conector funciona

Cómo comprobar, de punta a punta, que lo construido cumple lo prometido.

**Prerrequisito de la validación**: una API key real de una cuenta con plan
Empresa. **Al terminar la ronda de validación, revocarla** desde
`app.mpbot.cl/config` (research §6).

---

## 1. Validar el camino del cliente final (US1)

En un equipo con al menos un agente soportado instalado:

```
mpbot-mcp instalar
```

**Debe ocurrir**:
- Lista los agentes que encontró y pide confirmación antes de tocar nada.
- Pide la key sin mostrarla en pantalla.
- Si la key es inválida, lo dice y **no escribe ningún archivo** — verificable
  comprobando que la config del agente quedó igual.
- Informa dónde dejó el respaldo de cada archivo modificado.
- Al terminar, informa cuántas tools quedaron disponibles.

**Idempotencia (SC-005)**: ejecutarlo dos veces seguidas debe dejar el archivo
del agente funcionalmente idéntico y sin perder otras entradas. Comprobar
comparando el archivo antes y después de la segunda corrida.

---

## 2. Validar el diagnóstico (US2)

```
mpbot-mcp doctor
```

Provocar cada modo de falla y confirmar que se distinguen entre sí (FR-011):

| Cómo provocarlo | Qué debe reportar |
|---|---|
| Key inexistente o revocada | Falla en *Autenticación*, con acción "generar una nueva" |
| Key de una cuenta sin plan Empresa | Falla en *Plan*, distinta de la anterior |
| Key con cuota agotada | Falla en *Cuota*, con cuántas van y cuándo se renueva |
| Sin red / con proxy que bloquea | Falla en *Conectividad*, **no** en credenciales |

**Verificación de seguridad (SC-004)**: en ninguna de esas salidas la key
debe aparecer completa. Comprobable de forma automatizada buscando la key
literal en toda la salida del comando.

---

## 3. Validar el puente (US3)

Configurar un agente (o el MCP Inspector) para lanzar `mpbot-mcp servir` como
programa local, **sin ninguna credencial en su configuración**.

**Debe ocurrir**:
- El agente lista las mismas tools que por conexión directa (SC-006).
- Al inspeccionar la config de ese agente, la API key **no** aparece.
- Un error de plan o cuota llega al agente como mensaje comprensible, no como
  falla muda.

---

## 4. Verificación en vivo por agente (compuerta del Principio II)

Para **cada** agente que se quiera declarar compatible, el protocolo de tres
pasos (research §6):

1. Configurarlo con `mpbot-mcp instalar`.
2. Desde el agente real, listar las tools de mpbot.
3. Ejecutar al menos una tool y comprobar que devuelve datos reales.

Registrar la fecha en el perfil del agente y en su receta de la
documentación. **Sin los tres pasos, el agente no se publica como
compatible.**

---

## 5. Suite automatizada

```
python -m pytest
```

Debe pasar completa **sin tocar producción y sin ninguna API key real**: el
servidor va simulado. Un test que necesite credenciales reales está mal
escrito y debe rediseñarse.
