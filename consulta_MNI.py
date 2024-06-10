import requests
import csv
import time
import random
import threading
import sqlite3
from bs4 import BeautifulSoup
from funcoes_auxiliares import *

'''
Tem-se aqui um roteiro para extração de dados por meio do MNI - Modelo Nacional de Interoperabilidade (API) do PJe.

O tutorial oficial do WebService encontra-se aqui: https://www.pje.jus.br/wiki/index.php/Tutorial_MNI

Este roteiro é construído em cima da ideia de multithreading, de modo a acelerar a extração.
Fornece-se uma lista de processos de interesse, uma lista de usuários PJe (em nome dos quais as solicitações serão
feitas) e, ainda, uma base de dados na qual salvar as informações.

A lista de processos pode ser fornecido de diversos modos. Aqui, utiliza-se a função coletar_lista_procs_db() para extrair
os processo de uma base de dados.

A lista de processos será divida em partes o mais iguais possíveis entre os usuários e uma thread se iniciará para cada,
que enviará os requests ao webservice e coletará as informações desejadas.

Utiliza-se aqui sqlite3 para o armazenamento dos dados, solução extremamente simples porém com um grande problema:
não há suporte para acesso concurrente à base de dados, razão pela qual as informações são salvas somente após o final de
todas as consultas. Afinal, fazer isso com sqlite3 em multithread poderia ocasionar problemas. Assim, ao se fazer muitas 
consultas (na casa de milhares), o roteiro tem de ficar aberto/ em execução por muito tempo até sua conclusão.
Seria melhor inserir os dados na base de dados após cada consulta, ao invés de apenas no final de todas. Uma saída seria 
usar outros bancos que suportem acesso concorrente, como MySQL, PostgreSQL, ou ou SQLAlchemy com configuração de pool.

Apesar disso, ainda há valor neste roteiro, especialmente para usos mais esporádicos.
Quanto à estrutura da base de dados, para que nenhuma alteração seja necessária para usar tanto este roteiro quanto os 
coletar_lista_procs.py e download_docs.py, basta uma tabela como a abaixo:

CREATE TABLE "processos" (
	"nmr_proc"	TEXT,
	"orgao"	TEXT,
	"valor_causa"	NUMERIC,
	"classe"	TEXT,
	"procedimento"	TEXT,
	"assuntos"	NUMERIC,
	"ativo"	TEXT,
	"passivo"	TEXT,
	"adv_ativo"	TEXT,
	"adv_passivo"	TEXT,
	"dia"	INTEGER,
	"mes"	INTEGER,
	"ano"	INTEGER,
	"codigo_localidade"	TEXT,
	PRIMARY KEY("nmr_proc")
)

Anota-se, por fim, que, no roteiro abaixo, extraem-se poucas informações das disponíveis via MNI.
Isso tem a ver com os meus objetivos ao definir este roteiro. 
Quem desejar mais informações, pode simplesmente incrementar a extração via BeautifulSoup.


'''


#LISTA_PROCS = coletar_lista_procs_db()
#LISTA_USUARIOS = []
#DATABASE = ''
URL = 'https://pje.tjmt.jus.br/pje/intercomunicacao'



DICT_CNJ_ASSUNTOS = {}
DICT_CNJ_CLASSES = {}
#csv com os códigos de assuntos e seus significados
with open(r"codigos_cnj/Códigos Assuntos CNJ.csv", mode='r') as f:
    csv_reader = csv.reader(f, delimiter=',')
    for row in csv_reader:
       row_split = row[0].split(";")
       DICT_CNJ_ASSUNTOS[row_split[0]] = row_split[1]
#csv com os códigos de classes e seus significados
with open(r"codigos_cnj/Códigos Classes CNJ.csv", mode='r') as f:
    csv_reader = csv.reader(f, delimiter=',')
    for row in csv_reader:
       row_split = row[0].split(";")
       DICT_CNJ_CLASSES[row_split[0]] = row_split[1]



def main(url, lista_usuarios, lista_procs, database, delay=None):
    num_usuarios = len(lista_usuarios)
    print(f"número de usuários = {num_usuarios}")
    print(f'número de processo = {len(lista_procs)}')
    listas_procs = divide_list(lista_procs, num_usuarios)
    threads_MNI = []
    resultados_MNI = []
    for usuario, lista in zip(lista_usuarios, listas_procs):
        thread = threading.Thread(target=consulta_MNI, args=(url, usuario, lista, delay, resultados_MNI),
                                  name=f"{usuario.split('?')[0]}")
        threads_MNI.append(thread)
    print(threads_MNI)
    for thread in threads_MNI:
        thread.start()
        time.sleep(1)
    for thread in threads_MNI:
        thread.join()
    #seria melhor fazer isso dentro de cada thread, ao fim de cada consulta
    con = sqlite3.connect(database)
    cur = con.cursor()
    for resultado in resultados_MNI:
        proc = resultado[0]
        orgao_julgador = resultado[1]
        valor_causa = resultado[2]
        codigo_localidade = resultado[3]
        classe = resultado[4].upper()
        lista_assuntos = resultado[5].replace('[', '').replace(']', '')
        lista_partes_at = resultado[6].replace('[', '').replace(']', '')
        lista_adv_at = resultado[7].replace('[', '').replace(']', '')
        lista_partes_pa = resultado[8].replace('[', '').replace(']', '')
        lista_adv_pa = resultado[9].replace('[', '').replace(']', '')
        valores = [orgao_julgador, valor_causa, codigo_localidade, classe, lista_assuntos,lista_partes_at,
                   lista_partes_pa, lista_adv_at,  lista_adv_pa, proc]
        cur.execute("""
        UPDATE processos SET orgao = ?,valor_causa = ?, codigo_localidade = ?, classe = ?, 
        assuntos = ?, ativo = ?, passivo = ?, adv_ativo = ?, adv_passivo = ?
        WHERE nmr_proc = ?""", valores)
        con.commit()
    con.close()




