from flask import Flask, render_template, url_for, request, redirect
import requests

app = Flask(__name__, static_url_path='/static')
app.secret_key = "a secret key"  # In production, use environment variable

API_KEY = "6b68366ccc3b47c77ceb9d3d0f2b3799"
API_URL = "https://wdapi2.com.br/consulta/{placa}/" + API_KEY

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/consultar', methods=['POST'])
def consultar():
    placa = request.form.get('placa', '').strip().upper()
    if not placa:
        return redirect('/')

    try:
        response = requests.get(API_URL.format(placa=placa))
        if response.status_code == 200:
            veiculo_data = response.json()
            return render_template('veiculo.html', veiculo=veiculo_data)
        else:
            # Em caso de erro, redireciona para a página inicial
            return redirect('/')
    except Exception as e:
        print(f"Erro ao consultar API: {e}")
        return redirect('/')

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)