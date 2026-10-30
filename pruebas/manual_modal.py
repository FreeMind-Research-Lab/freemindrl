"""Prueba manual contra un despliegue de OrionOne API (por ejemplo, el de
prueba en Modal). No corre con las demás: la dirección y la llave las da
quien la corre, en variables de entorno.

    ORIONONE_URL=<dirección del despliegue> ORIONONE_LLAVE=<llave> python pruebas/manual_modal.py

La primera respuesta puede tardar: el contenedor se apaga sin uso y arranca
con el primer pedido. Con esperar, el cliente consulta GET /salud hasta que
el modelo está cargado.
"""

from __future__ import annotations

import os
import sys
import time

from freemindrl import ErrorDeFreeMind, OrionOne


def main() -> int:
    url, key = os.environ.get("ORIONONE_URL"), os.environ.get("ORIONONE_LLAVE")
    if not (url and key):
        print("Faltan ORIONONE_URL y ORIONONE_LLAVE.")
        return 2
    cliente = OrionOne(llave=key, url=url, esperar=600)
    try:
        start = time.monotonic()
        cliente.esperar_listo(600)
        print(f"listo ({time.monotonic() - start:.1f} s)")
        start = time.monotonic()
        r = cliente.responder("¿Cuál es la capital de Colombia?", modelo="O.1-T", pensamiento="apagado")
        print(f"completa ({time.monotonic() - start:.1f} s): {r.texto!r}")
        print(f"  motivo {r.motivo}, {r.fin.get('tokens_generados')} tokens, commit {r.fin.get('commit', '')[:12]}, "
              f"pesos {r.fin.get('pesos_sha256', '')[:16]}")
        print("en vivo: ", end="", flush=True)
        for event in cliente.responder("Di hola en una frase.", modelo="O.1-T", pensamiento="apagado", en_vivo=True):
            if event.tipo == "texto":
                print(event.texto, end="", flush=True)
        print()
    except ErrorDeFreeMind as error:
        print(f"{type(error).__name__}: {error}")
        return 1
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
