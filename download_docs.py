import os
import time
import threading
from funcoes_auxiliares.funcoes_auxiliares import *
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.select import Select


'''
Este é um roteiro de automação de navegador por meio da Selenium.
Seu intuito é baixar documentos de processos judiciais que tramitem no PJE de 1 Instância do TJMT.
Para ser adaptada para os outros tribunais que tenham adotado o PJe, basta renomear/readequar os elementos web, a estrutura-base do portais é a mesma.

Necessário:
1 - fornecer uma lista de processos, em strings no formato de numeração única do CNJ "XXXXXXX-XX.XXXX.X.XX.XXXX".
2 - fornecer uma lista de usuários pje, em strings no formato "<cpf>?<senha>";
3 - fornecer os parâmetros de seleção de documentos para baixar, conforme dict abaixo;
4 - definir uma pasta para os downloads.

Com isso:
1 - o roteiro separa o processos em quantidades iguais para os usuários;
2 - o roteiro inicia uma thread de automação de navegador por usuário;
3 - o roteiro baixa os docs conforme parâmetros na pasta definida.

Uma vez baixado os docs, não é difícil escrever pequenos roteiros para, entre outros, quais docs deveriam ser baixados, quais faltam.
Isso porque cada doc é baixado com um nome cujos 25 primeiros caracteres são o número do processo de origem.


Há três funções principais, uma envelopada dentro da outra:
1 - main, estabelece as threads de downloads por lista de processos e usuário
2 - baixar_docs_procs, define o roteiro de downloads de cada usuario
3 - baixar_docs_proc, defino o roteiro de entrar em cada processo específico

No módulo funcoes_auxiliares, como o nome diz, funções auxilares, para economizar espaço no roteiro principal.
'''

lista_procs = []
lista_usuarios = []
parametros_download = {
    "tipo_documento" : None, #ou string com nome exato do tipo do doc
    "id_partir": None, #ou int do id de início
    "id_ate": None, #ou int do id de final
    "periodo_de": None, #ou data em string 'ddmmaaaa' ou 'data_autuacao'
    "periodo_ate": None, #ou data em string 'ddmmaaaa' ou 'data_autuacao'
    #selecionar data_autuacao em ambos períodos para baixar somente os documentos iniciais
    "cronologia": 'Crescente', #ou 'Descrescente'
    "incluir_exp": 'Não', #ou 'Sim'
    "incluir_mov": 'Sim' #ou 'Não'
    }
'''
O fornecimento destes parâmetros é um problema à parte.
Definindo-se todos de igual maneira para todos os processos,
Encontra-se o problema de que os tipos de documento e números de ID variam processo por processo, de maneira não pré-estabelecida.
Os períodos de cada documento também variam de maneira não pré-determinável.
É possível capturar a data de autuacao de cada processo em cada página (determinando-se, assim, a primeira data),
assim como também é possível definir a data da última movimentação do processo.
Mas, se for o caso de pegar os docs desde o início até o fim, é só deixar os inputs em branco.
'''

def main(lista_usuarios, lista_procs, parametros):
    listas_procs = divide_list(lista_procs, len(lista_usuarios))
    for lista in listas_procs:
        print(len(lista))
    threads_selenium = []
    for usuario, lista in zip(lista_usuarios, listas_procs):
        thread = threading.Thread(target=baixar_docs_procs, args=(lista, usuario, parametros),
                                  name=f"{usuario.split('?')[0]}")
        (threads_selenium.append(thread))
    print(threads_selenium)
    for thread in threads_selenium:
        thread.start()
        #sleep para evitar erros, talvez desnecessário
        time.sleep(0.5)
    for thread in threads_selenium:
        thread.join()


def baixar_docs_procs(lista_procs, usuario, parametros):
# função criada para envelopar o download de docs por cada processo,
# para permitir rotina try/except e não parar o roteiro se algo der
# errado em um processo específico.
# BUG: não está fechando o driver após erro antes de abrir outro
    pasta = f"download_{usuario.split('?')[0]}"
    os.makedirs(pasta, exist_ok=True) #criando pastas com nome de cada usuario
    download_directory = os.path.abspath(pasta)
    options = webdriver.ChromeOptions()
    options.add_experimental_option('prefs', {"plugins.plugins_list": [{"enabled": False,
                                                                    "name": "Chrome PDF Viewer"}],
                                          "download.default_directory": download_directory,
                                          "download.extensions_to_open": "",
                                          "plugins.always_open_pdf_externally": True,
                                          "download.prompt_for_download": False  # desativando prompt de download
                                          })
    service = Service()
    driver = None
    for proc in lista_procs:
        if driver is None:
            driver = webdriver.Chrome(service=service, options=options)
            driver.implicitly_wait(10)
            logar(driver, usuario)
            time.sleep(5)
            ir_consulta(driver)
        else:
            pass
        try:
            baixar_docs_proc(driver=driver, proc=proc, pasta=download_directory, parametros=parametros)
        except Exception as e:
            print(f"erro no proc {proc}")
            print(e)
            driver.quit()
            driver = None

