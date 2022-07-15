from concurrent.futures import thread
import socket
import select
import threading
import sys
import json
from time import sleep

# replica de id 1
id = 1

# endereço da réplica
HOST = 'localhost'
PORTA = 5001

# endereços das outras réplicas
replicas = [(HOST, 5002), (HOST, 5003), (HOST, 5004)]

#define a lista de I/O de interesse
entradas = [sys.stdin]

#armazena historico de conexoes 
conexoes = {}

mutex = threading.Lock()

# dado replicado
x = 0

# histórico de alterações
hist = []

# booleanque determina se a réplica detém a cópia primária
copiaPrim = True

# status da réplica: 0 se livre e 1 se ocupada
status = 0

# retorna o valor atual de x na réplica
def getX():
    return x

# retorna o histórico de alterações do valor de x
def getHist():
    return hist

# retorna o status da réplica 
def getStatus():
    return status

# retorna se a réplica detém, ou não, a cópia
def getCopia():
    return copiaPrim

# atualiza o histórico de alterações com a tupla (replicaId, novoValorDeX)
def updateHist(replicaId, novoValor):
    hist.append((replicaId, novoValor))
    return hist

# atualiza o status da réplica
def updateStatus(novoStatus):
    if novoStatus not in [0,1]:
        return -1
    else:
        status = novoStatus
        return status

# atualiza a posse da cópia primária
def updateCopia():
    copiaPrim = not copiaPrim
    return copiaPrim

# altera o valor de x
def updateX(replicaId, novoValor):

    if(copiaPrim):
        x = novoValor
        res = updateHist(replicaId, x)
        print(f"Valor de x alterado para {novoValor} pela réplica {replicaId}")
        return res
    else:
        # encrontrar a cópia primaria
        pass

# inicia o servidor
def init():

    # cria o socket 
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #Internet( IPv4 + TCP) 

	# vincula a localizacao do servidor
    sock.bind((HOST, PORTA))

	# coloca-se em modo de espera por conexoes
    sock.listen(5) 

	# configura o socket para o modo nao-bloqueante
    sock.setblocking(False)

	# inclui o socket principal na lista de entradas de interesse
    entradas.append(sock)

    return sock

# envia mensagem para outra replica
def enviaMensagem(mensagem, sock):
    msgJson = json.dumps(mensagem)
    sock.send(msgJson.encode("utf-8"))

# recebe mensagem de outra réplica
def recebeMensagem(sock):
    msg = sock.recv(2048)
    return json.loads(msg.decode("utf-8"))

# aceita nova conexão e retorna o novo socket da conexão e o endereço do cliente
def aceitaConexao(sock):

	# estabelece conexao com o proximo cliente
	clisock, endr = sock.accept()

	# registra a nova conexao
	conexoes[clisock] = endr 

	return clisock, endr

# toma posse da cópia primaria
def pedeCopiaPrim(sock):
    # flag que determina se a replica conseguiu a cópia primária
    copiaResgatada = False

    while not copiaResgatada:
        msg = {'operacao': 'getStatus'}
        enviaMensagem(msg, sock)
        res = recebeMensagem(sock)
        if res == 0:
            msg = {'operacao': 'updateCopia'}
            enviaMensagem(msg, sock)
            res = recebeMensagem(sock)
            # tratar possível erro
            updateCopia()
            copiaResgatada = True
        else:
            sleep(1)
            continue

# recebe um pedido de atualização de outra réplica
def atendeRequisicoes(clisock, endr):

    while True:

		# recebe uma tupla (replicaId, NovoValorDeX)
        data = clisock.recv(1024) 

        if not data: # dados vazios: cliente encerrou
            print(str(endr) + '-> encerrou')
            clisock.close() # encerra a conexao com o cliente
            return 
        else:
            data_str = str(data, encoding='utf-8')
            print(str(endr) + ': ' + data_str)
            splited_data = data_str[1:-1].split(',')
            replica_id = int(splited_data[0])
            novoValorX = int(splited_data[1])
            mutex.acquire()
            updateX(replica_id, novoValorX)
            mutex.release()

def main():
    clientes=[] #armazena as threads criadas para fazer join
    sock = init()
    print("Pronto para receber conexoes...")
    while True:
		#espera por qualquer entrada de interesse
        leitura, escrita, excecao = select.select(entradas, [], [])
		#tratar todas as entradas prontas
        for pronto in leitura:
            if pronto == sock:  #pedido novo de conexao
                clisock, endr = aceitaConexao(sock)
                print ('Conectado com: ', endr)
				#cria nova thread para atender o cliente
                cliente = threading.Thread(target=atendeRequisicoes, args=(clisock,endr))
                cliente.start()
                clientes.append(cliente) #armazena a referencia da thread para usar com join()
            elif pronto == sys.stdin: #entrada padrao
                cmd = input()
                if cmd == 'fim': #solicitacao de finalizacao do servidor
                    for c in clientes: #aguarda todas as threads terminarem
                        c.join()
                    sock.close()
                    sys.exit()
                elif cmd == 'hist': #outro exemplo de comando para o servidor
                    print(getHist())
                elif cmd == 'x':
                    print(getX())
                elif cmd == 'atualiza':
                    novoValor = input('digite o novo valor de X: ')
                    mutex.acquire()
                    updateX(id, novoValor)
                    mutex.release()
