from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_cors import CORS
from werkzeug.utils import secure_filename # Embora secure_filename não seja usado diretamente, é bom ter se planeja usar no futuro para segurança
from PIL import Image
import os
import mimetypes
import uuid
import traceback # Para depuração, útil em desenvolvimento/deploy

# Inicialização da aplicação Flask
app = Flask(__name__)
CORS(app)  # Habilita CORS para todas as rotas

# Configurações das pastas
UPLOAD_FOLDER = 'uploads'
CONVERTED_FOLDER = 'converted'

# Criar pastas se não existirem
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CONVERTED_FOLDER, exist_ok=True)

# Expandindo as extensões permitidas para upload para incluir os novos formatos de documento
ALLOWED_EXTENSIONS = {
    'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'txt',
    'webp', 'bmp', 'tiff', 'ico', 'dcm', 'tga', 'psd', 'mpo', 'j2k', 'jpf', 'jpx', 'jp2', 'jpm', 'mj2', # Adicionei dcm e j2k,jpf,jpx,jp2,jpm,mj2 para completar
    'webp', 'bmp', 'tiff', 'ico', 'dds', 'tga', 'psp', 'blp', 'sgi', 'xbm', 'pcx', 'psd', 'mpo',
    # Novos formatos de documento adicionados aqui:
    'docm', 'dot', 'odt', 'xps', 'rtf', 'dotx', 'aw', 'djvu', 'sxw', 'dotm', 'abw', 'kwd', 'odt'
}

# Formatos suportados para imagem (mantidos como estavam, mas com alguns ajustes para Pillow)
# Chaves são os nomes que aparecerão na UI e valores são os formatos internos da PIL
FORMATS_IMG = {
    'JPG': 'JPEG',
    'JPEG': 'JPEG',
    'PNG': 'PNG',
    'WEBP': 'WEBP',
    'BMP': 'BMP',
    'TIFF': 'TIFF',
    'GIF': 'GIF',
    'ICO': 'ICO',      # Ícone
    'DDS': 'DDS',      # DirectDraw Surface
    'TGA': 'TGA',      # Truevision Targa
    'PSP': 'PSP',      # PaintShop Pro Image
    'BLP': 'BLP',      # Blizzard Texture Format (Pillow tem suporte limitado, pode requerer plugins)
    'SGI': 'SGI',      # Silicon Graphics Image
    'XBM': 'XBM',      # X BitMap
    'PCX': 'PCX',      # Paintbrush
    'PSD': 'PSD',      # Photoshop Document (Pillow pode ler, salvar pode ter limitações)
    'MPO': 'MPO',      # Multi Picture Object (geralmente usado para 3D)
    'J2K': 'JPEG2000', # JPEG 2000
    'JP2': 'JPEG2000', # JPEG 2000
    # DCM (DICOM) geralmente não é um formato de saída da Pillow, mas pode ser lido.
    # Se o objetivo é converter DCM, pode ser necessário um tratamento diferente.
}

