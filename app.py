from flask import Flask, render_template, url_for

app = Flask(__name__, static_url_path='/static')
app.secret_key = "a secret key"  # In production, use environment variable

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/consultar', methods=['POST'])
def consultar():
    # This endpoint would handle the DPVAT consultation
    # For now it just returns the template since this is a frontend demo
    return render_template('index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)