from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import pandas as pd
import os

# --- CONFIGURAÇÕES ---
# Quero pegar bastante coisa para garantir que apareçam os baratos
MAX_PRODUTOS_DESEJADOS = 200  
PRECO_MIN = 0.00    # Começando do ZERO
PRECO_MAX = 150.00  # Até 150 reais

# Inicializa as listas
produtos_filtrados = []
links_visitados = set()

# Configura o navegador
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
driver = webdriver.Chrome(options=options)

try:
    print("--- Acessando KaBuM (Mais Vendidos) ---")
    driver.get("https://www.kabum.com.br/promocao/maisvendidos")
    time.sleep(5) # Espera carregar bem a página

    print(f"Buscando QUALQUER PRODUTO de R$ {PRECO_MIN:.2f} até R$ {PRECO_MAX:.2f}...")

    # Controle de Scroll
    scroll_atual = 0
    altura_scroll = 800  

    # Loop principal
    while len(produtos_filtrados) < MAX_PRODUTOS_DESEJADOS:
        
        # Pega todos os cards visíveis na tela
        # Usando a classe 'productCard' que é padrão do KaBuM
        cards = driver.find_elements(By.CLASS_NAME, "productCard")
        
        # Feedback visual no terminal
        print(f"Processando tela... (Total coletado: {len(produtos_filtrados)})")

        for card in cards:
            # Se já batemos a meta, para
            if len(produtos_filtrados) >= MAX_PRODUTOS_DESEJADOS:
                break

            try:
                # 1. PEGAR O LINK (Identificador único)
                try:
                    elem_link = card.find_element(By.TAG_NAME, "a")
                    link = elem_link.get_attribute("href")
                except:
                    continue 

                # Evita duplicados
                if link in links_visitados:
                    continue
                
                links_visitados.add(link)

                # 2. PEGAR O PREÇO
                try:
                    # Tenta pela classe específica 'priceCard'
                    preco_elem = card.find_element(By.CLASS_NAME, "priceCard")
                    preco_texto = preco_elem.text
                    
                    # Limpeza: tira R$, espaços invisíveis, etc
                    preco_limpo = preco_texto.replace("R$", "").replace("\u00a0", "").strip()
                    # Converte formato BR (1.000,00) para Python (1000.00)
                    preco_limpo = preco_limpo.replace(".", "").replace(",", ".")
                    preco_num = float(preco_limpo)
                except:
                    # Se não tiver preço (ex: esgotado), ignora
                    continue

                # 3. FILTRO DE PREÇO (0 a 150)
                if preco_num > PRECO_MAX:
                    # print(f"Ignorado (Caro): R$ {preco_num}") # Comentado para limpar o terminal
                    continue
                
                # Aceita qualquer coisa maior ou igual a 0
                if preco_num >= PRECO_MIN:
                    
                    # Pega o título só agora, para economizar processamento
                    try:
                        titulo = card.find_element(By.CLASS_NAME, "nameCard").text
                    except:
                        titulo = "Produto sem Nome"

                    # Adiciona na lista final
                    produtos_filtrados.append({
                        "titulo": titulo,
                        "preco": f"{preco_num:.2f}".replace(".", ","), # Salva formatado bonito
                        "link": link
                    })
                    
                    # Mostra no terminal
                    print(f"✅ R$ {preco_num:.2f} - {titulo[:40]}...")

            except Exception:
                continue

        # 4. ROLAGEM DE PÁGINA (SCROLL)
        driver.execute_script(f"window.scrollTo(0, {scroll_atual + altura_scroll});")
        scroll_atual += altura_scroll
        time.sleep(2) # Pausa importante para carregar itens novos
        
        # Verifica se a página acabou
        altura_total = driver.execute_script("return document.body.scrollHeight")
        if scroll_atual > altura_total:
            print("--- Fim da página alcançado ---")
            break

except Exception as e:
    print(f"Erro inesperado: {e}")

finally:
    driver.quit()

# SALVAR ARQUIVO
if produtos_filtrados:
    df = pd.DataFrame(produtos_filtrados)
    
    # Nome do arquivo ajustado
    output_path = os.path.join(os.getcwd(), "kabum_0_a_150_completo.xlsx")
    df.to_excel(output_path, index=False)
    
    print("\n" + "="*40)
    print(f"CONCLUÍDO! Coletados {len(produtos_filtrados)} produtos.")
    print(f"Arquivo salvo em: {output_path}")
    print("="*40)
else:
    print("\nNenhum produto encontrado. O site pode ter mudado o layout ou demorou para carregar.")