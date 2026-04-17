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
    Busca alguns dados públicos do IBGE.
    Se algo falhar, devolve fallback seguro.
    """
    dados = {
        "ocupados_brasil": "Mais de 100 milhões de pessoas ocupadas",
        "fonte_ocupados": "IBGE",
        "atualizado_em": datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC"),
    }

    try:
        # API oficial do IBGE
        # Mantemos a estrutura preparada para evoluir depois com tabelas SIDRA específicas.
        resposta = requests.get(
            "https://servicodados.ibge.gov.br/api/v1/projecoes/populacao",
            timeout=15,
        )
        if resposta.ok:
            payload = resposta.json()
            projecao = payload.get("projecao", "não informado")
            dados["populacao_projetada"] = f"{projecao:,}".replace(",", ".")
            dados["fonte_populacao"] = "IBGE - API oficial"
        else:
            dados["populacao_projetada"] = "Não disponível"
            dados["fonte_populacao"] = "IBGE - indisponível no momento"
    except Exception:
        dados["populacao_projetada"] = "Não disponível"
        dados["fonte_populacao"] = "IBGE - indisponível no momento"

    return dados


def buscar_manchetes():
    """
    Lê feeds RSS/Atom configurados por variável de ambiente.
    Exemplo:
    NEWS_FEED_URLS=https://site1/feed,https://site2/rss
    """
    urls = os.environ.get("NEWS_FEED_URLS", "").strip()
    if not urls:
        return []

    resultados = []
    for url in [u.strip() for u in urls.split(",") if u.strip()]:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:2]:
                resultados.append({
                    "titulo": getattr(entry, "title", "Sem título"),
                    "link": getattr(entry, "link", ""),
                    "fonte": getattr(feed.feed, "title", url),
                })
        except Exception:
            continue

    return resultados[:5]


def gerar_pdf_bytes() -> bytes:
    dados_ibge = buscar_dados_ibge()
    manchetes = buscar_manchetes()

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
            "Atualizado automaticamente com dados oficiais e parâmetros executivos.",
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
            "Este relatório combina parâmetros executivos fixos com dados atualizados "
            "automaticamente para apoiar decisões em RH, compliance e liderança operacional.",
            styles["BodyExec"],
        )
    )

    story.append(Paragraph("Indicadores Atualizados", styles["HeadingExec"]))
    story.append(
        ListFlowable(
            [
                ListItem(Paragraph(
                    f"População projetada no Brasil: {dados_ibge.get('populacao_projetada', 'Não disponível')}.",
                    styles["BodyExec"],
                )),
                ListItem(Paragraph(
                    f"Mercado de trabalho: {dados_ibge.get('ocupados_brasil', 'Não disponível')}.",
                    styles["BodyExec"],
                )),
            ],
            bulletType="bullet",
            leftIndent=14,
        )
    )
    story.append(
        Paragraph(
            f"Fonte dos indicadores: {dados_ibge.get('fonte_populacao', 'IBGE')} | {dados_ibge.get('fonte_ocupados', 'IBGE')}",
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
    if manchetes:
        story.append(
            ListFlowable(
                [
                    ListItem(
                        Paragraph(
                            f"{item['titulo']} — {item['fonte']} — {item['link']}",
                            styles["BodyExec"],
                        )
                    )
                    for item in manchetes
                ],
                bulletType="bullet",
                leftIndent=14,
            )
        )
    else:
        story.append(
            Paragraph(
                "Nenhum feed configurado no momento. Você pode adicionar URLs RSS/Atom na variável NEWS_FEED_URLS.",
                styles["BodyExec"],
            )
        )

    story.append(Paragraph("Aplicação na Positivo Tecnologia", styles["HeadingExec"]))
    story.append(
        Paragraph(
            "Para a Positivo Tecnologia, o ganho principal dessa etapa é deixar de depender "
            "de um relatório totalmente fixo. A partir daqui, o sistema passa a incorporar "
            "sinais atualizados para enriquecer decisões em RH, compliance, operações e gestão.",
            styles["BodyExec"],
        )
    )

    story.append(Paragraph("Recomendações Executivas", styles["HeadingExec"]))
    story.append(
        ListFlowable(
            [
                ListItem(Paragraph("Manter dados sensíveis em variáveis de ambiente.", styles["BodyExec"])),
                ListItem(Paragraph("Evoluir a integração com indicadores oficiais do IBGE.", styles["BodyExec"])),
                ListItem(Paragraph("Configurar feeds confiáveis para acompanhar mudanças regulatórias.", styles["BodyExec"])),
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