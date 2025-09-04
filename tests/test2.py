import unittest
import os
import random
from collections import OrderedDict
from tcputils import *
from tcp import Servidor

from tests.common import *

class TestStep2(unittest.TestCase):
    def test_step2(self):
        seq_list = []
        ack_list = OrderedDict()
        esperado = b''
        recebido = b''
        def dados_recebidos(conexao, dados):
            nonlocal recebido
            recebido += dados

        def conexao_aceita(conexao):
            conexao.registrar_recebedor(dados_recebidos)

        rede = CamadaRede()
        dst_port = gerar_porta_servidor()
        servidor = Servidor(rede, dst_port)
        servidor.registrar_monitor_de_conexoes_aceitas(conexao_aceita)

        src_port = gerar_porta_cliente()
        seq_no = gerar_seq_no()
        src_addr, dst_addr = gerar_enderecos_teste2()
        rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no, 0, FLAGS_SYN), src_addr, dst_addr))
        segmento, _ = rede.fila[0]
        _, _, ack_no, ack, flags, _, _, _ = read_header(segmento)
        self.assertEqual(4*(flags>>12), len(segmento), msg="O SYN+ACK não deveria ter payload")
        self.assertTrue((flags & FLAGS_ACK) == FLAGS_ACK, msg="O SYN+ACK deve ter flag ACK")
        ack_list[ack] = None
        rede.fila.clear()

        seq_no += 1
        ack_no += 1

        payload = os.urandom(random.randint(16, MSS))
        rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no+random.randint(1, 128), ack_no, FLAGS_ACK) + payload, src_addr, dst_addr))
        payload = os.urandom(random.randint(4, MSS))
        rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no+random.randint(1, 128), ack_no, FLAGS_ACK) + payload, src_addr, dst_addr))

        payload = b'ola'
        rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no, ack_no, FLAGS_ACK) + payload, src_addr, dst_addr))
        rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no, ack_no, FLAGS_ACK) + payload, src_addr, dst_addr))
        seq_list.append(seq_no)
        seq_no += len(payload)
        esperado += payload

        payload = b', '
        rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no-3, ack_no, FLAGS_ACK) + payload, src_addr, dst_addr))
        rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no, ack_no, FLAGS_ACK) + payload, src_addr, dst_addr))
        rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no, ack_no, FLAGS_ACK) + payload, src_addr, dst_addr))
        seq_list.append(seq_no)
        seq_no += len(payload)
        esperado += payload

        payload = b'mundo'
        rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no-random.randint(1, 128), ack_no, FLAGS_ACK) + payload, src_addr, dst_addr))
        rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no-2, ack_no, FLAGS_ACK) + payload, src_addr, dst_addr))
        rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no+2, ack_no, FLAGS_ACK) + payload, src_addr, dst_addr))
        rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no+random.randint(1, 128), ack_no, FLAGS_ACK) + payload, src_addr, dst_addr))
        rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no, ack_no, FLAGS_ACK) + payload, src_addr, dst_addr))
        seq_list.append(seq_no)
        seq_no += len(payload)
        esperado += payload

        self.assertEqual(esperado, recebido, msg="Dados recebidos diferentes do esperado")

        payload = os.urandom(random.randint(16, MSS))
        rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no+random.randint(1, 128), ack_no, FLAGS_ACK) + payload, src_addr, dst_addr))
        payload = os.urandom(MSS)
        rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no+random.randint(1, 128), ack_no, FLAGS_ACK) + payload, src_addr, dst_addr))

        payload = os.urandom(random.randint(16, MSS))
        rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no, ack_no, FLAGS_ACK) + payload, src_addr, dst_addr))
        seq_list.append(seq_no)
        seq_no += len(payload)
        esperado += payload

        payload = os.urandom(MSS)
        rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no, ack_no, FLAGS_ACK) + payload, src_addr, dst_addr))
        seq_list.append(seq_no)
        seq_no += len(payload)
        seq_list.append(seq_no)
        esperado += payload

        self.assertEqual(esperado, recebido, msg="Dados recebidos devem corresponder ao esperado após vários segmentos")

        # Envia segmento com checksum inválido: deve ser ignorado (nenhum ACK adicional enviado)
        antes = len(rede.fila)
        # usa make_header sem fix_checksum para simular checksum inválido
        rede.callback(src_addr, dst_addr, make_header(src_port, dst_port, seq_no, ack_no, FLAGS_ACK) + b'bad')
        depois = len(rede.fila)
        self.assertEqual(antes, depois, msg="Segmento com checksum inválido não deveria gerar ACKs")

        for segmento, _ in rede.fila:
            ack_src_port, ack_dst_port, _, ack, flags, _, _, _ = read_header(segmento)
            self.assertEqual((ack_src_port, ack_dst_port), (dst_port, src_port), msg="As portas de origem/destino do servidor deveriam estar invertidas com relação às do cliente")
            self.assertEqual(4*(flags>>12), len(segmento), msg="Este teste não gera envios: não deveria haver payloads")
            if (flags & FLAGS_ACK) == FLAGS_ACK:
                ack_list[ack] = None

        ack_list = list(ack_list.keys())
        self.assertListEqual(seq_list, ack_list, msg="ACKs divergentes")

if __name__ == '__main__':
    unittest.main()
