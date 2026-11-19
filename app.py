import re
import time
import requests
import streamlit as st
from google import genai
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

st.set_page_config(page_title="Editor Contrapoder", page_icon="🗞️", layout="centered")

# Chaves configuradas nos Secrets do Streamlit
XGD_API_KEY = st.secrets.get("XGD_API_KEY", "")
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")

# === FUNÇÕES DE ENCURTAMENTO E DETECÇÃO ===
def limpar_url_para_encurtar(url):
    try:
        parsed = urlparse(url)
        query_params = parse_qsl(parsed.query)
        params_rastreamento = ('utm_', 'igsh', 'wa_logging_event', 'si', 'mc_cid', 'srtk', 'psln')
        query_limpa = [
            (k, v) for k, v in query_params
            if not any(k.startswith(p) for p in params_rastreamento)
        ]
        nova_query = urlencode(query_limpa)
        url_limpa = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, nova_query, parsed.fragment))
        return url_limpa[:-1] if url_limpa.endswith('?') else url_limpa
    except Exception:
        return url

def obter_canal_youtube(url):
    try:
        resp = requests.get("https://www.youtube.com/oembed", params={"url": url, "format": "json"}, timeout=10)
        if resp.status_code == 200:
            canal = resp.json().get("author_name", "").strip()
            if canal:
                return canal
    except Exception:
        pass
    return None

