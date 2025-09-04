import unittest
import os
import random
from tcputils import *
from tcp import Servidor

from tests.common import *

class TestStep3(unittest.TestCase):
    def test_step3(self):
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
        src_addr, dst_addr = gerar_enderecos_teste3()
        rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no, 0, FLAGS_SYN), src_addr, dst_addr))
        segmento, _ = rede.fila[0]
        _, _, ack_no, ack, flags, _, _, _ = read_header(segmento)
        self.assertEqual(4*(flags>>12), len(segmento), msg="O SYN+ACK não deveria ter payload")
        self.assertTrue((flags & FLAGS_ACK) == FLAGS_ACK, msg="O SYN+ACK deve ter flag ACK")
        rede.fila.clear()

        seq_no += 1
        ack_no += 1
        self.assertEqual(ack, seq_no, msg="ACK enviado pelo servidor no SYN+ACK deve ser seq_no + 1")

        rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no, ack_no, FLAGS_ACK), src_addr, dst_addr))
        rede.fila.clear()

        payload = os.urandom(MSS)
        conexao.enviar(payload)
        self.assertEqual(len(rede.fila), 1, msg="Enviar dado pela conexão deve gerar exatamente um segmento na fila da camada de rede")
        segmento, _ = rede.fila[0]
        _, _, seq, ack, flags, _, _, _ = read_header(segmento)
        self.assertEqual(seq, ack_no, msg="Número de sequência no segmento enviado deve ser o ack esperado")
        # Decomponha condição complexa em múltiplas asserts
        self.assertTrue((flags & FLAGS_ACK) == FLAGS_ACK, msg="O segmento de envio deve ter flag ACK")
        self.assertEqual(ack, seq_no, msg="O ack enviado deve corresponder ao seq_no do cliente")
        self.assertEqual(segmento[4*(flags>>12):], payload, msg="O payload do segmento enviado não corresponde ao enviado pela aplicação")
        ack_no += MSS
        rede.fila.clear()

        payload = b'hello world'
        rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no, ack_no, FLAGS_ACK) + payload, src_addr, dst_addr))
        seq_no += len(payload)
        self.assertEqual(recebido, payload, msg="Os dados recebidos pela camada de aplicação não correspondem ao que o cliente enviou")
        recebido = b''
        rede.fila.clear()

        for i in range(5):
            nseg = random.randint(2,10)
            payload = os.urandom(nseg*MSS)
            conexao.enviar(payload)

            # enviar um payload vazio não deve criar segmentos
            antes = len(rede.fila)
            conexao.enviar(b'')
            depois = len(rede.fila)
            self.assertEqual(antes, depois, msg="enviar(b'') não deveria colocar segmentos na fila")

            for j in range(nseg):
                self.assertLessEqual(len(rede.fila)+j, nseg, msg=f'Você deveria ter enviado no máximo {nseg} segmentos, mas parece ter enviado mais')
                segmento, _ = rede.fila.pop(0)
                _, _, seq, ack, flags, _, _, _ = read_header(segmento)
                self.assertEqual(seq, ack_no, msg="Número de sequência de cada segmento deve bater com ack_no atual")
                self.assertTrue((flags & FLAGS_ACK) == FLAGS_ACK, msg="Cada segmento enviado deve ter flag ACK")
                self.assertEqual(ack, seq_no, msg="ACK em segmentos enviados deve corresponder ao seq_no do cliente")
                self.assertEqual(segmento[4*(flags>>12):], payload[j*MSS:(j+1)*MSS], msg="Conteúdo do segmento não corresponde ao fragmento esperado")
                ack_no += MSS
                rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no, ack_no, FLAGS_ACK), src_addr, dst_addr))

if __name__ == '__main__':
    unittest.main()
