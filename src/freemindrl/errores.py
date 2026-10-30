"""Los errores del SDK. Todos heredan de ErrorDeFreeMind."""

from __future__ import annotations


class ErrorDeFreeMind(Exception):
    """Algo no salió. estado es el código HTTP, si lo hubo; codigo y mensaje
    son los que dio el servidor."""

    def __init__(self, mensaje: str, codigo: str | None = None, estado: int | None = None):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo = codigo
        self.estado = estado


class LlaveInvalida(ErrorDeFreeMind):
    """Sin llave, o la llave no es válida o fue revocada (401)."""


class ModeloNoDisponible(ErrorDeFreeMind):
    """El servidor no sirve ese modelo."""


class PedidoInvalido(ErrorDeFreeMind):
    """El servidor rechazó el pedido; mensaje dice por qué."""


class Desconexion(ErrorDeFreeMind):
    """No se pudo conectar, o la conexión se cortó antes del fin de la respuesta."""


class ErrorDelServidor(ErrorDeFreeMind):
    """El servidor falló: un 5xx, o un evento de error a mitad de la respuesta."""


class EventoDesconocido(ErrorDeFreeMind):
    """El servidor mandó un evento que esta versión del SDK no conoce: hay que
    actualizar el SDK. No se ignora, para no perder parte de la respuesta."""
