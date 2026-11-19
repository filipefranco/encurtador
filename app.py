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
                    return data["