# Formatos de documento (expandidos para incluir os novos)
DOC_FORMATS = [
    'PDF', 'TXT', 'DOCX',
    'DOCM', 'DOT', 'ODT', 'XPS', 'RTF', 'DOTX', 'AW', 'DJVU', 'SXW', 'DOTM', 'ABW', 'KWD'
]

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Rota para a página inicial (/)
@app.route('/')
def index():
    # Retorna o seu arquivo HTML principal
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'Nenhum arquivo enviado'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'Arquivo sem nome'}), 400

    if not allowed_file(file.filename):
        return jsonify({'success': False, 'error': 'Tipo de arquivo não permitido'}), 400

    # Gera nome único para o arquivo
    original_ext = file.filename.rsplit('.', 1)[1].lower()
    unique_filename = f"{uuid.uuid4().hex}.{original_ext}"
    original_path = os.path.join(UPLOAD_FOLDER, unique_filename)
    
    try:
        file.save(original_path)
    except Exception as e:
        return jsonify({'success': False, 'error': f'Erro ao salvar arquivo: {str(e)}'}), 500

    # Detecta tipo MIME e opções de conversão
    mime_type, _ = mimetypes.guess_type(original_path)
    opcoes = []
    categoria = "arquivo"

    # Determina a categoria e as opções de conversão com base no tipo MIME ou extensão
    if mime_type and mime_type.startswith('image/'):
        categoria = "imagem"
        opcoes = list(FORMATS_IMG.keys())
    # Se o arquivo é um dos novos formatos de documento ou outros tipos de texto/pdf
    elif mime_type in ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'] or \
         'text/' in mime_type or original_ext in [f.lower() for f in DOC_FORMATS]: # Verifica também pela extensão para robustez
        categoria = "documento"
        opcoes = DOC_FORMATS # Oferece todos os DOC_FORMATS como opções de conversão
    else:
        # Para outros tipos de arquivo não especificados
        categoria = "arquivo"
        opcoes = [] # Nenhuma opção de conversão por padrão para tipos desconhecidos

    return jsonify({
        'success': True,
        'filename': unique_filename,
        'originalName': file.filename,
        'tipo': mime_type,
        'categoria': categoria,
        'opcoes': opcoes,
        'message': 'Upload realizado com sucesso'
    })

