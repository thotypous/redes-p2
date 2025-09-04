import unittest
import os
import random
from tcputils import *
from tcp import Servidor

from tests.common import *

class TestStep4(unittest.TestCase):
    def test_step4(self):
        recebido = None
        def dados_recebidos(c, dados):
            nonlocal recebido
            recebido = dados

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
        src_addr, dst_addr = gerar_enderecos_teste4()
        rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no, 0, FLAGS_SYN), src_addr, dst_addr))
        segmento, _ = rede.fila[0]
        _, _, ack_no, ack, flags, _, _, _ = read_header(segmento)
        self.assertEqual(4*(flags>>12), len(segmento), msg="O SYN+ACK não deveria ter payload")
        self.assertTrue((flags & FLAGS_ACK) == FLAGS_ACK, msg="O SYN+ACK deve ter flag ACK")
        rede.fila.clear()

        seq_no += 1
        ack_no += 1
        self.assertEqual(ack, seq_no, msg="ACK do SYN+ACK deve ser seq_no+1")

        rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no, ack_no, FLAGS_FIN|FLAGS_ACK), src_addr, dst_addr))
        seq_no += 1
        self.assertEqual(recebido, b'', msg="Ao receber FIN do cliente, a camada de aplicação deve ser notificada com b'' (fechamento) e não com dados")

        self.assertEqual(len(rede.fila), 1, msg="Servidor deve enviar um ACK em resposta ao FIN")
        segmento, _ = rede.fila[0]
        _, _, _, ack, flags, _, _, _ = read_header(segmento)
        self.assertEqual(4*(flags>>12), len(segmento), msg="O servidor não enviou dados, então não deveria haver payload")
        self.assertTrue((flags & FLAGS_ACK) == FLAGS_ACK, msg="ACK em resposta ao FIN esperado")
        self.assertEqual(ack, seq_no, msg="ACK em resposta ao FIN deve confirmar o seq_no atualizado")
        rede.fila.clear()

        conexao.fechar()
        segmento, _ = rede.fila[0]
        _, _, seq, ack, flags, _, _, _ = read_header(segmento)
        self.assertTrue((flags & FLAGS_FIN) == FLAGS_FIN, msg="Ao fechar, a conexão deve enviar FIN")
        self.assertEqual(seq, ack_no, msg="Número de sequência do FIN deve ser o ack que o servidor esperava receber")
        if (flags & FLAGS_ACK) == FLAGS_ACK:
            self.assertEqual(ack, seq_no, msg="Se o FIN tiver ACK, o ack deve corresponder ao seq_no do cliente")
        ack_no += 1

        rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no, ack_no, FLAGS_ACK), src_addr, dst_addr))

        recebido = None
        rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no, ack_no, FLAGS_ACK) + os.urandom(MSS), src_addr, dst_addr))
        self.assertIsNone(recebido, msg="A conexão não deve receber dados depois de ter sido fechada")

if __name__ == '__main__':
    unittest.main()