def obter_perfil_instagram(url):
    try:
        parsed = urlparse(url)
        partes = [p for p in parsed.path.split('/') if p]
        rotas_sistema = {'p', 'reel', 'reels', 'tv', 'stories', 'explore', 'accounts'}

        if len(partes) >= 2 and partes[0].lower() not in rotas_sistema:
            return partes[0]

        match_id = re.search(r'/(p|reel|reels|tv)/([^/?#&]+)', parsed.path)
        if match_id:
            tipo, shortcode = match_id.group(1), match_id.group(2)
            embed_url = f"https://www.instagram.com/{tipo}/{shortcode}/embed/"
            resp_embed = requests.get(embed_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            if resp_embed.status_code == 200:
                for padrao in [
                    r'class="UsernameText"[^>]*>([a-zA-Z0-9._]+)<',
                    r'"username"\s*:\s*"([a-zA-Z0-9._]+)"',
                    r'instagram\.com/([a-zA-Z0-9._]+)/\?utm_source=ig_embed'
                ]:
                    m = re.search(padrao, resp_embed.text)
                    if m and m.group(1).lower() not in rotas_sistema:
                        return m.group(1)

        resp_bot = requests.get(url, headers={"User-Agent": "facebookexternalhit/1.1"}, timeout=10)
        if resp_bot.status_code == 200:
            m = re.search(r'\(@([a-zA-Z0-9._]+)\)', resp_bot.text)
            if m:
                return m.group(1)
    except Exception:
        pass
    return None

def extrair_dominio(url):
    try:
        parsed = urlparse(url)
        dominio = parsed.netloc.replace('www.', '')
        if dominio.startswith('m.'):
            dominio = dominio[2:]

        if 'youtube.com' in dominio or 'youtu.be' in dominio:
            canal = obter_canal_youtube(url)
            return f"youtube/{canal}" if canal else "youtube"

        if 'instagram.com' in dominio:
            perfil = obter_perfil_instagram(url)
            return f"instagram/{perfil}" if perfil else "instagram"

        dominios_conhecidos = {
            'telesurtv': 'telesurtv', 'brasildefato': 'brasildefato',
            'resumenlatinoamericano': 'resumenlatinoamericano', 'rebelion': 'rebelion',
            'esquerdadiario': 'esquerdadiario', 'opiniaosocialista': 'opiniaosocialista',
            'aterraeredonda': 'aterraeredonda', 'tradingeconomics': 'tradingeconomics',
            'soundcloud': 'soundcloud', 'outraspalavras': 'outraspalavras',
            'cartacapital': 'cartacapital', 'folha': 'folha', 'uol': 'uol',
            'agenciabrasil': 'agenciabrasil', 'ponte': 'ponte', 'metsul': 'metsul',
            'operamundi': 'operamundi', 'thenextrecession': 'thenextrecession',
            'economia': 'economia', 'estadao': 'estadao', 'brasil247': 'brasil247',
            'jornaldaorla': 'jornaldaorla', 'agencia': 'agencia', 'oglobo': 'oglobo',
            'g1': 'g1', 'mronline': 'mronline', 'ricardoantunes': 'ricardoantunes',
            'contrapoder': 'contrapoder'
        }

        for chave, valor in dominios_conhecidos.items():
            if chave in dominio:
                return valor

        partes = dominio.split('.')
        return partes[0] if len(partes) >= 2 else dominio
    except Exception:
        return "desconhecido"

def encurtar_link_xgd(url, api_key, tentativas=3):
    url_limpa = limpar_url_para_encurtar(url)
    endpoint = "https://xgd.io/V1/shorten"
    params = {"url": url_limpa, "key": api_key}

    for i in range(tentativas):
        try:
            response = requests.get(endpoint, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                if data.get("shorturl"):
                    time.sleep(1.5)
                    return data["shorturl"]
            if i < tentativas - 1:
                time.sleep(3)
        except Exception:
            if i < tentativas - 1:
                time.sleep(3)
    return url

# === FORMATAÇÃO COM GEMINI ===
def formatar_boletim(texto_encurtado, num_edicao, mes_ano, api_key):
    client = genai.Client(api_key=api_key)

    prompt = f"""Você é o editor técnico do "Boletim Semanal do Contrapoder".
Receba o texto abaixo (já com os links encurtados) e devolva EXATAMENTE duas versões separadas pela marcação "===SEPARADOR_SUBSTACK===". Não escreva nenhuma introdução ou comentário fora das versões.

REGRAS GERAIS:
1. Remova as letras de enumeração (a), b), c)...) das manchetes.
2. Adicione emojis temáticos adequados antes de cada manchete. Em protestos, greves ou marchas, use o punho ✊ (seguido da bandeira do país, quando aplicável).
3. Na seção Nacional, NÃO coloque a bandeira do Brasil (🇧🇷) nas chamadas individuais (pois a bandeira já está no título da seção).
4. Mantenha os links exatamente como estão no texto recebido, incluindo as atribuições entre parênteses.
5. Qualquer texto/artigo do site contrapoder.net (identificado por "(contrapoder)") deve ser REMOVIDO da seção "Leituras" e colocado EXCLUSIVAMENTE no bloco final "🚫 CONTRAPODER:".

---
VERSÃO 1: WHATSAPP (texto puro com formatação de negrito do WhatsApp usando *asteriscos*)
- Cabeçalho obrigatório:
*Boletim Semanal do Contrapoder*
*número {num_edicao}*
{mes_ano}

📢 *Se preferir receber por email, assine nossa newsletter:*
https://contrapoder.substack.com/p/{num_edicao}-boletim-semanal-do-contrapoder

- Títulos das seções: 🌍 *Internacional*, 🇧🇷 *Nacional*, 🌳 *Colapso ambiental*, 🩸 *Barbárie*, 📖 *Leituras*.
- Manchetes em *negrito* com os links logo na linha abaixo (sem linha em branco entre a manchete e o primeiro link).
- Bloco final (se houver textos do contrapoder):
---
🚫 CONTRAPODER:
Leia nossos artigos de destaque diretamente no site:

👉 *Autor, "Título"*
link (contrapoder)

- Rodapé obrigatório:
💰 Apoie o Contrapoder:
pix para 11951771614 (celular editor)

===SEPARADOR_SUBSTACK===

VERSÃO 2: SUBSTACK (Markdown rico)
- NÃO coloque cabeçalho. Comece diretamente em: ### 🌍 **Internacional**
- Títulos das seções: ### 🌍 **Internacional**, ### 🇧🇷 **Nacional**, ### 🌳 **Colapso ambiental**, ### 🩸 **Barbárie**, ### 📖 **Leituras**.
- Manchetes em **negrito**. Pule UMA linha simples após a manchete antes de listar os links.
- Formate cada link em Markdown clicável: [url](url) (fonte) — um link por linha.
- Bloco final (se houver textos do contrapoder):
---
### 🚫 **CONTRAPODER:**
Leia nossos artigos de destaque diretamente no site:

👉 **Autor, "Título"**
[url](url) (contrapoder)

- Rodapé obrigatório (apenas isso):
📲 Participe do nosso canal do Whatsapp e receba o conteúdo em primeira mão!
[https://whatsapp.com/channel/0029Vb8JyLPD8SDrxKt3p42j](https://whatsapp.com/channel/0029Vb8JyLPD8SDrxKt3p42j)

---
TEXTO DO BOLETIM PARA FORMATAR:
{texto_encurtado}
"""

    for tentativa in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=prompt,
            )
            return response.text
        except Exception as e:
            if "503" in str(e) and tentativa < 2:
                time.sleep(4)
                continue
            raise e

# === INTERFACE WEB ===
st.title("🗞️ Editor do Boletim Contrapoder")
st.caption("Encurta links (x.gd), identifica canais/perfis e formata automaticamente para WhatsApp e Substack.")

col1, col2 = st.columns(2)
with col1:
    num_edicao = st.text_input("Número da edição:", value="145")
with col2:
    mes_ano = st.text_input("Mês e Ano:", value="Novembro de 2026")

if not XGD_API_KEY:
    XGD_API_KEY = st.text_input("Chave da API x.gd:", type="password")
if not GEMINI_API_KEY:
    GEMINI_API_KEY = st.text_input("Chave da API Gemini:", type="password")

texto_entrada = st.text_area("Cole o rascunho do boletim com os links originais:", height=300)

if st.button("Encurtar e Formatar Boletim", type="primary", use_container_width=True):
    if not XGD_API_KEY or not GEMINI_API_KEY:
        st.error("Configure as chaves XGD_API_KEY e GEMINI_API_KEY nos Secrets (ou nos campos acima).")
    elif not texto_entrada.strip():
        st.warning("Cole o texto do boletim antes de continuar.")
    else:
        # Etapa 1: Encurtamento
        regex = r'https?://[^\s<>"{}|\\^`[\]]+'
        links = re.findall(regex, texto_entrada)
        links_unicos = list(dict.fromkeys(links))

        texto_encurtado = texto_entrada
        if links_unicos:
            barra = st.progress(0)
            status = st.empty()
            links_encurtados = {}

            for i, link in enumerate(links_unicos, 1):
                status.text(f"Encurtando {i}/{len(links_unicos)}: {link[:60]}...")
                dominio = extrair_dominio(link)
                link_curto = encurtar_link_xgd(link, XGD_API_KEY)
                links_encurtados[link] = f"{link_curto} ({dominio})"
                barra.progress(i / len(links_unicos))

            for link_original, link_formatado in sorted(links_encurtados.items(), key=lambda x: len(x[0]), reverse=True):
                texto_encurtado = texto_encurtado.replace(link_original, link_formatado)

            status.success(f"{len(links_unicos)} links encurtados!")

        # Etapa 2: Formatação via Gemini
        with st.spinner("Formatando versões para WhatsApp e Substack..."):
            try:
                resultado = formatar_boletim(texto_encurtado, num_edicao, mes_ano, GEMINI_API_KEY)
                partes = resultado.split("===SEPARADOR_SUBSTACK===")
                versao_wpp = partes[0].strip()
                versao_sub = partes[1].strip() if len(partes) > 1 else ""

                aba_wpp, aba_sub, aba_bruto = st.tabs(["📱 WhatsApp", "💻 Substack", "🔗 Links Encurtados"])

                with aba_wpp:
                    st.caption("Clique no ícone de copiar no canto superior direito da caixa abaixo:")
                    st.code(versao_wpp, language="text")

                with aba_sub:
                    st.info("Selecione o texto abaixo e copie (Ctrl+C / Cmd+C) para colar direto no editor visual do Substack.")
                    st.markdown(versao_sub)
                    with st.expander("Ver código Markdown bruto"):
                        st.code(versao_sub, language="markdown")

                with aba_bruto:
                    st.code(texto_encurtado, language="text")

            except Exception as e:
                st.error(f"Erro ao formatar com o Gemini: {e}")
                st.warning("A formatação automática falhou, mas os links já foram encurtados abaixo (clique no ícone no canto superior direito para copiar):")
                st.code(texto_encurtado, language="text")
                st.download_button(
                    label="⬇️ Baixar texto com links encurtados",
                    data=texto_encurtado,
                    file_name="texto_encurtado.txt",
                    mime="text/plain",
                    use_container_width=True
                )
                
