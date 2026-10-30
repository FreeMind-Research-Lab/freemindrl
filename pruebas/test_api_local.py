"""Pruebas contra OrionOne API corriendo en esta máquina.

Con el repositorio OrionOne:

    python orionone.py llaves crear --nombre sdk
    python orionone.py servir --modelo O.1-T --pesos <carpeta>

y aquí, con la llave en una variable de entorno, nunca en el código:

    ORIONONE_URL=http://127.0.0.1:8765 ORIONONE_LLAVE=<llave> python -m unittest discover -s pruebas -t .

Sin esas variables, estas pruebas se omiten y lo dicen.
"""

from __future__ import annotations

import json
import os
import unittest

from freemindrl import EVENTOS, Evento, LlaveInvalida, ModeloNoDisponible, OrionOne, PedidoInvalido, Respuesta

URL = os.environ.get("ORIONONE_URL")
LLAVE = os.environ.get("ORIONONE_LLAVE")
PREGUNTA = "¿Cuál es la capital de Colombia?"


@unittest.skipUnless(URL and LLAVE, "sin ORIONONE_URL y ORIONONE_LLAVE: no hay API contra la cual probar")
class ContraLaAPI(unittest.TestCase):
    def setUp(self):
        self.cliente = OrionOne(llave=LLAVE, url=URL)

    def test_respuesta_completa(self):
        r = self.cliente.responder(PREGUNTA, modelo="O.1-T", pensamiento="apagado", tope=64)
        self.assertIsInstance(r, Respuesta)
        self.assertTrue(r.texto)
        self.assertIn(r.motivo, ("fin", "tope"))
        for name in ("tokens_generados", "pesos_sha256", "commit", "huella_estilo", "modelo"):
            self.assertIn(name, r.fin)

    def test_en_vivo_da_lo_mismo(self):
        whole = self.cliente.responder(PREGUNTA, modelo="O.1-T", pensamiento="apagado", tope=64)
        events = list(self.cliente.responder(PREGUNTA, modelo="O.1-T", pensamiento="apagado", tope=64, en_vivo=True))
        self.assertTrue(all(isinstance(e, Evento) and e.tipo in EVENTOS for e in events))
        self.assertEqual(events[-1].tipo, "fin")
        self.assertEqual("".join(e.texto for e in events if e.tipo == "texto"), whole.texto)  # greedy
        self.assertEqual(events[-1].datos["tokens_generados"], whole.fin["tokens_generados"])

    def test_dejar_de_leer_no_traba_el_servidor(self):
        stream = self.cliente.responder("Escribe un cuento largo.", modelo="O.1-T", pensamiento="apagado", tope=1000,
                                        en_vivo=True)
        first = next(stream)
        self.assertIn(first.tipo, EVENTOS)
        stream.close()
        r = self.cliente.responder(PREGUNTA, modelo="O.1-T", pensamiento="apagado", tope=16)
        self.assertTrue(r.texto)

    def test_salud_y_esperar(self):
        self.assertTrue(self.cliente.salud())
        cliente = OrionOne(llave=LLAVE, url=URL, esperar=30)
        r = cliente.responder(PREGUNTA, modelo="O.1-T", pensamiento="apagado", tope=16)
        self.assertTrue(r.texto)

    def test_niveles(self):
        r = self.cliente.responder(PREGUNTA, modelo="O.1-T", pensamiento="bajo", tope=32)
        self.assertEqual(r.fin["pensamiento"], {"nivel": "bajo", "techo": 256})
        for level in ("ultra", "automatico"):
            with self.assertRaises(PedidoInvalido) as caught:
                self.cliente.responder(PREGUNTA, modelo="O.1-T", pensamiento=level)
            self.assertEqual(caught.exception.codigo, "pensamiento_no_disponible")

    def test_pensamiento_con_presupuesto(self):
        events = list(self.cliente.responder(PREGUNTA, modelo="O.1-T", presupuesto=16, tope=96, en_vivo=True))
        kinds = [e.tipo for e in events]
        self.assertIn("pensando", kinds)
        self.assertEqual(kinds[-1], "fin")
        self.assertTrue("".join(e.texto for e in events if e.tipo == "texto").strip(), "sin respuesta tras pensar")

    def test_llave_invalida(self):
        with self.assertRaises(LlaveInvalida) as caught:
            OrionOne(llave="oo_no-es-una-llave", url=URL).responder(PREGUNTA, modelo="O.1-T", pensamiento="apagado")
        self.assertEqual(caught.exception.estado, 401)

    def test_modelo_no_disponible(self):
        with self.assertRaises(ModeloNoDisponible):
            self.cliente.responder(PREGUNTA, modelo="O.1", pensamiento="apagado")

    def test_pedido_invalido_dice_por_que(self):
        with self.assertRaises(PedidoInvalido) as caught:
            self.cliente.responder(PREGUNTA, modelo="O.1-T", pensamiento="apagado", tope=10**6)
        self.assertTrue(caught.exception.mensaje)

    def test_contrato(self):
        schema = {"type": "object", "properties": {"capital": {"type": "string", "maxLength": 40}},
                  "required": ["capital"], "additionalProperties": False}
        r = self.cliente.responder(PREGUNTA + " Responde solo con un objeto JSON.", modelo="O.1-T",
                                   pensamiento="apagado", contrato=schema, tope=64)
        data = json.loads(r.texto)
        self.assertEqual(set(data), {"capital"})
        self.assertTrue(r.fin.get("huella_contrato"))


if __name__ == "__main__":
    unittest.main()
