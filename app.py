from flask import Flask, render_template

app = Flask(__name__)
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
