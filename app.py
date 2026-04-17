from flask import Flask, render_template, request, redirect, url_for, session
import os
import smtplib
from io import BytesIO
from email.message import EmailMessage
from datetime import datetime, timezone

import requests
import feedparser

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    ListFlowable,
    ListItem,
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "troque-essa-chave-em-producao")


def usuario_logado() -> bool:
    return session.get("logado", False)


def buscar_dados_ibge():
    """
    Busca dados públicos e monta fallback executivo caso algo falhe.
    """
    dados = {
        "ocupados_brasil": "O Brasil segue com contingente superior a 100 milhões de pessoas ocupadas.",
        "fonte_ocupados": "IBGE",
        "atualizado_em": datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC"),
        "populacao_projetada": "Dado não carregado nesta execução.",
        "fonte_populacao": "IBGE - fallback do sistema",
        "mensagem_contexto": (
            "Os indicadores automáticos foram parcialmente atualizados. "
            "O sistema manteve texto executivo de segurança para preservar a leitura do relatório."
        ),
    }

    try:
        resposta = requests.get(
            "https://servicodados.ibge.gov.br/api/v1/projecoes/populacao",
            timeout=20,
            headers={"User-Agent": "RadarTrabalhista/1.0"},
        )

        if resposta.ok:
            payload = resposta.json()
            projecao = payload.get("projecao")

            if projecao:
                try:
                    projecao_int = int(float(projecao))
                    dados["populacao_projetada"] = f"{projecao_int:,}".replace(",", ".")
                except Exception:
                    dados["populacao_projetada"] = str(projecao)

                dados["fonte_populacao"] = "IBGE - API oficial"
                dados["mensagem_contexto"] = (
                    "Os indicadores automáticos foram atualizados com sucesso a partir de fonte pública oficial."
                )
            else:
                dados["populacao_projetada"] = (
                    "Projeção oficial indisponível no retorno da API nesta execução."
                )
                dados["fonte_populacao"] = "IBGE - resposta sem projeção"
        else:
            dados["populacao_projetada"] = (
                "Projeção oficial temporariamente indisponível; manter leitura com base no contexto regulatório atual."
            )
            dados["fonte_populacao"] = f"IBGE - API retornou status {resposta.status_code}"

    except Exception:
        dados["populacao_projetada"] = (
            "Projeção oficial temporariamente indisponível; sistema aplicou fallback executivo."
        )
        dados["fonte_populacao"] = "IBGE - indisponível nesta execução"

    return dados


def buscar_manchetes():
    """
    Busca manchetes a partir de feeds RSS/Atom configurados.
    """
    urls = os.environ.get("NEWS_FEED_URLS", "").strip()
    if not urls:
        return {
            "itens": [],
            "status": "nenhum_feed_configurado",
            "mensagem": (
                "Nenhum feed foi configurado no ambiente. "
                "Adicione NEWS_FEED_URLS para ativar leituras recentes automáticas."
            ),
        }

    resultados = []

    for url in [u.strip() for u in urls.split(",") if u.strip()]:
        try:
            feed = feedparser.parse(url)

            if getattr(feed, "bozo", False) and not getattr(feed, "entries", []):
                continue

            feed_titulo = getattr(feed.feed, "title", url)

            for entry in getattr(feed, "entries", [])[:3]:
                titulo = getattr(entry, "title", "Sem título")
                link = getattr(entry, "link", "")
                publicado = getattr(entry, "published", "")

                resultados.append({
                    "titulo": titulo,
                    "link": link,
                    "fonte": feed_titulo,
                    "publicado": publicado,
                })

        except Exception:
            continue

    if resultados:
        return {
            "itens": resultados[:6],
            "status": "ok",
            "mensagem": "Leituras recentes carregadas automaticamente a partir de feeds configurados.",
        }

    return {
        "itens": [],
        "status": "sem_resultado",
        "mensagem": (
            "Os feeds foram configurados, mas não retornaram itens válidos nesta execução. "
            "Revise as URLs cadastradas em NEWS_FEED_URLS."
        ),
    }


