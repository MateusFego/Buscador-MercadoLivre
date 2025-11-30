from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
import time
from urllib.parse import urlparse, parse_qs
import pandas as pd
import os


driver = webdriver.Chrome()
driver.get("https://www.mercadolivre.com.br/")

botao_ofertas = driver.find_element(By.CLASS_NAME, "nav-menu-item-link")
botao_ofertas.click()
time.sleep(2)
driver.execute_script("window.scrollTo(0, 800);")
time.sleep(4)
seletor_minimo = driver.find_element(By.XPATH, '//*[@id="min_input"]')
seletor_minimo.click()
time.sleep(1)
seletor_minimo.clear()
seletor_minimo.send_keys("100")
time.sleep(2)
seletor_maximo = driver.find_element(By.XPATH, '//*[@id="max_input"]')
seletor_maximo.click()
time.sleep(1)
seletor_maximo.clear()
seletor_maximo.send_keys("150")
time.sleep(2)
botao_filtrar = driver.find_element(By.XPATH, '//*[@id="root-app"]/div/section/div[1]/aside/section[4]/div/button')
botao_filtrar.click()
time.sleep(2)

MAX_PRODUTOS = 300        # limite que você quer coletar
produtos_encontrados = []

while True:
    # pegar os cards da página atual (seletor estável)
    listar_produtos = driver.find_elements(By.CLASS_NAME, "poly-card")

    for produto in listar_produtos:
        try:
            # título e link
            try:
                a = produto.find_element(By.CSS_SELECTOR, "a.poly-component__title")
                titulo = a.text.strip()
                link = a.get_attribute("href")
            except:
                titulo = None
                link = None

            # preço atual (fraction + cents se houver)
            try:
                frac = produto.find_element(By.CSS_SELECTOR, ".poly-price__current .andes-money-amount__fraction").text.strip()
                try:
                    cents = produto.find_element(By.CSS_SELECTOR, ".poly-price__current .andes-money-amount__cents").text.strip()
                    preco_atual = f"{frac},{cents}"
                except:
                    preco_atual = frac
            except:
                preco_atual = None

            # preço anterior
            try:
                prev_frac = produto.find_element(By.CSS_SELECTOR, ".andes-money-amount--previous .andes-money-amount__fraction").text.strip()
                try:
                    prev_cents = produto.find_element(By.CSS_SELECTOR, ".andes-money-amount--previous .andes-money-amount__cents").text.strip()
                    preco_anterior = f"{prev_frac},{prev_cents}"
                except:
                    preco_anterior = prev_frac
            except:
                preco_anterior = None

            # desconto
            try:
                desconto = produto.find_element(By.CSS_SELECTOR, ".andes-money-amount__discount, .poly-price__disc--pill").text.strip()
            except:
                desconto = None

            # parcelamento
            try:
                parcelamento = produto.find_element(By.CSS_SELECTOR, ".poly-price__installments").text.strip()
            except:
                parcelamento = None

            # frete
            try:
                frete = produto.find_element(By.CSS_SELECTOR, ".poly-component__shipping").text.strip()
            except:
                frete = None

            # imagem
            try:
                imagem = produto.find_element(By.CSS_SELECTOR, "img.poly-component__picture").get_attribute("src")
            except:
                imagem = None

            produtos_encontrados.append({
                "titulo": titulo,
                "preco_atual": preco_atual,
                "preco_anterior": preco_anterior,
                "desconto": desconto,
                "parcelamento": parcelamento,
                "frete": frete,
                "link": link,
                "imagem": imagem
            })

            # checar limite
            if len(produtos_encontrados) >= MAX_PRODUTOS:
                break

        except Exception as e:
            print("Erro extraindo um produto:", e)
            continue

    print("Coletados até agora:", len(produtos_encontrados))

    if len(produtos_encontrados) >= MAX_PRODUTOS:
        break

    # Tentar clicar no botão "Próxima" da paginação
    time.sleep(1)

    parsed = urlparse(driver.current_url)
    qs = parse_qs(parsed.query)
    try:
        current_page = int(qs.get("page", ["1"])[0])
    except:
        current_page = 1

    next_page_num = current_page + 1
    pattern = f"page={next_page_num}"

    clicou_proxima = False
    try:
        links = driver.find_elements(By.CSS_SELECTOR, "a.andes-pagination__link")
        for l in links:
            href = l.get_attribute("href") or ""
            if pattern in href:
                try:
                    l.click()
                    clicou_proxima = True
                    break
                except:
                    driver.execute_script("arguments[0].click();", l)
                    clicou_proxima = True
                    break
    except Exception as e:
        print("Erro procurando links de paginação:", e)
        clicou_proxima = False

    if not clicou_proxima:
        print(f"Link para a página {next_page_num} não encontrado — finalizando coleta.")
        break

    time.sleep(2)

# ---------------------------
# SALVAR OS RESULTADOS EM EXCEL
# ---------------------------
df = pd.DataFrame(produtos_encontrados, columns=[
    "titulo",
    "preco_atual",
    "preco_anterior",
    "desconto",
    "parcelamento",
    "frete",
    "link",
    "imagem"
])

output_path = os.path.join(os.getcwd(), "produtos.xlsx")
df.to_excel(output_path, index=False)

print(f"Arquivo salvo em: {output_path}")

driver.quit()
