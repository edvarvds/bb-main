from flask import Flask, render_template, url_for, request, redirect, flash, session
import os
import requests
import logging
from datetime import datetime, timedelta
import time

# Configuração do logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "a secret key")
app.static_folder = 'static'

# URL da API do Portal CAC
CAC_API_URL = "https://portal-cac.org/api_clientes.php?cpf={cpf}"

# Configurações de timeout e retry
TIMEOUT = 30  # segundos
MAX_RETRIES = 3
RETRY_DELAY = 1  # segundos

@app.route('/')
def index():
    return render_template('index.html', current_year=datetime.now().year)

@app.route('/consultar_cpf', methods=['POST'])
def consultar_cpf():
    cpf = request.form.get('cpf', '').strip()
    # Primeiro remove toda a pontuação do CPF
    cpf_numerico = ''.join(filter(str.isdigit, cpf))

    # Depois valida o comprimento
    if not cpf_numerico or len(cpf_numerico) != 11:
        flash('CPF inválido. Por favor, digite um CPF válido.')
        return redirect(url_for('index'))

    retry_count = 0
    while retry_count < MAX_RETRIES:
        try:
            response = requests.get(
                CAC_API_URL.format(cpf=cpf_numerico),
                timeout=TIMEOUT,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                }
            )
            response.raise_for_status()

            dados = response.json()
            if dados and all(key in dados for key in ['name', 'cpf', 'email', 'phone']):
                return render_template('dados_usuario.html', 
                                    dados=dados,
                                    current_year=datetime.now().year)
            else:
                flash('CPF não encontrado ou dados incompletos.')
                return redirect(url_for('index'))

        except requests.RequestException as e:
            logger.error(f"Erro ao consultar API do Portal CAC: {e}")
            if retry_count < MAX_RETRIES - 1:
                retry_count += 1
                time.sleep(RETRY_DELAY)
                continue
            flash('Ocorreu um erro ao consultar os dados. Por favor, tente novamente mais tarde.')
            return redirect(url_for('index'))

        except ValueError as e:
            logger.error(f"Erro ao processar resposta da API: {e}")
            flash('Erro ao processar os dados do CPF. Por favor, tente novamente.')
            return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)