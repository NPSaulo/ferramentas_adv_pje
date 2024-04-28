import time
import sqlite3
import json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.select import Select


'''
Este é um roteiro de automação de navegador por meio da Selenium.
Capturam-se dados e salvam-nos numa base de dados cuja estrutura é, pelo menos:

CREATE TABLE "processos" (
	"nmr_proc"	TEXT NOT NULL UNIQUE,
	"orgao_txt"	TEXT,
	"dia"	INTEGER,
	"mes"	INTEGER,
	"ano"	INTEGER,
	"classe_jud"	TEXT,
	PRIMARY KEY("nmr_proc")
)

Ou seja, uma table chamada processos, com os números dos processos sendo a primary key, mas em texto.
Já que o número de cada processo é único, utilizá-los como primary key garante que não haverá duplicidades
mesmo nos casos em que algum processo apareça em mais de uma busca. Há também campos de orgão e classe judicial, em texto, 
além de dia, mês e ano, em integer. Os outros dados do processo são melhor capturados via a API do PJe. A ideia aqui é
tão somente selecionar os de interesse, já que não se encontrou alternativa melhor que uma automação pelo Selenium.

Aqui salvam-se as informações numa base de dados, mas o script pode facilmente ser adaptado a outras estruturas / formatos.
Como, por exemplo, salvar os dados em um json.

A rotina é feita para o PJE de 1 Instância do TJMT, mas para ser adaptada para os outros tribunais que tenham adotado o PJe,
basta renomear os elementos web, a estrutura-base do portais é a mesma.
'''

