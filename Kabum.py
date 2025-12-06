from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
import time
from urllib.parse import urlparse, parse_qs
import pandas as pd  # Importa a biblioteca Pandas (apelidada de 'pd') para criar o Excel
import os            # Importa a biblioteca OS para mexer com arquivos do sistema
import re            # Importa Regex para limpar textos (tirar o R$ do preço)

# --- CONFIGURAÇÕES DO ROBÔ ---
PRECO_MIN = 0         # Preço mínimo para capturar
PRECO_MAX = 150       # Preço máximo para capturar
META_PRODUTOS = 100   # Quantos produtos queremos achar antes de parar
MAX_PAGINAS = 25      # Limite de segurança: se ler 25 páginas e não bater a meta, ele para

# 1. INICIALIZAÇÃO DO NAVEGADOR
# Abre uma janela nova do Chrome controlada pelo Selenium
driver = webdriver.Chrome()
driver.maximize_window() # Deixa a janela grande para evitar elementos escondidos
driver.get('https://www.kabum.com.br/') # Acessa o site alvo
time.sleep(3) # Espera técnica para garantir que o site carregou visualmente

print("Acessando a home do Kabum...")
time.sleep(3)

# 2. TRATAMENTO DE COOKIES
try:
    # Procura na tela um botão que tenha o texto "Entendi" OU "Aceitar"
    # O XPath é uma linguagem de busca poderosa para encontrar elementos complexos
    botao_cookies = driver.find_element(By.XPATH, "//button[contains(text(), 'Entendi') or contains(text(), 'Aceitar')]")
    botao_cookies.click() # Clica para fechar o aviso
    print("Cookies: Aceitos/Fechados.")
    time.sleep(1)
except Exception:
    # Se der erro (ex: o banner não apareceu), o código não trava, apenas avisa e continua
    print("Cookies: O banner não apareceu ou não foi encontrado (seguindo o baile).")

# 3. NAVEGAÇÃO ATÉ A CATEGORIA
try:
    # Procura um link que contenha a palavra "Periféricos"
    botao_perifericos = driver.find_element(By.PARTIAL_LINK_TEXT, "Periféricos")
    
    botao_perifericos.click() # Entra na página de periféricos
    print("Sucesso: Cliquei em 'Periféricos'!")

except Exception as e:
    # Se não achar o botão, é um erro crítico. Encerra o programa.
    print("ERRO: Não consegui achar ou clicar no botão.")
    print(f"Detalhe do erro: {e}")
    time.sleep(10)
    driver.quit() # Fecha o navegador
    exit() # Mata o processo do Python

# 4. PREPARAÇÃO PARA PAGINAÇÃO
# Pega a URL atual (ex: kabum.com.br/perifericos) e remove qualquer "lixo" depois do '?'
url_base = driver.current_url.split('?')[0]

produtos_coletados = [] # Cria uma lista vazia para guardar os dicionários dos produtos
pagina_atual = 1        # Começamos pela página número 1