def consulta_MNI(url, usuario, lista_procs, delay, resultados):
    #valores de interesse
    #há muitos outros, por ora extraindo apenas os abaixo
    for proc in lista_procs:
        try:
            valor_causa = None
            codigo_localidade = None
            classe = None
            # não extraio data pois já vem de outro roteiro
            # data_autuacao = None
            lista_assuntos = []
            orgao_julgador = None
            lista_partes_at = []
            lista_adv_at = []
            lista_partes_pa = []
            lista_adv_pa = []
            SOAPEnvelope = f"""
                                            <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ser="http://www.cnj.jus.br/servico-intercomunicacao-2.2.2/" xmlns:tip="http://www.cnj.jus.br/tipos-servico-intercomunicacao-2.2.2">
                                            <soapenv:Header/>
                                            <soapenv:Body>
                                            <ser:consultarProcesso>
                                            <tip:idConsultante>{usuario.split('?')[0]}</tip:idConsultante>
                                            <tip:senhaConsultante>{usuario.split('?')[1]}</tip:senhaConsultante>
                                            <tip:numeroProcesso>{proc}</tip:numeroProcesso>
                                            <tip:movimentos>false</tip:movimentos>
                                            <tip:incluirDocumentos>false</tip:incluirDocumentos>
                                            </ser:consultarProcesso>
                                            </soapenv:Body>
                                            </soapenv:Envelope>
                                            """

            response = requests.post(url, data=SOAPEnvelope)
            xml_content = response.text
            start_marker = '<soap:Envelope'
            end_marker = '</soap:Envelope>'
            start_pos = xml_content.find(start_marker)
            end_pos = xml_content.find(end_marker) + len(end_marker)
            body_content = xml_content[start_pos:end_pos]
            print(body_content)
            soup = BeautifulSoup(body_content, 'xml')
            dados_basicos = soup.find("dadosBasicos")
            # dataAjuizamento = dados_basicos['dataAjuizamento']
            # não extraio aqui pois essa info vem de outro roteiro
            try:
                classe = DICT_CNJ_CLASSES[dados_basicos['classeProcessual']]
            except:
                pass
            try:
                codigo_localidade = dados_basicos['codigoLocalidade']
            except:
                pass
            try:
                valor_causa = dados_basicos.find('valorCausa').getText()
            except:
                pass
            try:
                orgao_julgador = dados_basicos.find('orgaoJulgador')['nomeOrgao']
            except:
                pass
            try:
                assuntos = dados_basicos.find_all('assunto')
                for assunto in assuntos:
                    lista_assuntos.append(DICT_CNJ_ASSUNTOS[assunto.getText()])
            except:
                pass
            polos = dados_basicos.find_all('polo')
            for polo in polos:
                if polo['polo'] == 'AT':
                    partes_at = polo.find_all('ns2:parte')
                    for parte in partes_at:
                        pessoa = parte.find('ns2:pessoa')
                        # extraindo apenas o nome
                        # caso seja de valor extrair outros atributos, apenas adicionar
                        pessoa_atributos = {
                            'nome': pessoa['nome']
                        }
                        lista_partes_at.append(pessoa_atributos['nome'])
                        advogados = parte.find_all('ns2:advogado')
                        for advogado in advogados:
                            #extraindo apenas o nome, sem interesse nos outros atributos
                            advogado_atributos = {
                                'nome': advogado['nome']
                                }
                            lista_adv_at.append(advogado_atributos['nome'])
                elif polo['polo'] == 'PA':
                    partes_pa = polo.find_all('ns2:parte')
                    for parte in partes_pa:
                        pessoa = parte.find('ns2:pessoa')
                        # extraindo apenas o nome
                        pessoa_atributos = {
                            'nome': pessoa['nome']
                        }
                        lista_partes_pa.append(pessoa_atributos['nome'])
                        advogados = parte.find_all('ns2:advogado')
                        for advogado in advogados:
                            advogado_atributos = {
                                'nome': advogado['nome']
                            }
                            lista_adv_pa.append(advogado_atributos['nome'])
            valores = [proc[0], orgao_julgador, valor_causa, codigo_localidade, classe, str(lista_assuntos),
                       str(lista_partes_at), str(lista_adv_at), str(lista_partes_pa), str(lista_adv_pa)]
            print(valores)
            #atraso randomizado
            if delay:
                r = random.uniform(0.2,1)
                time.sleep(r + delay)
            resultados.append(valores)
        except Exception as e:
            print(e)
            print(f"Erro no processo {proc}")




#if __name__ == '__main__':
    #main(URL=URL, lista_usuarios=LISTA_USUARIOS, lista_procs=LISTA_PROCS, database=DATABASE, delay=0.5)



