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

# === 2. PARSER ESTRUTURAL (PYTHON) ===
SECOES_MAPA = {
    "internacional": ("🌍", "Internacional"),
    "nacional": ("🇧🇷", "Nacional"),
    "colapso ambiental": ("🌳", "Colapso ambiental"),
    "barbárie": ("🩸", "Barbárie"),
    "barbarie": ("🩸", "Barbárie"),
    "leituras": ("📖", "Leituras"),
}

BANDEIRAS_PAISES = [
    (r'\b(eua|estados unidos|norte-american[oa]s?|washington|trump|casa branca)\b', '🇺🇸'),
    (r'\b(cuba|cuban[oa]s?|havana)\b', '🇨🇺'),
    (r'\b(venezuela|venezuelan[oa]s?|caracas)\b', '🇻🇪'),
    (r'\b(argentina|argentin[oa]s?|buenos aires|milei)\b', '🇦🇷'),
    (r'\b(chile|chilen[oa]s?|santiago)\b', '🇨🇱'),
    (r'\b(colômbia|colombia|colombian[oa]s?|bogotá|petro)\b', '🇨🇴'),
    (r'\b(méxico|mexico|mexican[oa]s?)\b', '🇲🇽'),
    (r'\b(bolívia|bolivia|bolivian[oa]s?)\b', '🇧🇴'),
    (r'\b(peru|peruan[oa]s?|lima)\b', '🇵🇪'),
    (r'\b(equador|equatorian[oa]s?|quito)\b', '🇪🇨'),
    (r'\b(uruguai|uruguai[oa]s?|montevidéu)\b', '🇺🇾'),
    (r'\b(paraguai|paraguai[oa]s?)\b', '🇵🇾'),
    (r'\b(haiti|haitian[oa]s?)\b', '🇭🇹'),
    (r'\b(palestina|palestin[oa]s?|gaza|cisjordânia)\b', '🇵🇸'),
    (r'\b(israel|israelenses?|tel aviv|netanyahu)\b', '🇮🇱'),
    (r'\b(líbano|libano|libanes[ea]s?|beirute)\b', '🇱🇧'),
    (r'\b(irã|ira|iranian[oa]s?|teerã)\b', '🇮🇷'),
    (r'\b(síria|siria|síri[oa]s?)\b', '🇸🇾'),
    (r'\b(iêmen|iemen|iemenitas?)\b', '🇾🇪'),
    (r'\b(china|chines[ea]s?|pequim)\b', '🇨🇳'),
    (r'\b(rússia|russia|russ[oa]s?|moscou|putin)\b', '🇷🇺'),
    (r'\b(ucrânia|ucrania|ucranian[oa]s?|kiev)\b', '🇺🇦'),
    (r'\b(frança|franca|frances[ea]s?|paris|macron)\b', '🇫🇷'),
    (r'\b(alemanha|alemã(?:es)?|alemão|berlim)\b', '🇩🇪'),
    (r'\b(reino unido|inglaterra|britânic[oa]s?|londres)\b', '🇬🇧'),
    (r'\b(espanha|espanh[óo]is|espanhol[ae]?|madri)\b', '🇪🇸'),
    (r'\b(itália|italia|italian[oa]s?|roma)\b', '🇮🇹'),
    (r'\b(portugal|portugues[ea]s?|lisboa)\b', '🇵🇹'),
    (r'\b(índia|india|indian[oa]s?)\b', '🇮🇳'),
    (r'\b(japão|japao|japones[ea]s?|tóquio)\b', '🇯🇵'),
    (r'\b(coreia do sul|sul-corean[oa]s?)\b', '🇰🇷'),
    (r'\b(coreia do norte|norte-corean[oa]s?)\b', '🇰🇵'),
    (r'\b(áfrica do sul|sul-african[oa]s?)\b', '🇿🇦'),
    (r'\b(canadá|canada|canadenses?)\b', '🇨🇦'),
    (r'\b(austrália|australia|australian[oa]s?)\b', '🇦🇺'),
    (r'\b(turquia|turc[oa]s?)\b', '🇹🇷'),
    (r'\b(egito|egípci[oa]s?)\b', '🇪🇬'),
    (r'\b(sudão|sudao|sudanes[ea]s?)\b', '🇸🇩'),
    (r'\b(congo|congoles[ea]s?)\b', '🇨🇩'),
    (r'\b(nicarágua|nicaragua|nicaraguenses?)\b', '🇳🇮'),
    (r'\b(el salvador|salvadorenh[oa]s?)\b', '🇸🇻'),
    (r'\b(honduras|hondurenh[oa]s?)\b', '🇭🇳'),
    (r'\b(panamá|panama|panamenh[oa]s?)\b', '🇵🇦'),
    (r'\b(brasil|brasileir[oa]s?)\b', '🇧🇷'),
]

