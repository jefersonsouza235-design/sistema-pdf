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
    dados = {
        "ocupados_brasil": "O Brasil segue com contingente superior a 100 milhões de pessoas ocupadas.",
        "fonte_ocupados": "IBGE",
        "atualizado_em": datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC"),
        "populacao_projetada": None,
        "fonte_populacao": "IBGE - API oficial",
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
    except Exception:
        pass

    return dados


def buscar_manchetes():
    urls = os.environ.get("NEWS_FEED_URLS", "").strip()
    if not urls:
        return []

    resultados = []

    for url in [u.strip() for u in urls.split(",") if u.strip()]:
        try:
            feed = feedparser.parse(url)

            if getattr(feed, "bozo", False) and not getattr(feed, "entries", []):
                continue

            feed_titulo = getattr(feed.feed, "title", url)

            for entry in getattr(feed, "entries", [])[:3]:
                resultados.append({
                    "titulo": getattr(entry, "title", "Sem título"),
                    "link": getattr(entry, "link", ""),
                    "fonte": feed_titulo,
                    "publicado": getattr(entry, "published", ""),
                })

        except Exception:
            continue

    return resultados[:6]


def gerar_pdf_bytes() -> bytes:
    dados_ibge = buscar_dados_ibge()
    _noticias = buscar_manchetes()  # reservado para evolução futura

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
            spaceBefore=12,
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
    story.append(Paragraph("Relatório Executivo", styles["HeadingExec"]))
    story.append(
        Paragraph(
            "Atualizado automaticamente com dados públicos e parâmetros executivos para apoio à tomada de decisão.",
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
            "O ambiente trabalhista brasileiro segue marcado por maior rastreabilidade regulatória, "
            "pressão por consistência documental e necessidade crescente de maturidade em gestão de pessoas. "
            "Para organizações com operações e estruturas corporativas mais complexas, os efeitos tendem a se distribuir "
            "entre RH, compliance, jurídico e operação.",
            styles["BodyExec"],
        )
    )

    story.append(Paragraph("Cenário Atual", styles["HeadingExec"]))
    story.append(
        Paragraph(
            "Os dados públicos disponíveis nesta execução reforçam um ambiente de maior controle institucional, "
            "exigência de integração entre sistemas e necessidade de respostas mais rápidas a inconsistências "
            "trabalhistas e operacionais.",
            styles["BodyExec"],
        )
    )

    itens_cenario = []

    if dados_ibge.get("populacao_projetada"):
        itens_cenario.append(
            ListItem(
                Paragraph(
                    f"População projetada no Brasil: {dados_ibge['populacao_projetada']}.",
                    styles["BodyExec"],
                )
            )
        )

    itens_cenario.append(
        ListItem(
            Paragraph(
                f"Mercado de trabalho: {dados_ibge.get('ocupados_brasil', 'Não informado')}",
                styles["BodyExec"],
            )
        )
    )

    story.append(
        ListFlowable(
            itens_cenario,
            bulletType="bullet",
            leftIndent=14,
        )
    )

    fontes_cenario = [dados_ibge.get("fonte_ocupados", "IBGE")]
    if dados_ibge.get("populacao_projetada"):
        fontes_cenario.insert(0, dados_ibge.get("fonte_populacao", "IBGE"))

    story.append(
        Paragraph(
            f"Fontes dos indicadores: {' | '.join(fontes_cenario)}",
            styles["SmallExec"],
        )
    )

    story.append(Paragraph("Tendências e Impactos", styles["HeadingExec"]))

    blocos = [
        (
            "1. Digitalização e fiscalização via eSocial",
            "O avanço da digitalização amplia a capacidade de fiscalização e reduz a tolerância a falhas cadastrais, "
            "inconsistências de eventos e desconexões entre sistemas internos.",
            [
                "Maior necessidade de governança documental.",
                "Redução da tolerância a falhas cadastrais e operacionais.",
                "Pressão por integração entre RH, folha e controles internos.",
            ],
            "Fonte específica: https://www.gov.br/esocial",
        ),
        (
            "2. Saúde mental e afastamentos",
            "O aumento da atenção institucional sobre saúde mental e o crescimento de afastamentos reforçam "
            "a necessidade de prevenção, acompanhamento e resposta gerencial mais estruturada.",
            [
                "Maior custo indireto com ausências e substituições.",
                "Pressão sobre retenção, clima e continuidade operacional.",
                "Necessidade de gestão preventiva e acompanhamento mais próximo.",
            ],
            "Fontes específicas: https://www.who.int | https://www.gov.br/inss",
        ),
        (
            "3. Jornada e reorganização operacional",
            "As discussões sobre jornada e escala reforçam a necessidade de elevar produtividade por hora, "
            "rever alocação de mão de obra e ampliar eficiência operacional.",
            [
                "Possível aumento de custo sem ganho correspondente de eficiência.",
                "Necessidade de redesenho operacional e revisão de turnos.",
                "Maior uso de indicadores de produtividade e cobertura.",
            ],
            "Fonte específica: https://www.weforum.org/agenda/2023/10/four-day-workweek-results",
        ),
        (
            "4. Formalização e rastreabilidade",
            "O ambiente regulatório exige processos mais auditáveis, documentação mais robusta e padronização "
            "mais consistente das rotinas trabalhistas.",
            [
                "Maior exposição regulatória e trabalhista.",
                "Necessidade de processos padronizados e auditáveis.",
                "Fortalecimento do papel de compliance e jurídico trabalhista.",
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

    story.append(Paragraph("Implicações para a Positivo Tecnologia", styles["HeadingExec"]))
    story.append(
        ListFlowable(
            [
                ListItem(Paragraph(
                    "Em operações industriais, o principal risco está no aumento de custo e na necessidade de ganho de produtividade para absorver possíveis pressões sobre jornada e escala.",
                    styles["BodyExec"]
                )),
                ListItem(Paragraph(
                    "Em Recursos Humanos, cresce a necessidade de controle mais rigoroso de afastamentos, qualidade cadastral e acompanhamento preventivo de saúde mental.",
                    styles["BodyExec"]
                )),
                ListItem(Paragraph(
                    "Em compliance e jurídico, o ambiente exige maior rastreabilidade documental, integração entre sistemas e resposta mais rápida a inconsistências trabalhistas.",
                    styles["BodyExec"]
                )),
                ListItem(Paragraph(
                    "Na gestão executiva, a principal demanda passa a ser transformar exigências regulatórias em prioridade operacional, evitando que o tema fique restrito a uma única área.",
                    styles["BodyExec"]
                )),
            ],
            bulletType="bullet",
            leftIndent=14,
        )
    )

    story.append(Paragraph("Prioridades de Atenção", styles["HeadingExec"]))
    story.append(
        ListFlowable(
            [
                ListItem(Paragraph(
                    "Revisar a robustez dos processos ligados a folha, jornada, eventos trabalhistas e consistência de cadastro.",
                    styles["BodyExec"]
                )),
                ListItem(Paragraph(
                    "Fortalecer mecanismos de prevenção de afastamentos e acompanhamento de fatores psicossociais.",
                    styles["BodyExec"]
                )),
                ListItem(Paragraph(
                    "Aumentar a integração entre RH, operação e compliance para reduzir exposição a passivos e retrabalho.",
                    styles["BodyExec"]
                )),
                ListItem(Paragraph(
                    "Avaliar oportunidades de automação e revisão de processos em áreas mais sensíveis a custo de mão de obra.",
                    styles["BodyExec"]
                )),
            ],
            bulletType="bullet",
            leftIndent=14,
        )
    )

    story.append(Paragraph("Fontes", styles["HeadingExec"]))
    story.append(
        ListFlowable(
            [
                ListItem(Paragraph("eSocial — https://www.gov.br/esocial", styles["BodyExec"])),
                ListItem(Paragraph("OMS — https://www.who.int", styles["BodyExec"])),
                ListItem(Paragraph("INSS — https://www.gov.br/inss", styles["BodyExec"])),
                ListItem(Paragraph("World Economic Forum — https://www.weforum.org/agenda/2023/10/four-day-workweek-results", styles["BodyExec"])),
                ListItem(Paragraph("IBGE — https://www.ibge.gov.br/explica/desemprego.php", styles["BodyExec"])),
            ],
            bulletType="bullet",
            leftIndent=14,
        )
    )

    story.append(Spacer(1, 12))
    story.append(
        Paragraph(
            "Documento gerado automaticamente para apoio à análise executiva.",
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
    msg["Subject"] = "Radar Trabalhista - Relatório Executivo"
    msg["From"] = email_user
    msg["To"] = destino
    msg.set_content(
        """Pessoal,

Estruturei um material com leitura executiva sobre tendências trabalhistas e possíveis impactos operacionais, com foco em apoio à tomada de decisão.

A ideia é consolidar de forma objetiva alguns pontos que vêm ganhando relevância e que podem demandar atenção das áreas.

Fico à disposição para aprofundar qualquer tema ou discutir possíveis aplicações dentro da nossa realidade.

Abs,
Jeferson"""
    )

    msg.add_attachment(
        pdf_bytes,
        maintype="application",
        subtype="pdf",
        filename="relatorio_executivo.pdf",
    )

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(email_user, email_password)
        smtp.send_message(msg)


def validar_login(username: str, password: str) -> bool:
    usuarios = [
        (os.environ.get("APP_USER_1", ""), os.environ.get("APP_PASSWORD_1", "")),
        (os.environ.get("APP_USER_2", ""), os.environ.get("APP_PASSWORD_2", "")),
        (os.environ.get("APP_USER_3", ""), os.environ.get("APP_PASSWORD_3", "")),
    ]

    for user, senha in usuarios:
        if user and senha and username == user and password == senha:
            return True

    return False


@app.route("/login", methods=["GET", "POST"])
def login():
    mensagem = ""

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if validar_login(username, password):
            session["logado"] = True
            session["usuario"] = username
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
            mensagem = "PDF enviado com sucesso!"
        else:
            mensagem = "Informe pelo menos um e-mail."

    return render_template(
        "index.html",
        mensagem=mensagem,
        usuario=session.get("usuario", "Usuário")
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))