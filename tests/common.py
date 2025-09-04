import socket, base64, select, os, re, sys
import random
from tcputils import *

class CamadaRede:
    ignore_checksum = False
    def __init__(self):
        self.callback = None
        self.fila = []
    def registrar_recebedor(self, callback):
        self.callback = callback
    def enviar(self, segmento, dest_addr):
        self.fila.append((segmento, dest_addr))

def gerar_porta_servidor():
    return random.randint(10, 1023)

def gerar_porta_cliente():
    return random.randint(1024, 0xffff)

def gerar_seq_no():
    return random.randint(0, 0xffff)

def gerar_enderecos_teste1():
    src_addr = '10.0.0.%d' % random.randint(1, 10)
    dst_addr = '10.0.0.%d' % random.randint(11, 20)
    return src_addr, dst_addr

def gerar_enderecos_teste2():
    src_addr = '172.16.%d.%d' % (random.randint(1, 10), random.randint(0, 255))
    dst_addr = '172.16.%d.%d' % (random.randint(11, 20), random.randint(0, 255))
    return src_addr, dst_addr

def gerar_enderecos_teste3():
    src_addr = '10.%d.1.%d' % (random.randint(1, 10), random.randint(0, 255))
    dst_addr = '10.%d.1.%d' % (random.randint(11, 20), random.randint(0, 255))
    return src_addr, dst_addr

def gerar_enderecos_teste4():
    return gerar_enderecos_teste3()

def gerar_enderecos_teste5():
    return gerar_enderecos_teste3()

def gerar_enderecos_teste6():
    src_addr = '10.%d.%d.%d' % (random.randint(1, 10), random.randint(0, 255), random.randint(0, 255))
    dst_addr = '10.%d.%d.%d' % (random.randint(11, 20), random.randint(0, 255), random.randint(0, 255))
    return src_addr, dst_addr

def gerar_enderecos_teste7():
    return gerar_enderecos_teste6()