def limpar_link_markdown(linha):
    # Converte [url](url) (fonte) de volta para url (fonte) caso venha do Substack
    return re.sub(r'\[(https?://[^\]]+)\]\(\1\)', r'\1', linha).strip()

def limpar_manchete(linha):
    texto = linha.strip()
    # Remove negrito markdown/wpp nas pontas
    texto = re.sub(r'^[*_#]+\s*', '', texto)
    texto = re.sub(r'\s*[*_]+$', '', texto)
    # Remove emojis/símbolos antigos no início da linha
    texto = re.sub(r'^[^\w"“\'(\[]+\s*', '', texto)
    # Remove enumeração tipo a), b., 1)
    texto = re.sub(r'^[a-zA-Z0-9]{1,2}[\)\.\-]\s*', '', texto)
    # Limpa asteriscos residuais nas pontas
    texto = texto.strip('*_ ').strip()
    return texto

def eh_linha_ignoravel(linha, mes_ano):
    low = linha.lower().strip('*_ ')
    if not low or low == '---':
        return True
    padroes = [
        'boletim semanal do contrapoder',
        'número ',
        'numero ',
        'se preferir receber por email',
        'contrapoder.substack.com',
        'apoie o contrapoder',
        'pix para ',
        'participe do nosso canal do whatsapp',
        'whatsapp.com/channel',
        'leia nossos artigos de destaque',
    ]
    if any(p in low for p in padroes):
        return True
    if mes_ano and low == mes_ano.lower().strip():
        return True
    return False

def extrair_estrutura(texto_encurtado, mes_ano):
    secoes = []
    secao_atual = None
    itens_contrapoder = []
    em_bloco_contrapoder = False

    linhas = [limpar_link_markdown(l.strip()) for l in texto_encurtado.splitlines()]
    i = 0

    while i < len(linhas):
        linha = linhas[i]

        if eh_linha_ignoravel(linha, mes_ano):
            i += 1
            continue

        chave_limpa = re.sub(r'[^a-zA-Záéíóúâêôãõç\s]', '', linha).strip().lower()

        if chave_limpa == "contrapoder":
            em_bloco_contrapoder = True
            i += 1
            continue

        if chave_limpa in SECOES_MAPA:
            em_bloco_contrapoder = False
            emoji, nome = SECOES_MAPA[chave_limpa]
            secao_atual = {"chave": chave_limpa, "emoji": emoji, "nome": nome, "itens": []}
            secoes.append(secao_atual)
            i += 1
            continue

        if not linha.startswith("http"):
            manchete = limpar_manchete(linha)
            links_da_manchete = []
            j = i + 1
            while j < len(linhas):
                prox = linhas[j]
                if prox == "":
                    j += 1
                    continue
                if prox.startswith("http"):
                    links_da_manchete.append(prox)
                    j += 1
                else:
                    break

            eh_contrapoder = em_bloco_contrapoder or any("(contrapoder)" in lk.lower() for lk in links_da_manchete)

            if eh_contrapoder:
                itens_contrapoder.append({"manchete": manchete, "links": links_da_manchete})
            else:
                if secao_atual is None:
                    secao_atual = {"chave": "geral", "emoji": "🗞️", "nome": "Destaques", "itens": []}
                    secoes.append(secao_atual)
                secao_atual["itens"].append({"manchete": manchete, "links": links_da_manchete})

            i = j
        else:
            # Link solto sem manchete
            if secao_atual and secao_atual["itens"]:
                secao_atual["itens"][-1]["links"].append(linha)
            i += 1

    return secoes, itens_contrapoder

