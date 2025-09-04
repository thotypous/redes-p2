import unittest
import os
import random
import asyncio
from tcputils import *
from tcp import Servidor

from tests.common import *

class TestStep5(unittest.IsolatedAsyncioTestCase):
    async def test_step5(self):
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
        src_addr, dst_addr = gerar_enderecos_teste5()
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

        await asyncio.sleep(0.2)

        while len(rede.fila) > 0:
            segmento, _ = rede.fila.pop(0)
            _, _, seq, ack, flags, _, _, _ = read_header(segmento)
            self.assertEqual(seq, ack_no, msg="Número de sequência enviado deve bater com ack_no")
            self.assertTrue((flags & FLAGS_ACK) == FLAGS_ACK, msg="Segmento de dados deve ter flag ACK")
            self.assertEqual(ack, seq_no, msg="ACK no segmento deve corresponder ao seq_no do cliente")
            self.assertEqual(segmento[4*(flags>>12):], payload, msg="Payload enviado não corresponde ao esperado")

        ack_no += MSS
        rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no, ack_no, FLAGS_ACK), src_addr, dst_addr))

        payload = os.urandom(MSS)
        conexao.enviar(payload)
        self.assertEqual(len(rede.fila), 1, msg="Enviar payload deve gerar exatamente um segmento (2)")
        rede.fila.clear()  # descarta

        await asyncio.sleep(1.5)

        while len(rede.fila) > 0:
            segmento, _ = rede.fila.pop(0)
            _, _, seq, ack, flags, _, _, _ = read_header(segmento)
            self.assertEqual(seq, ack_no, msg="Número de sequência reenviado deve ser ack_no")
            self.assertTrue((flags & FLAGS_ACK) == FLAGS_ACK, msg="Retransmissão deve manter flag ACK")
            self.assertEqual(ack, seq_no, msg="ACK do retransmit deve corresponder ao seq_no do cliente")
            self.assertEqual(segmento[4*(flags>>12):], payload, msg="Payload retransmitido não corresponde ao original")

        ack_no += MSS
        rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no, ack_no, FLAGS_ACK), src_addr, dst_addr))

        payload = os.urandom(2*MSS)
        conexao.enviar(payload)
        rede.fila.clear()  # descarta

        await asyncio.sleep(1.5)

        while len(rede.fila) > 0:
            segmento, _ = rede.fila.pop(0)
            _, _, seq, ack, flags, _, _, _ = read_header(segmento)
            # Apenas o segmento mais antigo deve ser reenviado no timeout
            self.assertEqual(seq, ack_no, msg="Apenas o segmento mais antigo deve ser reenviado no timeout")
            self.assertTrue((flags & FLAGS_ACK) == FLAGS_ACK, msg="Retransmit deve ter flag ACK")
            self.assertEqual(ack, seq_no, msg="ACK do retransmit deve corresponder ao seq_no do cliente")
            self.assertEqual(segmento[4*(flags>>12):], payload[:MSS], msg="O conteúdo reenviado não corresponde ao esperado")

        ack_no += MSS
        rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no, ack_no, FLAGS_ACK), src_addr, dst_addr))

        await asyncio.sleep(1.5)

        segmento, _ = rede.fila.pop(0)
        _, _, seq, ack, flags, _, _, _ = read_header(segmento)
        # Agora deve vir o segundo segmento
        self.assertEqual(seq, ack_no, msg="Após ACK, deve enviar o próximo segmento")
        self.assertTrue((flags & FLAGS_ACK) == FLAGS_ACK, msg="Flag ACK esperada no segmento")
        self.assertEqual(ack, seq_no, msg="ACK do segmento deve corresponder ao seq_no do cliente")
        self.assertEqual(segmento[4*(flags>>12):], payload[MSS:], msg="Segundo pedaço do payload não corresponde ao esperado")

        ack_no += MSS
        rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no, ack_no, FLAGS_ACK), src_addr, dst_addr))

if __name__ == '__main__':
    unittest.main()
