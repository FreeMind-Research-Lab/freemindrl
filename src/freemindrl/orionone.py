"""El cliente de OrionOne API (protocolo propio, POST /v1/responder).

    import os
    from freemindrl import OrionOne

    cliente = OrionOne(llave=os.environ["ORIONONE_LLAVE"], url=os.environ["ORIONONE_URL"])
    respuesta = cliente.responder("¿Cuál es la capital de Colombia?", modelo="O.1-T", pensamiento="apagado")
    print(respuesta.texto)

La llave y la dirección se pasan siempre explícitas: el SDK no trae ninguna
fija. La dirección por defecto se decide cuando exista el servidor definitivo.

Solo biblioteca estándar.
"""

from __future__ import annotations

import http.client
import json
import socket
import time
from dataclasses import dataclass, field
from typing import Iterator
from urllib.parse import urlparse

from freemindrl.errores import (Desconexion, ErrorDeFreeMind, ErrorDelServidor, EventoDesconocido,
                                LlaveInvalida, ModeloNoDisponible, PedidoInvalido)

#: Los eventos que OrionOne API emite hoy. cita, herramienta_propuesta y
#: no_se están en el diseño de la API pero no se emiten: aquí no existen.
EVENTOS = ("pensando", "texto", "fin")


@dataclass(frozen=True)
class Evento:
    """Un evento de la respuesta en vivo. En pensando y texto, datos["texto"]
    es el trozo nuevo; en fin, datos son los datos de la respuesta."""

    tipo: str
    datos: dict

    @property
    def texto(self) -> str:
        return self.datos.get("texto", "")


@dataclass(frozen=True)
class Respuesta:
    """La respuesta completa. fin trae motivo, tokens, semilla, el sha256 de
    los pesos, el commit del código y las huellas del estilo y del contrato."""

    texto: str
    pensamiento: str
    fin: dict = field(default_factory=dict)

    @property
    def motivo(self) -> str:
        """fin si el modelo terminó; tope si llegó al máximo de tokens."""
        return self.fin.get("motivo", "")


def _pensamiento(nivel, presupuesto):
    """Lo que va en el campo pensamiento del pedido."""
    if presupuesto is not None:
        if nivel not in (None, True):
            raise ValueError("pasa un nivel de pensamiento o un presupuesto, no los dos")
        if not isinstance(presupuesto, int) or isinstance(presupuesto, bool) or presupuesto < 0:
            raise ValueError("el presupuesto es un entero >= 0")
        return {"presupuesto": presupuesto}
    if nivel is None or nivel is True:
        raise ValueError('falta cuánto pensar: pensamiento="apagado", "bajo", "medio" o "alto", o presupuesto=N')
    if nivel is False:
        return "apagado"
    if not isinstance(nivel, str):
        raise ValueError("pensamiento es un nivel: apagado, bajo, medio o alto")
    return nivel


def _error(status: int, body: bytes) -> ErrorDeFreeMind:
    try:
        error = json.loads(body.decode("utf-8")).get("error", {})
        code, message = error.get("codigo"), error.get("mensaje") or ""
    except (ValueError, AttributeError):
        code, message = None, body.decode("utf-8", errors="replace")[:500]
    message = message or f"el servidor respondió {status}"
    if status == 401:
        return LlaveInvalida(message, code, status)
    if code == "modelo_no_disponible":
        return ModeloNoDisponible(message, code, status)
    if status >= 500:
        return ErrorDelServidor(message, code, status)
    return PedidoInvalido(message, code, status)