def emoji_fallback_python(secao_chave, manchete):
    low = manchete.lower()
    eh_protesto = any(p in low for p in ["greve", "protesto", "marcha", "manifesta", "ato ", "mobiliza"])

    if secao_chave == "internacional":
        bandeiras = []
        for padrao, flag in BANDEIRAS_PAISES:
            if re.search(padrao, low) and flag not in bandeiras:
                bandeiras.append(flag)
        if bandeiras:
            prefixo = "✊" if eh_protesto else ""
            return prefixo + "".join(bandeiras[:3])

    if eh_protesto:
        return "✊"
    return "📌"

# === 3. GROQ APENAS PARA ESCOLHER EMOJIS (RÁPIDO E SEM CORTES) ===
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

def escolher_emojis_groq(secoes, api_key):
    lista_manchetes = []
    idx = 1
    for sec in secoes:
        for item in sec["itens"]:
            lista_manchetes.append((idx, sec["chave"], sec["nome"], item["manchete"]))
            idx += 1

    if not lista_manchetes:
        return {}, "nenhum item"

    modelos = listar_modelos_groq(api_key)
    if not modelos:
        raise Exception("Nenhum modelo de texto disponível na sua conta Groq.")

    linhas_prompt = "\n".join(
        f"{n}. [{sec_nome}] {manchete}"
        for n, _, sec_nome, manchete in lista_manchetes
    )

    prompt = f"""Escolha o(s) emoji(s) ideal(is) para cada manchete abaixo do Boletim Semanal do Contrapoder.

REGRAS OBRIGATÓRIAS:
1. Responda EXCLUSIVAMENTE no formato "NÚMERO: EMOJI" (uma linha por item, sem explicações, sem repetir o texto).
2. Na seção [Internacional]: SEMPRE que um ou mais países forem citados (ou gentílicos/capitais/governantes de países), coloque a(s) bandeira(s) desse(s) país(es). Ex: Cuba -> 🇨🇺; EUA e Venezuela -> 🇺🇸🇻🇪; Chile -> 🇨🇱. Se não citar nenhum país, escolha 1 emoji temático.
3. Em protestos, greves, marchas ou manifestações: use ✊ (e, se for [Internacional] com país citado, use ✊ seguido da bandeira, ex: ✊🇦🇷).
4. Na seção [Nacional]: NUNCA use a bandeira do Brasil (🇧🇷). Escolha 1 emoji temático adequado ao assunto.
5. Nas demais seções ([Colapso ambiental], [Barbárie], [Leituras]): escolha 1 emoji temático adequado ao assunto.

MANCHETES:
{linhas_prompt}
"""

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    ultimo_erro = None
    for modelo in modelos:
        try:
            payload = {
                "model": modelo,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "max_tokens": 1200
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=45)
            if resp.status_code == 200:
                texto_resp = resp.json()["choices"][0]["message"]["content"]
                emojis_map = {}
                for linha in texto_resp.splitlines():
                    m = re.match(r'^\s*(\d+)\s*[:\-\.]\s*(.+?)\s*$', linha)
                    if m:
                        num = int(m.group(1))
                        emoji_escolhido = m.group(2).strip().split()[0]
                        emojis_map[num] = emoji_escolhido
                if emojis_map:
                    return emojis_map, modelo
                ultimo_erro = Exception(f"{modelo} retornou resposta fora do formato esperado.")
            else:
                ultimo_erro = Exception(f"{modelo} -> HTTP {resp.status_code}: {resp.text[:180]}")
        except Exception as e:
            ultimo_erro = e
            continue

    raise ultimo_erro

