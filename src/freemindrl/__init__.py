"""freemindrl: el SDK de FreeMind Research Lab.

Hoy trae el cliente de OrionOne API. Origin y Juno entrarán al mismo paquete.
"""

from freemindrl.errores import (Desconexion, ErrorDeFreeMind, ErrorDelServidor, EventoDesconocido,
                                LlaveInvalida, ModeloNoDisponible, PedidoInvalido)
from freemindrl.orionone import EVENTOS, Evento, OrionOne, Respuesta

__version__ = "0.1.0"

__all__ = ["OrionOne", "Respuesta", "Evento", "EVENTOS", "ErrorDeFreeMind", "LlaveInvalida", "ModeloNoDisponible",
           "PedidoInvalido", "Desconexion", "ErrorDelServidor", "EventoDesconocido"]