@app.route('/convert', methods=['POST'])
def convert_file():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Dados inválidos'}), 400

    filename = data.get('filename')
    formato_destino = data.get('formato_destino')

    if not filename or not formato_destino:
        return jsonify({'success': False, 'error': 'Faltando parâmetros'}), 400

    original_path = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(original_path):
        return jsonify({'success': False, 'error': 'Arquivo não encontrado'}), 404

    try:
        # Converter imagem
        if formato_destino.upper() in FORMATS_IMG:
            with Image.open(original_path) as img:
                
                # --- Lógica de tratamento de modo de cor ---
                target_format_pillow = FORMATS_IMG[formato_destino.upper()]

                # Formatos que preferencialmente não devem ter canal alfa (transparência)
                # Adicionei 'WEBP' aqui, pois WebP pode ser salvo sem alfa.
                formats_no_alpha = ['JPEG', 'BMP', 'TIFF', 'ICO', 'PCX', 'SGI', 'XBM', 'MPO', 'DDS', 'WEBP'] 
                
                # Se o destino é um formato que não suporta RGBA ou é melhor em RGB,
                # e a imagem original é RGBA, converte para RGB (remove transparência).
                if img.mode == 'RGBA' and target_format_pillow in formats_no_alpha:
                    # Cria um novo fundo branco para a imagem RGBA
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[3]) # Usa o canal alfa como máscara
                    img = background
                # Para outros modos (L, P, etc.), converte para RGB para compatibilidade geral,
                # a menos que seja um formato que lide bem com esses modos específicos ou RGBA.
                elif img.mode not in ('RGB', 'RGBA'):
                    img = img.convert('RGB')
                # --- Fim da Lógica de tratamento de modo de cor ---
                
                ext = formato_destino.lower()
                # Ajustes de extensão para Pillow se necessário para o nome do arquivo final
                if ext == 'jpg':
                    ext = 'jpeg'
                elif ext == 'tiff':
                    ext = 'tif' # Extensão mais comum para TIFF em nomes de arquivo
                elif ext == 'j2k' or ext == 'jp2': # Adicionando extensões para JPEG2000
                    ext = 'jp2'

                converted_name = f"{uuid.uuid4().hex}.{ext}"
                converted_path = os.path.join(CONVERTED_FOLDER, converted_name)
                
                print(f"Salvando arquivo convertido em: {converted_path}")
                
                # Parâmetros adicionais para 'save()' da Pillow
                save_params = {}
                if formato_destino.upper() == 'ICO':
                    # Para ICO, é comum precisar especificar o tamanho ou usar resize
                    # Pillow pode gerar um ICO multi-tamanho. Aqui apenas o tamanho original.
                    save_params['sizes'] = [img.size]
                if formato_destino.upper() == 'JPEG':
                    save_params['quality'] = 90 # Qualidade padrão para JPEG
                    save_params['optimize'] = True # Otimiza o arquivo

                # Salva a imagem usando os parâmetros apropriados
                img.save(converted_path, FORMATS_IMG[formato_destino.upper()], **save_params)
                
                print("Arquivo convertido salvo com sucesso.")
                
                return jsonify({
                    'success': True,
                    'filename': converted_name,
                    'download_url': f'/download/{converted_name}'
                })

        # Converter documentos (simplificado - apenas copia)
        # Atenção: Esta lógica de "copiar" só funciona se o formato de destino for o mesmo do original,
        # ou se for uma conversão de TXT para TXT, etc. Para conversões complexas (ex: DOC para PDF),
        # você precisaria de uma biblioteca ou ferramenta externa aqui.
        elif formato_destino.upper() in DOC_FORMATS:
            original_ext = original_path.rsplit('.', 1)[1].upper()
            target_ext = formato_destino.upper()

            # Lógica para converter DOCX para PDF ou TXT (se usar uma lib como python-docx e pypdf)
            # ou apenas copiar o arquivo se for o mesmo formato.
            # Exemplo BÁSICO (APENAS COPIA SE FOR O MESMO FORMATO OU ENTRE TXT/DOCX SE TIVER LIBS ESPECÍFICAS)
            # Para conversão real entre formatos de documento, você precisaria de:
            # - Uma biblioteca como 'python-docx' para ler/escrever .docx
            # - Uma biblioteca como 'pypdf' para manipular PDFs
            # - Ou ferramentas externas como LibreOffice/Pandoc via subprocess.

            if original_ext == target_ext: # Se o formato de destino é o mesmo do original, apenas copia
                ext = formato_destino.lower()
                converted_name = f"{uuid.uuid4().hex}.{ext}"
                converted_path = os.path.join(CONVERTED_FOLDER, converted_name)
                
                with open(original_path, 'rb') as f_in, open(converted_path, 'wb') as f_out:
                    f_out.write(f_in.read())
                
                return jsonify({
                    'success': True,
                    'filename': converted_name,
                    'download_url': f'/download/{converted_name}'
                })
            else:
                # Aqui você precisaria implementar a lógica de conversão real entre formatos de documento.
                # Por exemplo:
                # if original_ext == 'DOCX' and target_ext == 'PDF':
                #    # Chamar a lógica de conversão DOCX para PDF (ex: usando um conversor externo)
                #    pass
                # elif original_ext == 'PDF' and target_ext == 'TXT':
                #    # Chamar a lógica de extração de texto de PDF
                #    pass
                # ... e assim por diante para cada par de conversão.
                
                # Por enquanto, se a conversão real não estiver implementada, ele retornará erro
                return jsonify({'success': False, 'error': f'Conversão de {original_ext} para {target_ext} não implementada no backend.'}), 400

        return jsonify({'success': False, 'error': 'Formato de destino não suportado'}), 400

    except Exception as e:
        # Imprime o erro no console do Flask para depuração
        print(f"Erro durante a conversão: {e}")
        traceback.print_exc() # Imprime o traceback completo aqui
        return jsonify({'success': False, 'error': f'Erro na conversão: {str(e)}'}), 500

@app.route('/download/<filename>')
def download_file(filename):
    try:
        # Serve arquivo da pasta 'converted'
        return send_from_directory(
            CONVERTED_FOLDER,
            filename,
            as_attachment=True,
            download_name=filename # Define o nome de download
        )
    except FileNotFoundError:
        return jsonify({'success': False, 'error': 'Arquivo não encontrado'}), 404

# A linha abaixo é APENAS para rodar localmente no seu computador.
# No Render, o Gunicorn é responsável por iniciar a aplicação.
# Se você tiver `debug=True` em produção, isso pode expor informações sensíveis.
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
