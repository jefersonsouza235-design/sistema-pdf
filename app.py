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


# =========================
# DADOS IBGE
# =========================
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
        )

        if resposta.ok:
            payload = resposta.json()
            projecao = payload.get("projecao")

            if projecao:
                try:
                    projecao_int = int(float(projecao))
                    dados["populacao_projetada"] = f"{projecao_int:,}".replace(",", ".")
                except:
                    dados["populacao_projetada"] = str(projecao)
    except:
        pass

    return dados


def buscar_manchetes():
    return []


# =========================
# PDF
# =========================
def gerar_pdf_bytes() -> bytes:
    dados_ibge = buscar_dados_ibge()

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Titulo", fontSize=18, spaceAfter=10))
    styles.add(ParagraphStyle(name="Texto", fontSize=10, spaceAfter=6))

    story = []

    story.append(Paragraph("RADAR TRABALHISTA", styles["Titulo"]))
    story.append(Paragraph("Relatório Executivo", styles["Texto"]))
    story.append(Paragraph(f"Atualizado em: {dados_ibge['atualizado_em']}", styles["Texto"]))

    story.append(Spacer(1, 10))

    story.append(Paragraph("Resumo Executivo", styles["Titulo"]))
    story.append(Paragraph(
        "O ambiente trabalhista brasileiro segue marcado por maior rastreabilidade regulatória, "
        "pressão por consistência documental e necessidade crescente de maturidade em gestão de pessoas.",
        styles["Texto"]
    ))

    story.append(Spacer(1, 10))

    story.append(Paragraph("Cenário Atual", styles["Titulo"]))
    story.append(Paragraph(dados_ibge["ocupados_brasil"], styles["Texto"]))

    story.append(Spacer(1, 10))

    story.append(Paragraph("Implicações para a Positivo Tecnologia", styles["Titulo"]))
    story.append(Paragraph(
        "- Maior necessidade de controle de afastamentos\n"
        "- Aumento da exigência regulatória\n"
        "- Pressão por eficiência operacional",
        styles["Texto"]
    ))

    story.append(Spacer(1, 10))

    story.append(Paragraph("Documento gerado automaticamente para apoio à análise executiva.", styles["Texto"]))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()


# =========================
# EMAIL
# =========================
def enviar_email(destino: str) -> None:
    email_user = os.environ.get("EMAIL_USER")
    email_password = os.environ.get("EMAIL_PASSWORD")

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


# =========================
# LOGIN MULTIPLO
# =========================
def validar_login(username: str, password: str) -> bool:
    usuarios = [
        (os.environ.get("APP_USER_1"), os.environ.get("APP_PASSWORD_1")),
        (os.environ.get("APP_USER_2"), os.environ.get("APP_PASSWORD_2")),
        (os.environ.get("APP_USER_3"), os.environ.get("APP_PASSWORD_3")),
    ]

    for user, senha in usuarios:
        if username == user and password == senha:
            return True

    return False


@app.route("/login", methods=["GET", "POST"])
def login():
    mensagem = ""

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

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


# =========================
# DASHBOARD
# =========================
@app.route("/", methods=["GET", "POST"])
def index():
    if not usuario_logado():
        return redirect(url_for("login"))

    mensagem = ""

    if request.method == "POST":
        emails = request.form.get("email")

        if emails:
            lista = [e.strip() for e in emails.split(",")]
            for email in lista:
                enviar_email(email)

            mensagem = "PDF enviado com sucesso!"

    return render_template(
        "index.html",
        mensagem=mensagem,
        usuario=session.get("usuario", "Usuário")
    )


if __name__ == "__main__":
    app.run()