# 5. LOOP PRINCIPAL (O MOTOR DO ROBÔ)
# Repete o bloco abaixo ENQUANTO a meta não for atingida E não estourar o limite de páginas
while len(produtos_coletados) < META_PRODUTOS and pagina_atual <= MAX_PAGINAS:
    
    print(f"\n--- Lendo Página {pagina_atual} (Já temos {len(produtos_coletados)} produtos) ---")

    # Se não for a primeira página, precisamos "forçar" a ida para a próxima via URL
    if pagina_atual > 1:
        # Monta o link novo: URL base + numero da pagina + ordena por preço crescente (price_asc)
        link_proxima = f"{url_base}?page_number={pagina_atual}&sortBy=price_asc"
        driver.get(link_proxima) # O navegador carrega essa nova página
        time.sleep(3) # Espera carregar
    
    # Busca todos os elementos que sejam produtos (No Kabum, usam a tag HTML <article>)
    lista_produtos = driver.find_elements(By.TAG_NAME, "article")

    # Se a página estiver vazia, encerra o loop para não ficar rodando à toa
    if len(lista_produtos) == 0:
        print("Nenhum produto encontrado nesta página. Encerrando.")
        break

    # Loop interno: analisa cada card encontrado na página atual
    for produto in lista_produtos:
        try:
            # Coleta o Texto do Título
            titulo = produto.find_element(By.CSS_SELECTOR, "span.nameCard").text
            
            # Coleta o Texto do Preço (Ex: R$ 129,90)
            preco_texto = produto.find_element(By.CSS_SELECTOR, "span.priceCard").text
            
            # [NOVO] Coleta o Link do Produto
            # Procura a tag 'a' (link) dentro do card e pega o endereço (href)
            link = produto.find_element(By.TAG_NAME, "a").get_attribute("href")
            
            # LIMPEZA DE DADOS:
            # Usa Regex para remover tudo que não for dígito ou vírgula
            apenas_numeros = re.sub(r'[^\d,]', '', preco_texto).replace(',', '.')
            # Converte o texto limpo "129.90" para número decimal 129.90
            preco_float = float(apenas_numeros)

            # LÓGICA DE FILTRO: Só aceita se estiver entre o Mínimo e o Máximo
            if PRECO_MIN <= preco_float <= PRECO_MAX:
                
                # Verifica se o título já existe na nossa lista para não pegar repetidos
                if titulo not in [p['titulo'] for p in produtos_coletados]:
                    
                    # [NOVO] Bloco para pegar detalhes extras (Preço Antigo e Pagamento)
                    try:
                        # Tenta achar o preço riscado (oldPriceCard)
                        preco_antigo = produto.find_element(By.CSS_SELECTOR, "span.oldPriceCard").text
                    except:
                        # Se não tiver (não está em promoção), define um texto padrão
                        preco_antigo = "Sem desconto anterior"
                    
                    # Como pegamos o preço verde grande, ele sempre é "À vista" no Kabum
                    pagamento = "À vista no PIX"

                    print(f"✅ ACHEI! {titulo[:40]}... | R$ {preco_float}")

                    # Adiciona os dados validados (incluindo os novos) na lista principal
                    produtos_coletados.append({
                        "titulo": titulo,
                        "preco_atual": preco_float,
                        "preco_original": preco_antigo, # Coluna Nova no Excel
                        "forma_pagamento": pagamento,   # Coluna Nova no Excel
                        "link": link                    # Coluna Nova no Excel
                    })

                    # Se atingiu 100 produtos no meio da página, para imediatamente
                    if len(produtos_coletados) >= META_PRODUTOS:
                        break
            else:
                # Se o preço for ruim, ignora e o loop continua
                # print(f"❌ Ignorado: {titulo} | Preço: R$ {preco_float}")
                pass
        except Exception as e:
            # Se der erro ao ler um card (ex: card de publicidade sem preço), pula para o próximo
            continue
    
    # Incrementa o contador para que na próxima volta o robô vá para a página seguinte (2, 3, 4...)
    pagina_atual += 1   

print(f"\nResumo Final: Coletados {len(produtos_coletados)} produtos na faixa de preço.")

# 6. EXPORTAÇÃO PARA EXCEL
# Verifica se temos algo para salvar
if len(produtos_coletados) > 0:
    # Cria um DataFrame (uma tabela inteligente do Pandas) com nossos dados
    df = pd.DataFrame(produtos_coletados)

    # Define o nome do arquivo final
    nome_arquivo = "resultado_kabum.xlsx"
    
    # Salva o arquivo no disco. 
    # index=False serve para não criar uma coluna extra com 0, 1, 2, 3... no Excel
    df.to_excel(nome_arquivo, index=False)

    print(f"\nARQUIVO SALVO COM SUCESSO: {nome_arquivo}")
    # Mostra onde o arquivo foi salvo (pasta atual)
    print(f"Local: {os.getcwd()}")
else:
    print("\nNenhum produto foi coletado, nada para salvar.")

# ----------------------------------------------
# Mantém o terminal aberto até você apertar Enter
input("\nPressione ENTER no terminal para fechar o robô...")
driver.quit() # Fecha o navegador corretamente