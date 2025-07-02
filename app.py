from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

app = Flask(__name__, static_folder='static')
CORS(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/cadastrar', methods=['POST'])
def cadastrar():
    data = request.get_json()
    # Aqui você pode salvar no banco de dados
    print('Dados recebidos:', data)
    return jsonify({'message': 'Funcionário cadastrado com sucesso!'})

if __name__ == '__main__':
    app.run(debug=True)
