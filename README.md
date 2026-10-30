# freemindrl

El SDK de FreeMind Research Lab. Hoy trae el cliente de **OrionOne API**, la
entrada a OrionOne, la familia de modelos de FreeMind. Origin y Juno entrarán
al mismo paquete.

**Versión 0.1.0, mínima y sin publicar.** Envuelve la versión 0 de OrionOne
API. El paquete `freemindrl` 0.0.1 que hay en PyPI solo reserva el nombre.

Solo biblioteca estándar de Python, 3.10 o más reciente.

## Uso

La llave y la dirección del servidor se pasan siempre explícitas. La llave se
lee de una variable de entorno: nunca va escrita en el código. El SDK no trae
ninguna dirección fija; la dirección por defecto se decidirá cuando exista el
servidor definitivo de OrionOne.

```python
import os
from freemindrl import OrionOne

cliente = OrionOne(llave=os.environ["ORIONONE_LLAVE"], url=os.environ["ORIONONE_URL"])

respuesta = cliente.responder("¿Cuál es la capital de Colombia?", modelo="O.1-T", pensamiento=False)
print(respuesta.texto)
print(respuesta.motivo, respuesta.fin["tokens_generados"])
```

En vivo, evento por evento:

```python
for evento in cliente.responder("Cuéntame algo de Bogotá.", modelo="O.1-T", pensamiento=False, en_vivo=True):
    if evento.tipo == "texto":
        print(evento.texto, end="", flush=True)
```

Si dejas de recorrer los eventos, la conexión se cierra y el servidor deja de
generar.

### Servidores que se apagan sin uso

Un servidor que se apaga cuando nadie lo usa arranca con el primer pedido, y
mientras carga el modelo responde 503. Con `esperar`, el primer pedido
consulta `GET /salud` hasta que el servidor está listo, durante a lo sumo esos
segundos:

```python
cliente = OrionOne(llave=os.environ["ORIONONE_LLAVE"], url=os.environ["ORIONONE_URL"], esperar=600)
```

`cliente.salud()` dice si el servidor está listo, y `cliente.esperar_listo(segundos)`
espera a que lo esté. Si no lo está a tiempo, `Desconexion`.

### Parámetros de `responder`

| Parámetro | Qué es |
| --- | --- |
| `mensajes` | Un texto (un turno del usuario) o la lista de turnos `{"role", "content"}` |
| `modelo` | El código de la familia. Hoy la API sirve `O.1-T` |
| `pensamiento` | Obligatorio, `True` o `False`: el SDK no elige por ti |
| `estilo` | Un perfil de OrionOne Style, o el nombre de uno guardado |
| `contrato` | Un JSON Schema: la respuesta lo cumple por construcción |
| `semilla`, `tope`, `sesion` | Semilla del muestreo, máximo de tokens y conversación |
| `en_vivo` | `True` para recibir los eventos a medida que llegan |

### Eventos

Solo los que OrionOne API emite hoy:

| Evento | Qué lleva |
| --- | --- |
| `pensando` | Un trozo del pensamiento, si se pidió |
| `texto` | Un trozo de la respuesta |
| `fin` | Motivo, tokens, semilla, sha256 de los pesos, commit del código y huellas del estilo y del contrato |

Un evento que esta versión no conoce no se ignora: levanta `EventoDesconocido`.

### Errores

Todos heredan de `ErrorDeFreeMind`, con `estado` (HTTP), `codigo` y `mensaje`.

| Error | Cuándo |
| --- | --- |
| `LlaveInvalida` | Sin llave, o la llave no es válida o fue revocada |
| `ModeloNoDisponible` | El servidor no sirve ese modelo |
| `PedidoInvalido` | El servidor rechazó el pedido; `mensaje` dice por qué |
| `Desconexion` | No se pudo conectar, o la conexión se cortó antes del fin |
| `ErrorDelServidor` | El servidor falló |
| `EventoDesconocido` | El servidor mandó un evento que esta versión no conoce |

## Pruebas

```bash
pip install -e .
```

```bash
python -m unittest discover -s pruebas -t .
```

Las pruebas contra la API se corren con OrionOne API levantada en la máquina
(repositorio OrionOne, `python orionone.py servir`) y las variables
`ORIONONE_URL` y `ORIONONE_LLAVE`; sin ellas se omiten y lo dicen.
`pruebas/manual_modal.py` es una prueba manual contra un despliegue.

## Licencia

Apache 2.0. Ver [LICENSE](LICENSE).