# === 4. MONTAGEM DETERMINÍSTICA (WHATSAPP + SUBSTACK) ===
def montar_boletins(secoes, itens_contrapoder, emojis_map, num_edicao, mes_ano):
    wpp = [
        "*Boletim Semanal do Contrapoder*",
        f"*número {num_edicao}*",
        mes_ano,
        "",
        "📢 *Se preferir receber por email, assine nossa newsletter:*",
        f"https://contrapoder.substack.com/p/{num_edicao}-boletim-semanal-do-contrapoder",
        ""
    ]
    sub = []

    idx = 1
    for sec in secoes:
        if not sec["itens"]:
            continue

        wpp.append(f"{sec['emoji']} *{sec['nome']}*")
        wpp.append("")
        sub.append(f"### {sec['emoji']} **{sec['nome']}**")
        sub.append("")

        for item in sec["itens"]:
            emoji_item = emojis_map.get(idx) or emoji_fallback_python(sec["chave"], item["manchete"])

            # Blindagem: nunca permite bandeira do Brasil nas chamadas individuais do Nacional
            if sec["chave"] == "nacional":
                emoji_item = emoji_item.replace("🇧🇷", "").strip() or emoji_fallback_python("nacional", item["manchete"])

            # Blindagem: garante bandeira no Internacional se um país foi citado e a IA esqueceu
            if sec["chave"] == "internacional":
                bandeiras_detectadas = []
                low = item["manchete"].lower()
                for padrao, flag in BANDEIRAS_PAISES:
                    if re.search(padrao, low) and flag not in bandeiras_detectadas:
                        bandeiras_detectadas.append(flag)
                for flag in bandeiras_detectadas[:3]:
                    if flag not in emoji_item:
                        emoji_item = f"{emoji_item}{flag}" if emoji_item == "✊" else "".join(bandeiras_detectadas[:3])
                        break

            wpp.append(f"{emoji_item} *{item['manchete']}*")
            for lk in item["links"]:
                wpp.append(lk)
            wpp.append("")

            sub.append(f"{emoji_item} **{item['manchete']}**")
            sub.append("")
            for lk in item["links"]:
                m = re.match(r'(https?://\S+)(.*)', lk)
                sub.append(f"[{m.group(1)}]({m.group(1)}){m.group(2)}" if m else lk)
            sub.append("")

            idx += 1

    if itens_contrapoder:
        wpp.extend(["---", "🚫 CONTRAPODER:", "Leia nossos artigos de destaque diretamente no site:", ""])
        sub.extend(["---", "### 🚫 **CONTRAPODER:**", "Leia nossos artigos de destaque diretamente no site:", ""])

        for item in itens_contrapoder:
            wpp.append(f"👉 *{item['manchete']}*")
            for lk in item["links"]:
                wpp.append(lk)
            wpp.append("")

            sub.append(f"👉 **{item['manchete']}**")
            sub.append("")
            for lk in item["links"]:
                m = re.match(r'(https?://\S+)(.*)', lk)
                sub.append(f"[{m.group(1)}]({m.group(1)}){m.group(2)}" if m else lk)
            sub.append("")

    wpp.extend([
        "💰 Apoie o Contrapoder:",
        "pix para 11951771614 (celular editor)"
    ])
    sub.extend([
        "📲 Participe do nosso canal do Whatsapp e receba o conteúdo em primeira mão!",
        "[https://whatsapp.com/channel/0029Vb8JyLPD8SDrxKt3p42j](https://whatsapp.com/channel/0029Vb8JyLPD8SDrxKt3p42j)"
    ])

    return "\n".join(wpp).strip(), "\n".join(sub).strip()

# === 5. INTERFACE WEB ===
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
    help="A IA escolhe apenas os emojis; o Python monta todo o texto para nunca cortar nem alterar links."
)
pular_encurtamento = st.toggle(
    "Links já estão encurtados (pular etapa do x.gd)",
    value=False,
    help="Ative se você já tem o texto com links x.gd e quer apenas formatar e colocar os emojis."
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
        secoes, itens_contrapoder = extrair_estrutura(texto_encurtado, mes_ano)

        emojis_map = {}
        msg_status = "Formatado em Python (sem IA)."

        if usar_ia and GROQ_API_KEY:
            with st.spinner("Escolhendo emojis com Groq..."):
                try:
                    emojis_map, modelo_usado = escolher_emojis_groq(secoes, GROQ_API_KEY)
                    msg_status = f"Emojis escolhidos com Groq ({modelo_usado}) + montagem garantida em Python!"
                except Exception as e:
                    msg_status = f"Groq indisponível ({e}) — formatado automaticamente em Python (com bandeiras no Internacional)!"

        wpp, sub = montar_boletins(secoes, itens_contrapoder, emojis_map, num_edicao, mes_ano)
        st.session_state["resultado"] = (wpp, sub, msg_status)

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
