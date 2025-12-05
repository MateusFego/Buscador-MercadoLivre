from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import pandas as pd
import os

# ==============================
# CONFIGURAÇÃO DO NAVEGADOR
# ==============================
options = webdriver.ChromeOptions()
# Se der problema com Wayland, você pode testar:
# options.add_argument("--ozone-platform=wayland")
# options.add_argument("--enable-features=UseOzonePlatform")

driver = webdriver.Chrome(options=options)

# Hyprland: garante uma janela "decente"
driver.set_window_size(1400, 900)
driver.set_window_position(0, 0)

wait = WebDriverWait(driver, 20)

# ==============================
# ABRIR KABUM E IR PARA OFERTAS
# ==============================
driver.get("https://www.kabum.com.br/")
time.sleep(2)

# (Opcional) Tentar fechar banner de cookies se aparecer
try:
    botao_cookies = WebDriverWait(driver, 5).until(
        EC.element_to_be_clickable(
            (By.XPATH, '//*[@id="header-container"]/header/div/div[2]/div[2]/div/div[2]/div[2]/a[1]')
        )
    )
    botao_cookies.click()
    time.sleep(1)
except:
    pass  # se não tiver banner, segue o jogo

# Clicar no link de ofertas
botao_ofertas = wait.until(
    EC.element_to_be_clickable(
        (By.XPATH, '//a[contains(@href, "/ofertas")]')
    )
)
botao_ofertas.click()
time.sleep(3)

# ==============================
# APLICAR FILTRO DE PREÇO 100–150
# ==============================

# Campo mínimo
seletor_minimo = wait.until(
    EC.presence_of_element_located((By.ID, "minPrice"))
)

# Scroll suave até o campo (evita flick no Hyprland)
driver.execute_script(
    "arguments[0].scrollIntoView({block: 'center'});", seletor_minimo
)
time.sleep(1)

seletor_minimo.click()
seletor_minimo.clear()
seletor_minimo.send_keys("100")
time.sleep(1)

# Campo máximo
seletor_maximo = wait.until(
    EC.presence_of_element_located((By.ID, "maxPrice"))
)
driver.execute_script(
    "arguments[0].scrollIntoView({block: 'center'});", seletor_maximo
)
time.sleep(1)

seletor_maximo.click()
seletor_maximo.clear()
seletor_maximo.send_keys("150")
time.sleep(1)

# Aplica o filtro (Kabum geralmente aplica ao perder o foco)
seletor_maximo.send_keys(Keys.TAB)
time.sleep(3)

# ==============================
# COLETAR PRODUTOS (PRIMEIRA PÁGINA)
# ==============================

MAX_PRODUTOS = 300
produtos_encontrados = []

# Tenta pegar os cards de produto
# IMPORTANTE: se esse seletor não bater, abra o Kabum, inspecione um card,
# veja algum atributo padrão (ex: data-testid, class) e ajuste aqui.
cards = wait.until(
    EC.presence_of_all_elements_located(
        (By.CSS_SELECTOR, '[data-testid="product-card"], div[data-sku]')
    )
)

for card in cards:
    if len(produtos_encontrados) >= MAX_PRODUTOS:
        break

    try:
        # ---------- TÍTULO ----------
        try:
            # AJUSTAR SELETOR se necessário
            titulo = card.find_element(
                By.CSS_SELECTOR,
                '[data-testid="product-card-name"], h2, h3'
            ).text.strip()
        except:
            titulo = card.text.split("\n")[0].strip() or None

        # ---------- PREÇO ATUAL ----------
        try:
            # AJUSTAR SELETOR se necessário
            preco_texto = card.find_element(
                By.CSS_SELECTOR,
                '[data-testid="product-card-price"], span'
            ).text

            # normalizar número (tenta transformar em algo tipo "123,45")
            # e guardar como string mesmo (igual ML)
            # Kabum costuma usar "R$ 123,45"
            preco_limpo = preco_texto.replace("R$", "").strip()
            preco_atual = preco_limpo
        except:
            preco_atual = None

        # ---------- PREÇO ANTERIOR (NEM SEMPRE TEM) ----------
        try:
            # AJUSTAR SELETOR se necessário
            preco_ant_texto = card.find_element(
                By.XPATH,
                ".//*[contains(text(), 'De:') or contains(text(), 'R$')]"
            ).text
            # aqui dá pra refinar igual acima, se você quiser
            preco_anterior = preco_ant_texto
        except:
            preco_anterior = None

        # ---------- DESCONTO / PARCELAMENTO / FRETE ----------
        # Essas infos variam muito de layout pra layout, então deixei
        # tentativas genéricas. Você pode ir refinando depois no inspecionar.
        try:
            desconto = card.find_element(
                By.XPATH,
                ".//*[contains(text(), '%')]"
            ).text.strip()
        except:
            desconto = None

        try:
            parcelamento = card.find_element(
                By.XPATH,
                ".//*[contains(text(), 'x ')]"
            ).text.strip()
        except:
            parcelamento = None

        try:
            frete = card.find_element(
                By.XPATH,
                ".//*[contains(text(), 'Frete') or contains(text(), 'grátis')]"
            ).text.strip()
        except:
            frete = None

        # ---------- LINK ----------
        try:
            link = card.find_element(By.TAG_NAME, "a").get_attribute("href")
        except:
            link = None

        # ---------- IMAGEM ----------
        try:
            imagem = card.find_element(By.TAG_NAME, "img").get_attribute("src")
        except:
            imagem = None

        # Se quiser garantir só preços entre 100 e 150 mesmo:
        try:
            valor_num = float(
                preco_atual.replace(".", "").replace(",", ".")
            )
            if not (100 <= valor_num <= 150):
                # pula se sair da faixa
                continue
        except:
            # se não conseguir converter, deixa passar
            pass

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

    except Exception as e:
        print("Erro extraindo um produto:", e)
        continue

print("Total coletado na primeira página:", len(produtos_encontrados))

# ==============================
# SALVAR EM EXCEL
# ==============================
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

output_path = os.path.join(os.getcwd(), "produtos_kabum.xlsx")
df.to_excel(output_path, index=False)

print(f"Arquivo salvo em: {output_path}")

driver.quit()