def gerar_pdf_bytes() -> bytes:
    dados_ibge = buscar_dados_ibge()
    noticias = buscar_manchetes()

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="TitleExec",
            parent=styles["Title"],
            fontSize=22,
            leading=26,
            textColor=colors.HexColor("#1A2A44"),
            spaceAfter=18,
        )
    )
    styles.add(
        ParagraphStyle(
            name="HeadingExec",
            parent=styles["Heading2"],
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#2E5AAC"),
            spaceBefore=10,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BodyExec",
            parent=styles["BodyText"],
            fontSize=10.5,
            leading=15,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SmallExec",
            parent=styles["BodyText"],
            fontSize=9,
            leading=12,
            textColor=colors.grey,
            spaceAfter=6,
        )
    )

    story = []

    story.append(Paragraph("RADAR TRABALHISTA", styles["TitleExec"]))
    story.append(Paragraph("Relatório Executivo Automatizado", styles["HeadingExec"]))
    story.append(
        Paragraph(
            "Atualizado automaticamente com dados públicos, parâmetros executivos e leituras recentes configuradas.",
            styles["BodyExec"],
        )
    )
    story.append(
        Paragraph(
            f"Atualizado em: {dados_ibge.get('atualizado_em', 'não informado')}",
            styles["SmallExec"],
        )
    )
    story.append(Spacer(1, 12))

    story.append(Paragraph("Resumo Executivo", styles["HeadingExec"]))
    story.append(
        Paragraph(
            "Este relatório combina automação, leitura executiva e dados públicos para apoiar decisões em RH, compliance e liderança operacional.",
            styles["BodyExec"],
        )
    )
    story.append(
        Paragraph(
            dados_ibge.get("mensagem_contexto", ""),
            styles["SmallExec"],
        )
    )

    story.append(Paragraph("Indicadores Atualizados", styles["HeadingExec"]))
    story.append(
        ListFlowable(
            [
                ListItem(Paragraph(
                    f"População projetada no Brasil: {dados_ibge.get('populacao_projetada', 'Não informado')}.",
                    styles["BodyExec"],
                )),
                ListItem(Paragraph(
                    f"Mercado de trabalho: {dados_ibge.get('ocupados_brasil', 'Não informado')}",
                    styles["BodyExec"],
                )),
            ],
            bulletType="bullet",
            leftIndent=14,
        )
    )
    story.append(
        Paragraph(
            f"Fontes dos indicadores: {dados_ibge.get('fonte_populacao', 'IBGE')} | {dados_ibge.get('fonte_ocupados', 'IBGE')}",
            styles["SmallExec"],
        )
    )

    story.append(Paragraph("Tendências e Impactos", styles["HeadingExec"]))

    blocos = [
        (
            "1. Digitalização e fiscalização via eSocial",
            "O aumento da digitalização pressiona consistência cadastral, integração entre sistemas e redução de erros operacionais.",
            [
                "Maior necessidade de governança documental.",
                "Redução da tolerância a falhas cadastrais e de eventos.",
                "Pressão por integração entre RH, folha e controles internos.",
            ],
            "Fonte específica: https://www.gov.br/esocial",
        ),
        (
            "2. Saúde mental e afastamentos",
            "A pressão sobre produtividade e clima organizacional reforça a necessidade de gestão preventiva e acompanhamento de afastamentos.",
            [
                "Maior custo indireto com ausências.",
                "Necessidade de gestão ativa de bem-estar.",
                "Pressão sobre retenção e liderança.",
            ],
            "Fontes específicas: https://www.who.int | https://www.gov.br/inss",
        ),
        (
            "3. Jornada e reorganização operacional",
            "Discussões sobre jornada fortalecem a agenda de produtividade por hora e automação.",
            [
                "Possível aumento de custo sem ganho de eficiência.",
                "Necessidade de redesenho operacional.",
                "Maior uso de indicadores de produtividade.",
            ],
            "Fonte específica: https://www.weforum.org/agenda/2023/10/four-day-workweek-results",
        ),
        (
            "4. Formalização e rastreabilidade",
            "O ambiente regulatório exige processos mais auditáveis e documentação mais robusta.",
            [
                "Maior exposição regulatória.",
                "Necessidade de processos padronizados.",
                "Fortalecimento de compliance e jurídico trabalhista.",
            ],
            "Fonte específica: https://www.ibge.gov.br/explica/desemprego.php",
        ),
    ]

    for titulo, texto, impactos, fonte in blocos:
        story.append(Paragraph(titulo, styles["BodyExec"]))
        story.append(Paragraph(texto, styles["BodyExec"]))
        story.append(
            ListFlowable(
                [ListItem(Paragraph(item, styles["BodyExec"])) for item in impactos],
                bulletType="bullet",
                leftIndent=14,
            )
        )
        story.append(Spacer(1, 6))
        story.append(Paragraph(fonte, styles["SmallExec"]))
        story.append(Spacer(1, 8))

    story.append(Paragraph("Leituras Recentes Configuradas", styles["HeadingExec"]))
    story.append(
        Paragraph(
            noticias.get("mensagem", ""),
            styles["SmallExec"],
        )
    )

    if noticias.get("itens"):
        lista_noticias = []
        for item in noticias["itens"]:
            texto = f"{item['titulo']} — {item['fonte']}"
            if item.get("publicado"):
                texto += f" — {item['publicado']}"
            if item.get("link"):
                texto += f" — {item['link']}"
            lista_noticias.append(ListItem(Paragraph(texto, styles["BodyExec"])))

        story.append(
            ListFlowable(
                lista_noticias,
                bulletType="bullet",
                leftIndent=14,
            )
        )
    else:
        story.append(
            Paragraph(
                "Sem itens recentes válidos para exibir nesta execução.",
                styles["BodyExec"],
            )
        )

    story.append(Paragraph("Aplicação na Positivo Tecnologia", styles["HeadingExec"]))
    story.append(
        Paragraph(
            "Para a Positivo Tecnologia, o ganho principal desta etapa é reduzir dependência de relatório totalmente fixo e incorporar sinais atualizados para apoiar decisões em RH, compliance, operações e gestão.",
            styles["BodyExec"],
        )
    )

    story.append(Paragraph("Recomendações Executivas", styles["HeadingExec"]))
    story.append(
        ListFlowable(
            [
                ListItem(Paragraph("Manter dados sensíveis em variáveis de ambiente.", styles["BodyExec"])),
                ListItem(Paragraph("Revisar periodicamente a qualidade dos feeds configurados.", styles["BodyExec"])),
                ListItem(Paragraph("Evoluir a integração com indicadores públicos mais específicos.", styles["BodyExec"])),
                ListItem(Paragraph("Criar versões do relatório por área: RH, compliance e operações.", styles["BodyExec"])),
            ],
            bulletType="bullet",
            leftIndent=14,
        )
    )

    story.append(Spacer(1, 12))
    story.append(
        Paragraph(
            "Relatório automatizado gerado pelo Radar Trabalhista.",
            styles["SmallExec"],
        )
    )

    doc.build(story)
    buffer.seek(0)
    return buffer.read()