class OrionOne:
    """Cliente de OrionOne API.

    llave: la llave de acceso, leída de donde la guardes (una variable de
    entorno, por ejemplo); nunca escrita en el código.
    url: la dirección del servidor, sin la ruta (https://servidor).
    esperar: si se da, segundos que el primer pedido espera a que el
    servidor esté listo (GET /salud en 200). Sirve con un servidor que se
    apaga sin uso y arranca con el primer pedido.
    """

    def __init__(self, llave: str, url: str, tiempo_maximo: float = 600, esperar: float | None = None):
        if not llave or not isinstance(llave, str):
            raise ValueError("falta la llave: pásala desde una variable de entorno, nunca escrita en el código")
        parts = urlparse(url or "")
        if parts.scheme not in ("http", "https") or not parts.hostname:
            raise ValueError("falta la dirección del servidor, con su esquema: url='https://servidor'")
        self._llave = llave
        self._parts = parts
        self._base = parts.path.rstrip("/")
        self.url = url
        self.tiempo_maximo = tiempo_maximo
        self.esperar = esperar
        self._ready = False

    def __repr__(self) -> str:
        return f"OrionOne(url={self.url!r})"      # sin la llave

    def salud(self) -> bool:
        """Si el servidor está listo: GET /salud responde 200. Mientras carga
        responde 503; un servidor que todavía arranca puede no responder."""
        conn = self._connection(min(self.tiempo_maximo, 160))
        try:
            conn.request("GET", f"{self._base}/salud")
            return conn.getresponse().status == 200
        except (OSError, http.client.HTTPException):
            return False
        finally:
            conn.close()

    def esperar_listo(self, segundos: float, cada: float = 5) -> None:
        """Consulta /salud hasta el 200. Si no llega en `segundos`, Desconexion."""
        start = time.monotonic()
        while not self.salud():
            if time.monotonic() - start + cada > segundos:
                raise Desconexion(f"{self.url} no estuvo listo en {segundos:g} s (GET /salud sin 200)")
            time.sleep(cada)
        self._ready = True

    def responder(self, mensajes, *, modelo: str, pensamiento=None, presupuesto: int | None = None, estilo=None,
                  contrato: dict | None = None, semilla: int | None = None, tope: int | None = None,
                  sesion: str | None = None, en_vivo: bool = False):
        """Pide una respuesta.

        mensajes: un texto (un turno del usuario) o la lista de turnos
        [{"role": "user" | "assistant", "content": "..."}].
        modelo: el código de la familia, por ejemplo "O.1-T".
        pensamiento: cuánto piensa el modelo antes de responder, un nivel de
        OrionOne Think: "apagado", "bajo", "medio" o "alto" (False es
        "apagado"). "ultra" y "automatico" existen en el diseño y el servidor
        los rechaza: no están disponibles aún. Obligatorio, salvo que se pase
        presupuesto: la API no elige por ti.
        presupuesto: en vez de un nivel, un techo exacto de tokens pensando;
        al llegar, el servidor cierra el pensamiento y fuerza la respuesta.
        tope es el máximo de la respuesta; el pensamiento va aparte.
        estilo: un perfil de OrionOne Style (dict) o el nombre de uno guardado.
        contrato: un JSON Schema que la respuesta cumple por construcción.

        Devuelve una Respuesta. Con en_vivo=True, un iterador de Evento; si
        dejas de recorrerlo, la conexión se cierra y el servidor deja de
        generar.
        """
        if isinstance(mensajes, str):
            mensajes = [{"role": "user", "content": mensajes}]
        body = {"modelo": modelo, "mensajes": list(mensajes),
                "pensamiento": _pensamiento(pensamiento, presupuesto)}
        for name, value in (("estilo", estilo), ("contrato", contrato), ("semilla", semilla),
                            ("tope", tope), ("sesion", sesion)):
            if value is not None:
                body[name] = value
        if self.esperar is not None and not self._ready:
            self.esperar_listo(self.esperar)
        events = self._eventos(body)
        if en_vivo:
            return events
        parts = {"texto": [], "pensando": []}
        end = {}
        for event in events:
            if event.tipo == "fin":
                end = event.datos
            else:
                parts[event.tipo].append(event.texto)
        return Respuesta("".join(parts["texto"]), "".join(parts["pensando"]), end)

    # --- HTTP y SSE ----------------------------------------------------------

    def _connection(self, timeout: float):
        kind = http.client.HTTPSConnection if self._parts.scheme == "https" else http.client.HTTPConnection
        return kind(self._parts.hostname, self._parts.port, timeout=timeout)

    def _eventos(self, body: dict) -> Iterator[Evento]:
        conn = self._connection(self.tiempo_maximo)
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self._llave}",
                   "Accept": "text/event-stream"}
        try:
            conn.request("POST", f"{self._base}/v1/responder", body=json.dumps(body).encode("utf-8"), headers=headers)
            response = conn.getresponse()
        except (OSError, http.client.HTTPException) as error:
            conn.close()
            raise Desconexion(f"no se pudo conectar con {self.url}: {error}") from error
        if response.status != 200:
            data = response.read()
            conn.close()
            raise _error(response.status, data)
        return self._leer(conn, response)

    def _leer(self, conn, response) -> Iterator[Evento]:
        finished = False
        try:
            block = {}
            while True:
                try:
                    line = response.readline()
                except (OSError, socket.timeout, http.client.HTTPException) as error:
                    raise Desconexion(f"la conexión se cortó a mitad de la respuesta: {error}") from error
                if not line:
                    break
                line = line.decode("utf-8").rstrip("\r\n")
                if line:
                    name, _, value = line.partition(": ")
                    block[name] = value
                    continue
                if "event" not in block:
                    continue
                kind, data = block["event"], json.loads(block.get("data") or "{}")
                block = {}
                if kind == "error":
                    raise ErrorDelServidor(data.get("mensaje", "error a mitad de la respuesta"), data.get("codigo"))
                if kind not in EVENTOS:
                    raise EventoDesconocido(f"evento {kind!r}: esta versión del SDK no lo conoce; actualízala")
                yield Evento(kind, data)
                if kind == "fin":
                    finished = True
                    return
            if not finished:
                raise Desconexion("la respuesta terminó sin su evento fin")
        finally:
            # También si quien recorre deja de hacerlo: cerrar avisa al servidor.
            conn.close()
