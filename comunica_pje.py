import time
import math
import json
import requests


def capturar_info_item(item): #definir aqui o que fazer com a info. de cada item
    id = item['id']
    data_disponibilizacao = item['data_disponibilizacao']
    siglaTribunal = item['siglaTribunal']
    tipoComunicacao = item['tipoComunicacao']
    nomeOrgao = item['nomeOrgao']
    texto = item['texto']
    numero_processo = item['numero_processo']
    meio = item['meio']
    link = item['link']
    tipoDocumento = item['tipoDocumento']
    nomeClasse = item['nomeClasse']
    codigoClasse = item['codigoClasse']
    numeroComunicacao = item['numeroComunicacao']
    ativo = item['ativo']
    hash = item['hash']
    status = item['status']
    motivo_cancelamento = item['motivo_cancelamento']
    data_cancelamento = item['data_cancelamento']
    datadisponibilizacao = item['datadisponibilizacao']
    #dataenvio = item['dataenvio'] #apareceu em coletas anteriores, hoje não aparece mais
    meiocompleto = item['meiocompleto']
    numeroprocessocommascara = item['numeroprocessocommascara']
    destinatarios = item['destinatarios']
    destinatarioadvogados = item['destinatarioadvogados']

def main(texto="", sigla_tribunal="", orgao_id="", meio="", data_inicio="", data_fim="", n_processo="", nome_parte="",
         nome_adv="", n_oab="", uf_oab=""):
    #definindo headers similares a de navegador, para dar aquela disfarçada
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
               'Accept': 'application/json, text/plain, */*',
               'Accept-Encoding': 'gzip, deflate, br, zstd'}
    params = {
            #Teor da comunicação (não funciona nem pelo navegador)
            'texto': texto,
            #Instituição
            'siglaTribunal': sigla_tribunal,
            #Órgão (inserir o ID do órgão. Para coletar o ID, inspecionar as páginas de https://comunica.pje.jus.br)
            'orgaoId': orgao_id,
            #Meio ('E' ou 'D')
            'meio': meio,
            #Data inicial (em string YYYY-MM-DD)
            'dataDisponibilizacaoInicio': data_inicio,
            #Data final (em string YYYY-MM-DD)
            'dataDisponibilizacaoFim': data_fim,
            #Nº de processo
            'numeroProcesso': n_processo,
            #Nome da parte
            'nomeParte': nome_parte,
            #Nome do advogado
            'nomeAdvogado': nome_adv,
            #Nº da OAB
            'numeroOab': n_oab,
            #UF da OAB
            'ufOab': uf_oab,
            'pagina': '1',
            'itensPorPagina': '5'
              }
    """
            Também dá para mexer na página e número de itens por página. Mas eu deixo eles como estão para imitar um 
            navegador e, também, porque o importante, nesta etapa, é tão somente coletar a contagem de resultados, 
            que é enviada no dict {'count': <>}. 
    """
    #deixando apenas os parâmetros fornecidos, para não enviar os outros como strings vazias
    params_filtrados = {k:v for k,v in params.items() if v}
    url = 'https://comunicaapi.pje.jus.br/api/v1/comunicacao'
    r = requests.get(url=url, auth=('user', 'pass'), headers=headers, params=params_filtrados)
    for key, value in r.request.headers.items():
        print(f"{key}: {value}")
    data = r.content.decode('utf-8')
    data_json = json.loads(data)
    print(data_json['status'])
    if data_json['status'] != "success":
        print(f"ERRO NA PÁGINA {params['pagina']}")
    count = data_json['count']
    print(f"Número de itens = {count}")
    #são até 5 itens por página, portanto, número de páginas equivale ao 'ceiling' da divisão do n. de itens por 5.
    n_paginas = math.ceil(count / 5)
    print(f"Número de páginas = {n_paginas}")
    print(r.url)
    for item in data_json['items']:
        print(item)
        capturar_info_item(item)
    time.sleep(2)
    for _ in range (2, n_paginas+1):
        params_filtrados['pagina'] = f"{_}"
        r = requests.get(url=url, auth=('user', 'pass'), headers=headers, params=params_filtrados)
        print(r.url)
        data = r.content.decode('utf-8')
        data_json = json.loads(data)
        if data_json['status'] != "success":
            print(f"ERRO NA PÁGINA {params['pagina']}")
        for item in data_json['items']:
            print(item)
            capturar_info_item(item)
        time.sleep(2)

"""
Se o envio dos parâmetros fornecidos não retornar o resultado esperado, confira se a busca por navegador no 
https://comunica.pje.jus.br/ está funcionando normalmente. Às vezes, nem pelo navegados os resultados retornam como 
esperados, o que pode ser indicação de um erro interno.
"""

if __name__ == '__main__':
    main(texto="", sigla_tribunal="", orgao_id="", meio="", data_inicio="", data_fim="", n_processo="", nome_parte="",
         nome_adv="", n_oab="", uf_oab="")

