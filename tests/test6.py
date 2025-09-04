import unittest
import os
import random
import asyncio
from tcputils import *
from tcp import Servidor

from tests.common import *

class TestStep6(unittest.IsolatedAsyncioTestCase):
    async def test_step6(self):
        recebido = b''
        def dados_recebidos(c, dados):
            nonlocal recebido
            recebido += dados

        conexao = None
        def conexao_aceita(c):
            nonlocal conexao
            conexao = c
            c.registrar_recebedor(dados_recebidos)

        rede = CamadaRede()
        dst_port = gerar_porta_servidor()
        servidor = Servidor(rede, dst_port)
        servidor.registrar_monitor_de_conexoes_aceitas(conexao_aceita)

        src_port = gerar_porta_cliente()
        seq_no = gerar_seq_no()
        src_addr, dst_addr = gerar_enderecos_teste6()
        rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no, 0, FLAGS_SYN), src_addr, dst_addr))
        segmento, _ = rede.fila[0]
        _, _, ack_no, ack, flags, _, _, _ = read_header(segmento)
        self.assertEqual(4*(flags>>12), len(segmento), msg="O SYN+ACK não deveria ter payload")
        self.assertTrue((flags & FLAGS_ACK) == FLAGS_ACK, msg="O SYN+ACK deve ter flag ACK")
        rede.fila.clear()

        seq_no += 1
        ack_no += 1
        self.assertEqual(ack, seq_no, msg="ACK do SYN+ACK deve ser seq_no+1")

        rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no, ack_no, FLAGS_ACK), src_addr, dst_addr))
        rede.fila.clear()

        payload = os.urandom(MSS)
        conexao.enviar(payload)
        self.assertEqual(len(rede.fila), 1, msg="Enviar payload deve gerar exatamente um segmento")

        await asyncio.sleep(0.1)

        while len(rede.fila) > 0:
            segmento, _ = rede.fila.pop(0)
            _, _, seq, ack, flags, _, _, _ = read_header(segmento)
            self.assertEqual(seq, ack_no, msg="Seq do segmento enviado deve ser ack_no")
            self.assertTrue((flags & FLAGS_ACK) == FLAGS_ACK, msg="Flag ACK esperada")
            self.assertEqual(ack, seq_no, msg="ACK deve corresponder ao seq_no do cliente")
            self.assertEqual(segmento[4*(flags>>12):], payload, msg="Payload enviado não corresponde")

        ack_no += MSS
        rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no, ack_no, FLAGS_ACK), src_addr, dst_addr))

        payload = os.urandom(MSS)
        conexao.enviar(payload)
        self.assertEqual(len(rede.fila), 1, msg="Enviar payload deve gerar exatamente um segmento (2)")
        rede.fila.clear()  # descarta

        # sample_rtt = 0.1
        await asyncio.sleep(0.29)
        self.assertEqual(len(rede.fila), 0, msg="Não deveria ter retransmitido ainda")
        await asyncio.sleep(0.02)
        self.assertEqual(len(rede.fila), 1, msg="Já deveria ter retransmitido")

        segmento, _ = rede.fila.pop(0)
        _, _, seq, ack, flags, _, _, _ = read_header(segmento)
        self.assertEqual(seq, ack_no, msg="Seq do retransmit deve ser ack_no")
        self.assertTrue((flags & FLAGS_ACK) == FLAGS_ACK, msg="Retransmit deve ter flag ACK")
        self.assertEqual(ack, seq_no, msg="ACK do retransmit deve corresponder ao seq_no do cliente")

        # Verifica se o tempo de segmentos retransmitidos está sendo ignorado
        await asyncio.sleep(2)
        rede.fila.clear()
        ack_no += MSS
        rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no, ack_no, FLAGS_ACK), src_addr, dst_addr))
        payload = os.urandom(MSS)
        conexao.enviar(payload)
        self.assertEqual(len(rede.fila), 1, msg="Enviar payload deve gerar exatamente um segmento (3)")
        rede.fila.clear()  # descarta
        await asyncio.sleep(0.25)
        self.assertEqual(len(rede.fila), 0, msg="Não deveria ter retransmitido ainda")
        await asyncio.sleep(0.06)
        self.assertEqual(len(rede.fila), 1, msg="Já deveria ter retransmitido")
        segmento, _ = rede.fila.pop(0)
        _, _, seq, ack, flags, _, _, _ = read_header(segmento)
        self.assertEqual(seq, ack_no, msg="Seq do retransmit deve ser ack_no (2)")
        self.assertTrue((flags & FLAGS_ACK) == FLAGS_ACK, msg="Retransmit deve ter flag ACK (2)")
        self.assertEqual(ack, seq_no, msg="ACK do retransmit deve corresponder ao seq_no do cliente (2)")
        ack_no += MSS
        rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no, ack_no, FLAGS_ACK), src_addr, dst_addr))

        payload = os.urandom(MSS)
        conexao.enviar(payload)
        await asyncio.sleep(0.001)
        self.assertEqual(len(rede.fila), 1, msg="Envio imediato deve colocar segmento na fila")
        segmento, _ = rede.fila.pop(0)
        _, _, seq, ack, flags, _, _, _ = read_header(segmento)
        self.assertEqual(seq, ack_no, msg="Seq do segmento deve ser ack_no (3)")
        self.assertTrue((flags & FLAGS_ACK) == FLAGS_ACK, msg="Flag ACK esperada (3)")
        self.assertEqual(ack, seq_no, msg="ACK do segmento deve corresponder ao seq_no (3)")
        ack_no += MSS
        rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no, ack_no, FLAGS_ACK), src_addr, dst_addr))

        payload = os.urandom(MSS)
        conexao.enviar(payload)
        self.assertEqual(len(rede.fila), 1, msg="Envio deve colocar segmento na fila (4)")
        rede.fila.clear()  # descarta

        # sample_rtt = 0.1
        # estimated_rtt = sample_rtt = 0.1
        # dev_rtt = sample_rtt/2 = 0.05
        # timeout_interval = estimated_rtt + 4*dev_rtt  = 0.3
        # 0.25 < timeout_interval < 0.35
        await asyncio.sleep(0.25)
        self.assertEqual(len(rede.fila), 0, msg="Não deveria ter retransmitido ainda")
        await asyncio.sleep(0.10)
        self.assertEqual(len(rede.fila), 1, msg="Já deveria ter retransmitido")

        segmento, _ = rede.fila.pop(0)
        _, _, seq, ack, flags, _, _, _ = read_header(segmento)
        self.assertEqual(seq, ack_no, msg="Seq do retransmit final deve ser ack_no")
        self.assertTrue((flags & FLAGS_ACK) == FLAGS_ACK, msg="Retransmit final deve ter flag ACK")
        self.assertEqual(ack, seq_no, msg="ACK do retransmit final deve corresponder ao seq_no")
        ack_no += MSS
        rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no, ack_no, FLAGS_ACK), src_addr, dst_addr))

if __name__ == '__main__':
    unittest.main()
