import re
import time
import requests
import streamlit as st
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

st.set_page_config(page_title="Editor Contrapoder", page_icon="🗞️", layout="centered")

XGD_API_KEY = st.secrets.get("XGD_API_KEY", "")
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", "")

# === 1. FUNÇÕES DE ENCURTAMENTO E DETECÇÃO ===
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

# === 2. FORMATADOR 100% PYTHON (PLANO B INSTANTÂNEO) ===
def formatar_sem_ia(texto_encurtado, num_edicao, mes_ano):
    secoes_mapa = {
        "internacional": ("🌍", "Internacional"),
        "nacional": ("🇧🇷", "Nacional"),
        "colapso ambiental": ("🌳", "Colapso ambiental"),
        "barbárie": ("🩸", "Barbárie"),
        "barbarie": ("🩸", "Barbárie"),
        "leituras": ("📖", "Leituras"),
    }

    wpp_linhas = [
        "*Boletim Semanal do Contrapoder*",
        f"*número {num_edicao}*",
        mes_ano,
        "",
        "📢 *Se preferir receber por email, assine nossa newsletter:*",
        f"https://contrapoder.substack.com/p/{num_edicao}-boletim-semanal-do-contrapoder",
        ""
    ]
    sub_linhas = []
    itens_contrapoder = []

    linhas = [l.strip() for l in texto_encurtado.splitlines()]
    i = 0

    while i < len(linhas):
        linha = linhas[i]
        if not linha:
            i += 1
            continue

        chave_secao = re.sub(r'[^a-zA-Záéíóúâêôãõç\s]', '', linha).strip().lower()
        if chave_secao in secoes_mapa:
            emoji, nome = secoes_mapa[chave_secao]
            wpp_linhas.append(f"{emoji} *{nome}*")
            wpp_linhas.append("")
            sub_linhas.append(f"### {emoji} **{nome}**")
            sub_linhas.append("")
            i += 1
            continue

        if not linha.startswith("http"):
            manchete = re.sub(r'^[a-zA-Z0-9]{1,2}[\)\.\-]\s*', '', linha).strip()
            links_da_manchete = []
            j = i + 1
            while j < len(linhas) and (linhas[j].startswith("http") or linhas[j] == ""):
                if linhas[j].startswith("http"):
                    links_da_manchete.append(linhas[j])
                j += 1

            eh_contrapoder = any("(contrapoder)" in lk.lower() for lk in links_da_manchete)

            if eh_contrapoder:
                itens_contrapoder.append((manchete, links_da_manchete))
            else:
                emoji_item = "📌"
                if any(p in manchete.lower() for p in ["greve", "protesto", "marcha", "manifesta", "ato "]):
                    emoji_item = "✊"

                wpp_linhas.append(f"{emoji_item} *{manchete}*")
                for lk in links_da_manchete:
                    wpp_linhas.append(lk)
                wpp_linhas.append("")

                sub_linhas.append(f"{emoji_item} **{manchete}**")
                sub_linhas.append("")
                for lk in links_da_manchete:
                    m = re.match(r'(https?://\S+)(.*)', lk)
                    sub_linhas.append(f"[{m.group(1)}]({m.group(1)}){m.group(2)}" if m else lk)
                sub_linhas.append("")

            i = j
        else:
            wpp_linhas.append(linha)
            m = re.match(r'(https?://\S+)(.*)', linha)
            sub_linhas.append(f"[{m.group(1)}]({m.group(1)}){m.group(2)}" if m else linha)
            i += 1

    if itens_contrapoder:
        wpp_linhas.extend(["---", "🚫 CONTRAPODER:", "Leia nossos artigos de destaque diretamente no site:", ""])
        sub_linhas.extend(["---", "### 🚫 **CONTRAPODER:**", "Leia nossos artigos de destaque diretamente no site:", ""])
        for manchete, lks in itens_contrapoder:
            wpp_linhas.append(f"👉 *{manchete}*")
            for lk in lks:
                wpp_linhas.append(lk)
            wpp_linhas.append("")

            sub_linhas.append(f"👉 **{manchete}**")
            sub_linhas.append("")
            for lk in lks:
                m = re.match(r'(https?://\S+)(.*)', lk)
                sub_linhas.append(f"[{m.group(1)}]({m.group(1)}){m.group(2)}" if m else lk)
            sub_linhas.append("")

    wpp_linhas.extend([
        "💰 Apoie o Contrapoder:",
        "pix para 11951771614 (celular editor)"
    ])
    sub_linhas.extend([
        "📲 Participe do nosso canal do Whatsapp e receba o conteúdo em primeira mão!",
        "[https://whatsapp.com/channel/0029Vb8JyLPD8SDrxKt3p42j](https://whatsapp.com/channel/0029Vb8JyLPD8SDrxKt3p42j)"
    ])

    return "\n".join(wpp_linhas).strip(), "\n".join(sub_linhas).strip()

