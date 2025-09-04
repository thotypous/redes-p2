import unittest
import random
from tcputils import *
from tcp import Servidor

from tests.common import *

class TestStep1(unittest.TestCase):
    def test_step1(self):
        foi_aceita = False
        conexao_obj = None
        def conexao_aceita(conexao):
            nonlocal foi_aceita
            nonlocal conexao_obj
            foi_aceita = True
            conexao_obj = conexao

        rede = CamadaRede()
        dst_port = gerar_porta_servidor()
        servidor = Servidor(rede, dst_port)
        servidor.registrar_monitor_de_conexoes_aceitas(conexao_aceita)

        src_port = gerar_porta_cliente()
        seq_no = gerar_seq_no()
        src_addr, dst_addr = gerar_enderecos_teste1()
        self.assertListEqual(rede.fila, [], msg="A camada de rede não deveria ter mensagens pendentes antes do teste")
        rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port, dst_port, seq_no, 0, FLAGS_SYN), src_addr, dst_addr))
        self.assertTrue(foi_aceita, msg="O monitor de conexões aceitas deveria ter sido chamado")
        self.assertEqual(len(rede.fila), 1, msg="Esperava-se que o servidor enviasse um SYN+ACK em resposta ao SYN")
        segmento, dst_addr2 = rede.fila[0]
        self.assertEqual(fix_checksum(segmento, src_addr, dst_addr), segmento, msg="O checksum do segmento enviado pelo servidor está incorreto")
        src_port2, dst_port2, seq_no2, ack_no2, flags2, _, _, _ = read_header(segmento)
        self.assertEqual(4*(flags2>>12), len(segmento), msg="O SYN+ACK não deveria ter payload")
        self.assertEqual(dst_addr2, src_addr, msg="O endereço de destino do segmento enviado deveria ser o endereço do cliente")
        self.assertEqual(src_port2, dst_port, msg="A porta de origem do segmento enviado deveria ser a porta do servidor")
        self.assertEqual(dst_port2, src_port, msg="A porta de destino do segmento enviado deveria ser a porta do cliente")
        self.assertEqual(ack_no2, seq_no + 1, msg="O ACK do SYN+ACK deve ser seq_no+1")
        self.assertEqual(flags2 & (FLAGS_SYN|FLAGS_ACK), (FLAGS_SYN|FLAGS_ACK), msg="O segmento de resposta deve ter as flags SYN e ACK")
        self.assertEqual(flags2 & (FLAGS_FIN|FLAGS_RST), 0, msg="O segmento de resposta não deve conter FIN ou RST")

        # Verifica que o objeto de conexão passado ao monitor possui a API esperada
        self.assertIsNotNone(conexao_obj, msg="O monitor de conexões aceitas deveria receber o objeto de conexão")
        self.assertTrue(hasattr(conexao_obj, 'enviar') and callable(getattr(conexao_obj, 'enviar')), msg="O objeto de conexão deve expor o método 'enviar'")
        self.assertTrue(hasattr(conexao_obj, 'registrar_recebedor') and callable(getattr(conexao_obj, 'registrar_recebedor')), msg="O objeto de conexão deve expor o método 'registrar_recebedor'")

        # Checa comportamento com checksum inválido
        rede.fila.clear()
        foi_aceita = False
        self.assertListEqual(rede.fila, [], msg="A camada de rede não deveria ter mensagens pendentes antes do teste (2)")
        rede.callback(src_addr, dst_addr, make_header(src_port, dst_port, seq_no, 0, FLAGS_SYN))
        self.assertFalse(foi_aceita, msg="O monitor de conexões aceitas não deveria ter sido chamado pois o checksum era inválido")
        self.assertListEqual(rede.fila, [], msg="O TCP não deveria ter gerado resposta quando checksum inválido")

        # Verifica aleatoriedade do número de sequência do servidor
        rede.fila.clear()
        src_port3 = src_port
        while src_port3 == src_port:
            src_port3 = gerar_porta_cliente()
        rede.callback(src_addr, dst_addr, fix_checksum(make_header(src_port3, dst_port, seq_no, 0, FLAGS_SYN), src_addr, dst_addr))
        self.assertEqual(len(rede.fila), 1, msg="Esperava resposta ao SYN válido")
        segmento, dst_addr4 = rede.fila[0]
        self.assertEqual(fix_checksum(segmento, src_addr, dst_addr), segmento, msg="Checksum do SYN+ACK inválido")
        src_port4, dst_port4, seq_no4, ack_no4, flags4, _, _, _ = read_header(segmento)
        self.assertEqual(4*(flags4>>12), len(segmento), msg="O SYN+ACK não deveria ter payload (2)")
        self.assertEqual(dst_addr4, src_addr, msg="Destino incorreto no SYN+ACK")
        self.assertEqual(src_port4, dst_port, msg="Porta de origem incorreta no SYN+ACK")
        self.assertEqual(dst_port4, src_port3, msg="Porta de destino incorreta no SYN+ACK")
        self.assertEqual(ack_no4, seq_no + 1, msg="ACK do SYN+ACK deve ser seq_no+1 (2)")
        self.assertNotEqual(seq_no4, seq_no2, msg="O primeiro número de sequência usado em uma conexão deveria ser aleatório")
        self.assertEqual(flags4 & (FLAGS_SYN|FLAGS_ACK), (FLAGS_SYN|FLAGS_ACK), msg="O segmento de resposta deve ter as flags SYN e ACK (2)")
        self.assertEqual(flags4 & (FLAGS_FIN|FLAGS_RST), 0, msg="O segmento de resposta não deve conter FIN ou RST (2)")

if __name__ == '__main__':
    unittest.main()