def baixar_docs_proc(driver, proc, pasta, parametros):
    input_nmr_proc(driver, proc)
    botao_pesquisar = driver.find_element(By.ID, "fPP:searchProcessos")
    botao_pesquisar.click()
    #ajustar conforme necessário
    #fora de horário útil (tarde da noite, madrugada, dá para deixar bem mais rápido)
    time.sleep(6)
    element_proc = driver.find_element(By.CSS_SELECTOR, value=".btn-link.btn-condensed")
    element_proc.click()
    #aqui é para superar o alerta de que o processo é de terceiros
    checkIfAlert(driver)
    time.sleep(2)
    wait = WebDriverWait(driver, 2)
    original_window = driver.current_window_handle
    #não lembro porque a linha abaixo está comentada
    #wait.until(EC.number_of_windows_to_be(2))
    for window_handle in driver.window_handles:
        if window_handle != original_window:
            driver.switch_to.window(window_handle)
            break
    #botão de download de documentos
    dropdown_download = driver.find_element(By.CSS_SELECTOR, value='li.dropdown.drop-menu.filtros-download')
    dropdown_download.click()
    time.sleep(1)
    #localizando elementos web dos parâmetros de seleção dos documentos
    seletor_tipo_doc = Select(driver.find_element(By.ID, value="navbar:cbTipoDocumento"))
    input_id_partir = driver.find_element(By.ID, value='navbar:idDe')
    input_id_ate = driver.find_element(By.ID, value='navbar:idDe')
    input_periodo_de = driver.find_element(By.ID, value='navbar:dtInicioInputDate')
    input_periodo_ate = driver.find_element(By.ID, value='navbar:dtFimInputDate')
    seletor_cronologia = Select(driver.find_element(By.ID, value="navbar:cbCronologia"))
    seletor_exp = Select(driver.find_element(By.ID, value="navbar:cbExpediente"))
    seletor_mov = Select(driver.find_element(By.ID, value="navbar:cbMovimentos"))
    #inserindo os parâmetros fornecidos
    #meio feio mas funciona
    #pequenos sleeps para evitar erros
    if parametros['tipo_documento']:
        seletor_tipo_doc.select_by_visible_text(parametros['tipo_documento'])
        time.sleep(0.3)
    if parametros['id_partir']:
        input_id_partir.send_keys(parametros['id_partir'])
        time.sleep(0.3)
    if parametros['id_ate']:
        input_id_ate.send_keys(parametros['id_ate'])
        time.sleep(0.3)
    if parametros['periodo_de']:
        if parametros['periodo_de'] == 'data_autuacao':
            element_mais_detalhes = driver.find_element(By.ID, 'maisDetalhes')
            dl_element = element_mais_detalhes.find_element(By.TAG_NAME, 'dl')
            dd_elements = dl_element.find_elements(By.TAG_NAME, 'dd')
            texto_data = dd_elements[3].get_attribute('innerHTML')
            #função auxiliar para converter, por ex. 01 jan 2020 em 01012020
            data_autuacao = converter_data_autuacao(texto_data)
            input_periodo_de.send_keys(data_autuacao)
            time.sleep(0.3)
        else:
            input_periodo_de.send_keys(parametros['periodo_de'])
            time.sleep(0.3)
    if parametros['periodo_ate']:
        if parametros['periodo_ate'] == 'data_autuacao':
            element_mais_detalhes = driver.find_element(By.ID, 'maisDetalhes')
            dl_element = element_mais_detalhes.find_element(By.TAG_NAME, 'dl')
            dd_elements = dl_element.find_elements(By.TAG_NAME, 'dd')
            texto_data = dd_elements[3].get_attribute('innerHTML')
            data_autuacao = converter_data_autuacao(texto_data)
            input_periodo_ate.send_keys(data_autuacao)
            time.sleep(0.3)
        else:
            input_periodo_ate.send_keys(parametros['periodo_ate'])
            time.sleep(0.3)
    if parametros['cronologia'] != 'Crescente':
        seletor_cronologia.select_by_visible_text(parametros['cronologia'])
        time.sleep(0.3)
    if parametros['incluir_exp'] != 'Não':
        seletor_exp.select_by_visible_text(parametros['incluir_exp'])
        time.sleep(0.3)
    if parametros['incluir_mov'] != 'Sim':
        seletor_mov.select_by_visible_text(parametros['incluir_mov'])
        time.sleep(0.3)
    #verificando o tamanho da pasta para, assim que mudar, encerrar a espera pelo download
    tamanho_inicial = os.path.getsize(pasta)
    botao_download_doc = driver.find_element(By.CSS_SELECTOR,
                                             value="input.btn.btn-primary[value='Download']")
    botao_download_doc.click()
    time.sleep(2)
    #não lembro o porquê da linha abaixo estar comentada
    #original_window2 = driver.current_window_handle
    wait.until(EC.number_of_windows_to_be(2))
    for window_handle in driver.window_handles:
        if window_handle != original_window:
            driver.switch_to.window(window_handle)
            break
    """esperar download"""
    for _ in range(20):  # ajustar conforme necessário
        time.sleep(1)
        current_size = os.path.getsize(pasta)
        if current_size > tamanho_inicial:
            break
    driver.close()
    driver.switch_to.window(original_window)


main(lista_usuarios=lista_usuarios, lista_procs=lista_procs, parametros=parametros_download)

