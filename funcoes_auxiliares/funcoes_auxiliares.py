import sqlite3
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def divide_list(data, num_parts):
  """
  Função para dividir os processos em partes iguais entre os usuários.
  100% ChatGPT
  """
  part_size = len(data) // num_parts
  leftover = len(data) % num_parts
  parts = []
  for i in range(num_parts):
    start_index = i * part_size
    end_index = start_index + part_size
    if i < leftover:
      end_index += 1
    parts.append(data[start_index:end_index])
  return parts

def coletar_lista_procs_db(query, database):
    con = sqlite3.connect(database)
    cur = con.cursor()
    # defina os processos de interesse
    cur.execute(query)
    procs = cur.fetchall()
    return procs

def converter_data_autuacao(texto_pje):
    meses = {
        'jan':'01',
        'fev':'02',
        'mar':'03',
        'abr':'04',
        'mai':'05',
        'jun':'06',
        'jul':'07',
        'ago':'08',
        'set':'09',
        'out':'10',
        'nov':'11',
        'dez': '12'
    }
    texto = texto_pje.strip()
    dia = texto[:2]
    mes = texto[3:6]
    ano = texto[-4:]
    texto_conv = dia+meses[mes]+ano
    return texto_conv


def logar(driver, usuario):
    cpf, senha = usuario.split('?')
    driver.get("https://pje.tjmt.jus.br/pje/login.seam")
    frame = driver.find_element(By.ID, value='ssoFrame')
    driver.switch_to.frame((frame))
    username = driver.find_element(By.CSS_SELECTOR, value="input#username")
    password = driver.find_element(By.CSS_SELECTOR, value="input#password")
    username.send_keys(cpf)
    password.send_keys(senha)
    entrar = driver.find_element(By.ID, value="kc-login")
    entrar.click()

def ir_consulta(driver):
    driver.get("https://pje.tjmt.jus.br/pje/Processo/ConsultaProcesso/listView.seam")


def checkIfAlert(driver):
    try:
        alert = WebDriverWait(driver, 10).until(EC.alert_is_present())
        driver.switch_to.alert.accept()
    except:
        pass

def input_nmr_proc(driver, proc):
    nmr_proc = proc.replace("8.11.", "")
    _ = nmr_proc.split("-")
    nmr_proc1 = _[0]
    nmr_proc2, nmr_proc3, nmr_proc4 = _[1].split(".")
    element_nmr_proc1 = driver.find_element(By.CSS_SELECTOR, value="input[id='fPP:numeroProcesso:numeroSequencial']")
    element_nmr_proc2 = driver.find_element(By.CSS_SELECTOR,
                                            value="input[id='fPP:numeroProcesso:numeroDigitoVerificador']")
    element_nmr_proc3 = driver.find_element(By.CSS_SELECTOR, value="input[id='fPP:numeroProcesso:Ano']")
    element_nmr_proc4 = driver.find_element(By.CSS_SELECTOR, value="input[id='fPP:numeroProcesso:NumeroOrgaoJustica']")
    element_nmr_proc1.clear()
    element_nmr_proc2.clear()
    element_nmr_proc3.clear()
    element_nmr_proc4.clear()
    element_nmr_proc1.send_keys(nmr_proc1)
    element_nmr_proc2.send_keys(nmr_proc2)
    element_nmr_proc3.send_keys(nmr_proc3)
    element_nmr_proc4.send_keys(nmr_proc4)
