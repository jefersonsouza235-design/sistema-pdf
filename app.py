from flask import Flask, render_template, request
import smtplib
import pdfkit
from email.message import EmailMessage

app = Flask(__name__)

# 🔹 FUNÇÃO PARA GERAR PDF
def gerar_pdf():
    config = pdfkit.configuration(
        wkhtmltopdf=r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
    )

    html = render_template('relatorio.html')

    pdfkit.from_string(
        html,
        'pdf/tendencias.pdf',
        configuration=config
    )


# 🔹 FUNÇÃO PARA ENVIAR EMAIL
def enviar_email(destino):

    gerar_pdf()  # 👈 GERA O PDF ANTES DE ENVIAR

    email = EmailMessage()
    email['Subject'] = 'Relatório - Tendências Trabalhistas'
    email['From'] = 'jefersonsouza235@gmail.com'
    email['To'] = destino

    email.set_content('Segue o relatório executivo em anexo.')

    with open('pdf/tendencias.pdf', 'rb') as f:
        email.add_attachment(
            f.read(),
            maintype='application',
            subtype='pdf',
            filename='relatorio.pdf'
        )

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login('jefersonsouza235@gmail.com', 'vjjrplfpczcotkni')
        smtp.send_message(email)


# 🔹 ROTA PRINCIPAL
@app.route('/', methods=['GET', 'POST'])
def index():
    mensagem = ""

    if request.method == 'POST':
        emails = request.form['email']

        lista_emails = [e.strip() for e in emails.split(',')]

        for email in lista_emails:
            enviar_email(email)

        mensagem = "PDF enviado com sucesso para todos!"

    return render_template('index.html', mensagem=mensagem)


# 🔹 RODAR APP
app.run(debug=True, use_reloader=False)