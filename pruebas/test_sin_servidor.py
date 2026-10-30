"""Lo que se comprueba sin servidor.

    python -m unittest discover -s pruebas -t .
"""

from __future__ import annotations

import re
import socket
import unittest
from pathlib import Path

from freemindrl import Desconexion, OrionOne

PAQUETE = Path(__file__).resolve().parents[1] / "src" / "freemindrl"
RAIZ = Path(__file__).resolve().parents[1]


class SinServidor(unittest.TestCase):
    def test_exige_llave_y_url(self):
        for llave, url in ((None, "https://servidor"), ("", "https://servidor"), ("x", None), ("x", ""),
                           ("x", "servidor-sin-esquema")):
            with self.assertRaises(ValueError):
                OrionOne(llave=llave, url=url)

    def test_la_llave_no_se_muestra(self):
        cliente = OrionOne(llave="secreto-de-prueba", url="https://servidor")
        self.assertNotIn("secreto-de-prueba", repr(cliente))

    def test_ni_llaves_ni_direcciones_fijas(self):
        # Condición del repositorio: ninguna llave ni dirección de un servidor
        # en el código, los ejemplos o las pruebas.
        files = [p for p in RAIZ.rglob("*") if p.is_file() and p.suffix in (".py", ".md", ".toml")
                 and ".git" not in p.parts]
        for path in files:
            text = path.read_text(encoding="utf-8")
            self.assertNotRegex(text, r"oo_[A-Za-z0-9_-]{20,}", f"{path.name} parece tener una llave")
            self.assertNotRegex(text, r"\.modal\.run|modal\.com/apps", f"{path.name} tiene una dirección fija")
            self.assertIsNone(re.search(r"https?://(?!servidor\b|localhost\b|127\.0\.0\.1\b|www\.apache\.org"
                                        r"|github\.com/FreeMind-Research-Lab)", text),
                              f"{path.name} tiene una dirección que no es de ejemplo")

    def test_sin_servidor_es_desconexion(self):
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        cliente = OrionOne(llave="x", url=f"http://127.0.0.1:{port}", tiempo_maximo=5)
        with self.assertRaises(Desconexion):
            cliente.responder("Hola", modelo="O.1-T", pensamiento=False)

    def test_esperar_sin_servidor_es_desconexion(self):
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        cliente = OrionOne(llave="x", url=f"http://127.0.0.1:{port}", esperar=1)
        self.assertFalse(cliente.salud())
        with self.assertRaises(Desconexion) as caught:
            cliente.responder("Hola", modelo="O.1-T", pensamiento=False)
        self.assertIn("/salud", str(caught.exception))

    def test_pensamiento_obligatorio(self):
        cliente = OrionOne(llave="x", url="http://127.0.0.1:9")
        with self.assertRaises(TypeError):
            cliente.responder("Hola", modelo="O.1-T")
        with self.assertRaises(ValueError):
            cliente.responder("Hola", modelo="O.1-T", pensamiento="no")
        with self.assertRaises(ValueError):
            cliente.responder("Hola", modelo="O.1-T", pensamiento=True)
        with self.assertRaises(ValueError):
            cliente.responder("Hola", modelo="O.1-T", pensamiento=False, presupuesto=8)


if __name__ == "__main__":
    unittest.main()
