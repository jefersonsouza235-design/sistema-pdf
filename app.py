from flask import Flask, render_template, request
import os
import smtplib
from io import BytesIO
from email.message import EmailMessage

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


def gerar_pdf_bytes() -> bytes:
    """
    Gera o PDF em memória, sem depender de wkhtmltopdf.
    Ideal para deploy no Render.
    """
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

    # Capa simples
    story.append(Paragraph("RELATÓRIO EXECUTIVO", styles["TitleExec"]))
    story.append(
        Paragraph(
            "Tendências da Legislação Trabalhista no Brasil",
            styles["HeadingExec"],
        )
    )
    story.append(
        Paragraph(
            "Análise estratégica aplicada à Positivo Tecnologia S.A.",
            styles["BodyExec"],
        )
    )
    story.append(Spacer(1, 16))

    story.append(Paragraph("Visão Geral", styles["HeadingExec"]))
    story.append(
        Paragraph(
            "O ambiente trabalhista brasileiro está passando por mudanças "
            "estruturais ligadas à digitalização, à ampliação da fiscalização "
            "e à maior pressão social por saúde mental, jornada sustentável e "
            "conformidade documental. Para uma organização como a Positivo "
            "Tecnologia, isso significa maior necessidade de governança, "
            "padronização de processos e capacidade de resposta rápida.",
            styles["BodyExec"],
        )
    )

    story.append(Paragraph("Principais Tendências e Impactos", styles["HeadingExec"]))

    blocos = [
        (
            "1. Digitalização e fiscalização via eSocial",
            "O eSocial consolidou mais de 15 obrigações trabalhistas, fiscais "
            "e previdenciárias, aumentando a capacidade de cruzamento de dados "
            "e detecção automática de inconsistências.",
            [
                "Maior risco de penalidades por erro operacional.",
                "Necessidade de integração entre RH, folha e controles internos.",
                "Redução da tolerância para inconsistências cadastrais e de eventos.",
            ],
            "Fonte específica: https://www.gov.br/esocial",
        ),
        (
            "2. Saúde mental e afastamentos",
            "O Brasil figura entre os países com maior prevalência de ansiedade, "
            "e o avanço dos afastamentos por transtornos mentais pressiona "
            "produtividade, absenteísmo e gestão das lideranças.",
            [
                "Maior custo indireto com afastamentos e substituições.",
                "Pressão sobre retenção e clima organizacional.",
                "Necessidade de programas preventivos e acompanhamento gerencial.",
            ],
            "Fontes específicas: https://www.who.int | https://www.gov.br/inss",
        ),
        (
            "3. Jornada e pressão por reorganização operacional",
            "As discussões sobre redução de jornada e revisão de escalas reforçam "
            "a necessidade de elevar produtividade por hora e rever alocação de mão de obra.",
            [
                "Possível aumento de custo operacional sem automação.",
                "Necessidade de redesenho de turnos e cobertura operacional.",
                "Maior importância de indicadores de produtividade e eficiência.",
            ],
            "Fonte específica: https://www.weforum.org/agenda/2023/10/four-day-workweek-results",
        ),
        (
            "4. Formalização, documentação e compliance",
            "Com mais trabalhadores ocupados e maior rastreabilidade estatal, "
            "o ambiente tende a exigir processos mais robustos e evidências formais.",
            [
                "Maior exposição a risco regulatório e trabalhista.",
                "Necessidade de processos auditáveis.",
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

    story.append(Paragraph("Aplicação na Positivo Tecnologia", styles["HeadingExec"]))
    story.append(
        Paragraph(
            "Para a Positivo Tecnologia, a necessidade mais concreta não é apenas "
            "‘acompanhar tendências’, mas estruturar resposta operacional. Em "
            "operações industriais, a prioridade tende a ser produtividade e "
            "automação para absorver pressões de jornada e custo. Em RH, a "
            "necessidade é fortalecer saúde mental, gestão de afastamentos, "
            "qualidade cadastral e governança. Em compliance e jurídico, a "
            "prioridade é rastreabilidade, documentação e prevenção de passivos.",
            styles["BodyExec"],
        )
    )

    story.append(Paragraph("Recomendações Executivas", styles["HeadingExec"]))
    story.append(
        ListFlowable(
            [
                ListItem(Paragraph("Mapear riscos trabalhistas por processo crítico.", styles["BodyExec"])),
                ListItem(Paragraph("Revisar integração entre folha, RH e controles de jornada.", styles["BodyExec"])),
                ListItem(Paragraph("Criar agenda formal de saúde mental e acompanhamento de afastamentos.", styles["BodyExec"])),
                ListItem(Paragraph("Priorizar automação e produtividade em áreas operacionais.", styles["BodyExec"])),
                ListItem(Paragraph("Usar indicadores mensais para jornada, absenteísmo, erros de folha e passivos.", styles["BodyExec"])),
            ],
            bulletType="bullet",
            leftIndent=14,
        )
    )

    story.append(Spacer(1, 12))
    story.append(
        Paragraph(
            "Relatório automatizado gerado pelo sistema interno.",
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
        raise RuntimeError(
            "Variáveis EMAIL_USER e EMAIL_PASSWORD não configuradas."
        )

    pdf_bytes = gerar_pdf_bytes()

    msg = EmailMessage()
    msg["Subject"] = "Relatório Executivo - Tendências Trabalhistas"
    msg["From"] = email_user
    msg["To"] = destino
    msg.set_content(
        "Segue em anexo o relatório executivo gerado automaticamente pelo sistema."
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


@app.route("/", methods=["GET", "POST"])
def index():
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