import unittest
import os
import random
import asyncio
from tcputils import *
from tcp import Servidor

from tests.common import *

class TestStep7(unittest.IsolatedAsyncioTestCase):
    async def test_step7(self):
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
        src_addr, dst_addr = gerar_enderecos_teste7()
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

        ack_no += len(payload)
        rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no, ack_no, FLAGS_ACK), src_addr, dst_addr))

        payload = os.urandom(14*MSS)
        conexao.enviar(payload)
        for winsize in (2, 3, 4, 5):
            self.assertEqual(len(rede.fila), winsize, msg=f'A janela neste momento deveria ser de {winsize} MSS, mas foi de {len(rede.fila)} MSS')
            for _ in range(winsize):
                segmento, _ = rede.fila.pop(0)
                _, _, seq, ack, flags, _, _, _ = read_header(segmento)
                self.assertEqual(seq, ack_no, msg="Seq de cada segmento enviado deve ser ack_no")
                self.assertTrue((flags & FLAGS_ACK) == FLAGS_ACK, msg="Flag ACK esperada")
                self.assertEqual(ack, seq_no, msg="ACK em segmentos enviados deve corresponder ao seq_no do cliente")
                self.assertEqual(segmento[4*(flags>>12):], payload[:MSS], msg="Conteúdo do segmento não corresponde ao pedaço esperado")
                payload = payload[MSS:]
                ack_no += MSS
            if winsize == 5:
                # Causa um timeout
                await asyncio.sleep(0.25)
                self.assertEqual(len(rede.fila), 1, msg='Deveria ter acontecido a retransmissão de um segmento')
                rede.fila.clear()
            else:
                await asyncio.sleep(0.1)
            rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no, ack_no, FLAGS_ACK), src_addr, dst_addr))

        payload = os.urandom(12*MSS)
        conexao.enviar(payload)
        for winsize in (3, 4, 5):
            self.assertEqual(len(rede.fila), winsize, msg=f'A janela neste momento deveria ser de {winsize} MSS, mas foi de {len(rede.fila)} MSS')
            for _ in range(winsize):
                segmento, _ = rede.fila.pop(0)
                _, _, seq, ack, flags, _, _, _ = read_header(segmento)
                self.assertEqual(seq, ack_no, msg="Seq de cada segmento enviado deve ser ack_no (2)")
                self.assertTrue((flags & FLAGS_ACK) == FLAGS_ACK, msg="Flag ACK esperada (2)")
                self.assertEqual(ack, seq_no, msg="ACK em segmentos enviados deve corresponder ao seq_no do cliente (2)")
                self.assertEqual(segmento[4*(flags>>12):], payload[:MSS], msg="Conteúdo do segmento não corresponde ao pedaço esperado (2)")
                payload = payload[MSS:]
                ack_no += MSS
            await asyncio.sleep(0.1)
            rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no, ack_no, FLAGS_ACK), src_addr, dst_addr))

if __name__ == '__main__':
    unittest.main()
