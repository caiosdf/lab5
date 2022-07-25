# replica de id 2

import select
import socket
import sys
import json

HOST = 'localhost'
PORTA = 5002

replicas = [(HOST, 5001), (HOST, 5003), (HOST, 5004)]

# id da réplica
id = 2

# dado replicado
x = 0

# booleanque determina se a réplica detém a cópia primária
copiaPrim = True

entradas = [sys.stdin]
conexoes = {}

# histórico de alterações
hist = []

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
	conexoes[endr[1]] = clisock 

	return clisock, endr

# atualiza as outras replicas com o novo valor de x
def updateReplicas(novoValor):
    global id
    for replica in replicas:
        sock = socket.socket()
        sock.connect(replica)
        msg = {'operacao': 'updateX', 'novoX': novoValor, 'replicaId': id}
        enviaMensagem(msg, sock)
        sock.close()
        
# atualiza a posse da cópia primária
def updateCopia():
    global copiaPrim
    copiaPrim = not copiaPrim
    return copiaPrim

# recebe um pedido de atualização de outra réplica
def atendeRequisicoes(clisock, endr):

    # recebe dados do cliente
    data = recebeMensagem(clisock)
    print(data)
    if not data:  # dados vazios: cliente encerrou
        print(str(endr) + '-> encerrou')
        clisock.close()  # encerra a conexao com o cliente
        return

    operacao = data['operacao']

    if operacao == 'updateX':
        #params = data['params'][1:-1].split(',')
        novoX = data['novoX']
        novoValor = int(novoX)
        replicaId = int(data['replicaId'])
        #replicaId = int(params[0])
        setX(novoValor, replicaId)
        #getX()
        #updateHist(replicaId, novoValor)
    elif operacao == 'updateCopia':
        global copiaPrim
        print('recebi um pedido pra entregar a cópia')
        print(f'minha cópia: {copiaPrim}')
        if copiaPrim == True:
            updateCopia()
            print(f'minha cópia agora: {copiaPrim}')
            if copiaPrim == True:
                msg = {'res': -1}
                enviaMensagem(msg, clisock)
                return
            else:
                msg = {'res': 0}
                enviaMensagem(msg, clisock)
                return
        else:
            msg = {'res': 0}
            enviaMensagem(msg, clisock)
            return

def getX():
    global x
    print(f"x = {x}")
    
# retorna o histórico de alterações do valor de x
def getHist():
    return hist
    
def setX(newX, replicaId):
    
    global x
    
    if(copiaPrim):
        x = newX
        res = updateHist(replicaId, x)
        print(f"Valor de x alterado para {newX} pela réplica {replicaId}")
        return x
    else:
        print('vou pedir a cópia primária')
        print(f'minha copia: {copiaPrim}')
        # pede cópia primária
        sock = socket.socket()
        res = pedeCopiaPrim(sock)
        if res == -1:
            print('Não foi possível obter a cópia primária')
            sock.close()
        else:
            updateCopia()
            print(f'agora minha copia: {copiaPrim}')
            x = newX
            res = updateHist(replicaId, x)
            print(f"Valor de x alterado para {newX} pela réplica {replicaId}")
            sock.close()
            return x
    
# pede cópia primária
def pedeCopiaPrim(sock):
    msg = {'operacao': 'updateCopia'}
    for replica in replicas:
        sock.connect(replica)
        enviaMensagem(msg, sock)
        res = recebeMensagem(sock)
        if int(res['res']) == -1:
            return -1
    return 0

# atualiza o histórico de alterações com a tupla (replicaId, novoValorDeX)
def updateHist(replicaId, novoValor):
    if(len(hist) == 0):
        hist.append((replicaId, novoValor))
    else:
        if(hist[-1][0] == replicaId):
            hist[-1] = (replicaId, novoValor)
        else:
            hist.append((replicaId, novoValor))
    return hist


def main():
    global id
    sock = init()
    while True:
        print('Digite um comando: ')
        #espera por qualquer entrada de interesse
        leitura, escrita, excecao = select.select(entradas, [], [])
        #tratar todas as entradas prontas
        for pronto in leitura:
            if pronto == sock:  #pedido novo de conexao
                clisock, endr = aceitaConexao(sock)
                print ('Conectado com: ', endr)
                
                atendeRequisicoes(clisock, endr)
                #cria nova thread para atender o cliente
                # cliente = threading.Thread(target=atendeRequisicoes, args=(clisock,endr))
                # cliente.start()
                # clientes.append(cliente) #armazena a referencia da thread para usar com join()
            elif pronto == sys.stdin: #entrada padrao
                cmd = input()
                if cmd == 'fim': #solicitacao de finalizacao do servidor
                    sock.close()
                    sys.exit()
                elif cmd == 'atualiza':
                    novoValor = input('digite o novo valor de X: ')
                    res = setX(novoValor, id)
                    updateReplicas(res)
                    getX()
                elif cmd == 'x':
                    getX()
                elif cmd == 'hist':
                    print(getHist())
                else:
                    print('comando não reconhecido.')
                        
main()