def enviar_email(destino: str) -> None:
    email_user = os.environ.get("EMAIL_USER")
    email_password = os.environ.get("EMAIL_PASSWORD")

    if not email_user or not email_password:
        raise RuntimeError("Variáveis EMAIL_USER e EMAIL_PASSWORD não configuradas.")

    pdf_bytes = gerar_pdf_bytes()

    msg = EmailMessage()
    msg["Subject"] = "Relatório Executivo - Radar Trabalhista"
    msg["From"] = email_user
    msg["To"] = destino
    msg.set_content("Segue em anexo o relatório executivo gerado automaticamente pelo sistema.")

    msg.add_attachment(
        pdf_bytes,
        maintype="application",
        subtype="pdf",
        filename="relatorio_executivo.pdf",
    )

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(email_user, email_password)
        smtp.send_message(msg)


@app.route("/login", methods=["GET", "POST"])
def login():
    mensagem = ""

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        admin_user = os.environ.get("APP_USER", "admin")
        admin_pass = os.environ.get("APP_PASSWORD", "123456")

        if username == admin_user and password == admin_pass:
            session["logado"] = True
            return redirect(url_for("index"))

        mensagem = "Usuário ou senha inválidos."

    return render_template("login.html", mensagem=mensagem)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/", methods=["GET", "POST"])
def index():
    if not usuario_logado():
        return redirect(url_for("login"))

    mensagem = ""

    if request.method == "POST":
        emails = request.form.get("email", "").strip()

        if emails:
            lista_emails = [e.strip() for e in emails.split(",") if e.strip()]
            for email in lista_emails:
                enviar_email(email)
            mensagem = "PDF enviado com sucesso para todos!"
        else:
            mensagem = "Informe pelo menos um e-mail."

    return render_template("index.html", mensagem=mensagem)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))