# === 3. FORMATAÇÃO COM GROQ (PRINCIPAL) ===
def listar_modelos_groq(api_key):
    url = "https://api.groq.com/openai/v1/models"
    headers = {"Authorization": f"Bearer {api_key}"}
    ignorar = ("whisper", "guard", "tts", "playai", "orpheus", "safeguard", "compound")

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            dados = resp.json().get("data", [])
            modelos = [
                m["id"] for m in dados
                if m.get("id") and not any(x in m["id"].lower() for x in ignorar)
            ]
            # Prioriza modelos maiores/mais recentes de texto
            def prioridade(nome):
                n = nome.lower()
                if "llama-4" in n or "70b" in n or "120b" in n:
                    return 0
                if "qwen" in n or "llama" in n or "gpt" in n:
                    return 1
                return 2

            modelos.sort(key=prioridade)
            if modelos:
                return modelos[:4]
    except Exception:
        pass
    return []

def formatar_com_groq(texto_encurtado, num_edicao, mes_ano, api_key):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    modelos = listar_modelos_groq(api_key)
    if not modelos:
        raise Exception("Nenhum modelo de texto disponível na sua conta Groq.")

    prompt = f"""Você é o editor técnico do "Boletim Semanal do Contrapoder".
Receba o texto abaixo (já com os links encurtados) e devolva EXATAMENTE duas versões separadas pela marcação "===SEPARADOR_SUBSTACK===". Não escreva nenhuma introdução ou comentário fora das versões.

REGRAS GERAIS:
1. Remova as letras de enumeração (a), b), c)...) das manchetes.
2. Adicione emojis temáticos adequados antes de cada manchete (substituindo eventuais 📌 genéricos). Em protestos, greves ou marchas, use ✊ (seguido da bandeira do país, quando aplicável).
3. Na seção Nacional, NÃO coloque a bandeira do Brasil (🇧🇷) nas chamadas individuais.
4. Mantenha os links exatamente como estão no texto recebido, incluindo as atribuições entre parênteses.
5. Qualquer texto do site contrapoder.net ("(contrapoder)") deve ser REMOVIDO da seção "Leituras" e colocado EXCLUSIVAMENTE no bloco final "🚫 CONTRAPODER:".

VERSÃO 1: WHATSAPP (texto puro com negrito usando *asteriscos*)
- Cabeçalho obrigatório:
*Boletim Semanal do Contrapoder*
*número {num_edicao}*
{mes_ano}

📢 *Se preferir receber por email, assine nossa newsletter:*
https://contrapoder.substack.com/p/{num_edicao}-boletim-semanal-do-contrapoder

- Seções: 🌍 *Internacional*, 🇧🇷 *Nacional*, 🌳 *Colapso ambiental*, 🩸 *Barbárie*, 📖 *Leituras*.
- Manchetes em *negrito* com os links logo na linha abaixo (sem linha em branco entre manchete e link).
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
- Seções: ### 🌍 **Internacional**, ### 🇧🇷 **Nacional**, ### 🌳 **Colapso ambiental**, ### 🩸 **Barbárie**, ### 📖 **Leituras**.
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

TEXTO DO BOLETIM PARA FORMATAR:
{texto_encurtado}
"""

    ultimo_erro = None
    for modelo in modelos:
        try:
            payload = {
                "model": modelo,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            if resp.status_code == 200:
                conteudo = resp.json()["choices"][0]["message"]["content"]
                partes = conteudo.split("===SEPARADOR_SUBSTACK===")
                return partes[0].strip(), (partes[1].strip() if len(partes) > 1 else ""), modelo
            else:
                ultimo_erro = Exception(f"{modelo} -> HTTP {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            ultimo_erro = e
            continue

    raise ultimo_erro

# === 4. INTERFACE WEB ===
st.title("🗞️ Editor do Boletim Contrapoder")
st.caption("Encurta links (x.gd), identifica canais/perfis e formata para WhatsApp e Substack.")

col1, col2 = st.columns(2)
with col1:
    num_edicao = st.text_input("Número da edição:", value="145")
with col2:
    mes_ano = st.text_input("Mês e Ano:", value="Novembro de 2026")

usar_ia = st.toggle(
    "Usar IA (Groq) para escolher emojis temáticos",
    value=True,
    help="Se desligado — ou se a Groq estiver fora do ar — o app formata instantaneamente em Python."
)
pular_encurtamento = st.toggle(
    "Links já estão encurtados (pular etapa do x.gd)",
    value=False,
    help="Ative se você já tem o texto com links x.gd e quer apenas que a Groq formate e coloque os emojis."
)

if not pular_encurtamento and not XGD_API_KEY:
    XGD_API_KEY = st.text_input("Chave da API x.gd:", type="password")
if usar_ia and not GROQ_API_KEY:
    GROQ_API_KEY = st.text_input("Chave da API Groq:", type="password")

texto_entrada = st.text_area("Cole o rascunho do boletim:", height=280)

if st.button("Encurtar e Formatar Boletim", type="primary", use_container_width=True):
    if not pular_encurtamento and not XGD_API_KEY:
        st.error("Configure a chave XGD_API_KEY nos Secrets (ou no campo acima).")
    elif not texto_entrada.strip():
        st.warning("Cole o texto do boletim antes de continuar.")
    else:
        texto_encurtado = texto_entrada

        if not pular_encurtamento:
            regex = r'https?://[^\s<>"{}|\\^`[\]]+'
            links = re.findall(regex, texto_entrada)
            links_unicos = [l for l in dict.fromkeys(links) if "x.gd/" not in l]

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

        st.session_state["texto_encurtado"] = texto_encurtado

        if usar_ia and GROQ_API_KEY:
            with st.spinner("Formatando com Groq..."):
                try:
                    wpp, sub, modelo_usado = formatar_com_groq(texto_encurtado, num_edicao, mes_ano, GROQ_API_KEY)
                    st.session_state["resultado"] = (wpp, sub, f"Formatado com Groq ({modelo_usado})")
                except Exception as e:
                    wpp, sub = formatar_sem_ia(texto_encurtado, num_edicao, mes_ano)
                    st.session_state["resultado"] = (wpp, sub, f"Groq indisponível ({e}) — formatado automaticamente em Python!")
        else:
            wpp, sub = formatar_sem_ia(texto_encurtado, num_edicao, mes_ano)
            st.session_state["resultado"] = (wpp, sub, "Formatado instantaneamente em Python (sem IA).")

if "resultado" in st.session_state:
    versao_wpp, versao_sub, msg_status = st.session_state["resultado"]
    st.info(msg_status)

    aba_wpp, aba_sub, aba_bruto = st.tabs(["📱 WhatsApp", "💻 Substack", "🔗 Links Encurtados"])

    with aba_wpp:
        st.caption("Clique no ícone de copiar no canto superior direito da caixa abaixo:")
        st.code(versao_wpp, language="text")

    with aba_sub:
        st.caption("Selecione o texto abaixo e copie (Ctrl+C / Cmd+C) para colar no Substack:")
        st.markdown(versao_sub)
        with st.expander("Ver código Markdown bruto"):
            st.code(versao_sub, language="markdown")

    with aba_bruto:
        st.code(st.session_state.get("texto_encurtado", ""), language="text")