def main(database, json_saida=None, nome_parte="", outros_nomes="",
                        nome_rep="", cpf="", cnpj="", assunto="", classe="", num_doc="", oab="", jurisd="", orgao="",
                        data_inicial="",data_final="", valor_ini="", valor_fim="", username="", password=""):
    con = sqlite3.connect(database)
    cur = con.cursor()
    procs = {} #para salvar num json
    driver = webdriver.Chrome()
    driver.implicitly_wait(10)
    driver.get("https://pje.tjmt.jus.br/pje/login.seam")
    frame = driver.find_element(By.ID, value='ssoFrame')
    driver.switch_to.frame((frame))
    driver.find_element(By.CSS_SELECTOR, value="input#username").send_keys(username)
    driver.find_element(By.CSS_SELECTOR, value="input#password").send_keys(password)
    driver.find_element(By.ID, value="kc-login").click()
    time.sleep(5)
    driver.get("https://pje.tjmt.jus.br/pje/Processo/ConsultaProcesso/listView.seam")
    time.sleep(5)
    nome_parte_element = driver.find_element(By.ID,"fPP:j_id158:nomeParte")
    outros_nomes_element = driver.find_element(By.ID,"fPP:j_id167:outrosNomesAlcunha")
    nome_rep_element = driver.find_element(By.ID,"fPP:j_id176:nomeAdvogado")
    cpf_element = driver.find_element(By.ID,"fPP:dpDec:documentoParte")
    #input é o mesmo do cpf, este elemento apenas altera a máscar do input
    cnpj_element = driver.find_element(By.ID,"cnpj")
    assunto_element = driver.find_element(By.ID,"fPP:j_id244:assunto")
    classe_element = driver.find_element(By.ID,"fPP:j_id253:classeJudicial")
    num_doc_element = driver.find_element(By.ID,"fPP:j_id262:numeroDocumento")
    oab_element = driver.find_element(By.ID,"fPP:decorationDados:numeroOAB")
    jurisd_element = Select(driver.find_element(By.ID,"fPP:jurisdicaoComboDecoration:jurisdicaoCombo"))
    orgao_element = Select(driver.find_element(By.ID,"fPP:orgaoJulgadorComboDecoration:orgaoJulgadorCombo"))
    data_inicial_element = driver.find_element(By.ID,"fPP:dataAutuacaoDecoration:dataAutuacaoInicioInputDate")
    data_final_element = driver.find_element(By.ID,"fPP:dataAutuacaoDecoration:dataAutuacaoFimInputDate")
    valor_ini_element = driver.find_element(By.ID,"fPP:valorDaCausaDecoration:valorCausaInicial")
    valor_fim_element = driver.find_element(By.ID,"fPP:valorDaCausaDecoration:valorCausaFinal")
    #seria bom poder encapsular isto tudo em algum outro local
    parametros_elementos = {
        "nome_parte": nome_parte_element,
        "outros_nomes": outros_nomes_element,
        "nome_rep": nome_rep_element,
        "cpf": cpf_element,
        "cnpj": cnpj_element,
        "assunto": assunto_element,
        "classe": classe_element,
        "num_doc": num_doc_element,
        "oab": oab_element,
        "data_inicial": data_inicial_element,
        "data_final": data_final_element,
        "valor_ini": valor_ini_element,
        "valor_fim": valor_fim_element
    }
    #inserir nos inputs os parâmetros fornecidos, exceto o orgao e jurisd, que ficam num seletor
    for parametro, elemento in parametros_elementos.items():
        if locals()[parametro]:
            elemento.send_keys(locals()[parametro])
            time.sleep(1) #para evitar erros
    if jurisd != "":
        jurisd_element.select_by_visible_text(jurisd)
    else:
        pass
    if orgao != "":
        orgao_element.select_by_visible_text(orgao)
    else:
        pass
    botao_pesquisar = driver.find_element(By.CSS_SELECTOR,
                                          value="input[id='fPP:searchProcessos']")
    botao_pesquisar.click()
    time.sleep(10)
    #a seção abaixo serve para definir a quantidade de página - o que é necessário para usar for ao invés de while
    #vai-se para a ultima pagina, e coleta-se o texto do elemento que marca a página atual
    #o try/except é para lidar com quando só há uma página, pois a rotina pressupõe
    #que haja uma página diferente da atual após pesquisar pelos processos
    cont_pags = 0
    botao_ultima_pag = driver.find_elements(By.CSS_SELECTOR, ".rich-datascr-button")[-1]
    botao_ultima_pag.click()
    time.sleep(5)
    try:
        pagina_atual = driver.find_element(By.CSS_SELECTOR, ".rich-datascr-act")
        ultima_pag = int(pagina_atual.text)
        botao_primeira_pag = driver.find_elements(By.CSS_SELECTOR, ".rich-datascr-button")[0]
        botao_primeira_pag.click()
        time.sleep(8)
    except:
        ultima_pag = 1
    #início do loop, visitará todas as páginas e salvará os dados de todos os processos.
    while cont_pags < ultima_pag:
        tabela_procs = driver.find_element(By.ID, "fPP:processosTable:tb")
        for row in tabela_procs.find_elements(By.TAG_NAME, "tr"):
            proc = row.find_elements(By.TAG_NAME, "td")
            proc_cell = proc[1]
            orgao_cell = proc[3]
            data_autuacao_cell = proc[4]
            classe_cell = proc[5]
            # as outras info (polo ativo, polo passivo e última moviment. são melhor capturadas pela API do PJe)
            nmr_proc = proc_cell.text
            orgao_txt = orgao_cell.text
            classe_jud = classe_cell.text
            dia, mes, ano = data_autuacao_cell.text.split("/")
            values = [nmr_proc, orgao_txt, dia, mes, ano, classe_jud]
            cur.execute("""INSERT OR REPLACE INTO processos (nmr_proc,orgao_txt,dia,mes,ano,classe_jud)
                                VALUES (?,?,?,?,?,?)""", values)
            if json_saida != None:
                with open(json_saida, "a") as file:
                    json.dump(values,file)
        con.commit()
        cont_pags += 1
        botao_proxima_pag = driver.find_elements(By.CSS_SELECTOR, ".rich-datascr-button")[-2]
        botao_proxima_pag.click()
        time.sleep(5)
    con.close()
    driver.quit()



if __name__ == "__main__":
    main(username="",password="",database="data.db",json_saida="teste.json")