from flask import Flask, request, send_from_directory, jsonify
import os
from werkzeug.utils import secure_filename

app = Flask(__name__, static_folder='../frontend', static_url_path='')

# Diretórios de upload e conversão
UPLOAD_FOLDER = 'uploads'
CONVERTED_FOLDER = 'converted'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CONVERTED_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['CONVERTED_FOLDER'] = CONVERTED_FOLDER

# Servir a interface (index.html)
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory(app.static_folder, path)

# Upload de arquivos
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'Nenhum arquivo enviado.'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Nome de arquivo inválido.'}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    # Simulação de conversão (só copia)
    converted_path = os.path.join(app.config['CONVERTED_FOLDER'], filename)
    with open(filepath, 'rb') as f_in, open(converted_path, 'wb') as f_out:
        f_out.write(f_in.read())

    return jsonify({'message': 'Arquivo enviado e convertido com sucesso!', 'filename': filename})

# Download do arquivo convertido
@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['CONVERTED_FOLDER'], filename, as_attachment=True)

if __name__ == '__main__':
    # Host e porta compatíveis com Render.com
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
