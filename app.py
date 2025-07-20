from flask import Flask, request, send_file, after_this_request
from flask_cors import CORS
from fpdf import FPDF
from PIL import Image
from PyPDF2 import PdfMerger
import io
import os
import subprocess
import uuid

app = Flask(__name__)
CORS(app)  # Permitir CORS para que tu frontend JS pueda llamar

# 1. JPG/PNG a PDF
@app.route('/jpg_to_pdf', methods=['POST'])
def jpg_to_pdf():
    try:
        files = request.files.getlist('files')
        if not files:
            return "No se enviaron imágenes", 400
        # Solo procesa la primera imagen
        img = Image.open(files[0].stream).convert('RGB')
        width, height = img.size
        pdf = FPDF(unit='pt', format=[width, height])
        pdf.add_page()
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='JPEG')
        img_byte_arr.seek(0)
        pdf.image(img_byte_arr, 0, 0, width, height)
        output = io.BytesIO()
        pdf.output(output)
        output.seek(0)
        return send_file(output, download_name="imagen_a_pdf.pdf", as_attachment=True)
    except Exception as e:
        return f"Error al convertir JPG a PDF: {e}", 500

# 2. Unir PDFs
@app.route('/merge_pdf', methods=['POST'])
def merge_pdf():
    files = request.files.getlist('files')
    if not files:
        return "No se enviaron PDFs", 400
    merger = PdfMerger()
    for f in files:
        merger.append(f.stream)
    output = io.BytesIO()
    merger.write(output)
    merger.close()
    output.seek(0)
    return send_file(output, download_name="pdf_unido.pdf", as_attachment=True)

# 3. Comprimir PDF (usando Ghostscript, debe estar instalado en el servidor)
@app.route('/compress_pdf', methods=['POST'])
def compress_pdf():
    f = request.files.get('file')
    if not f:
        return "No se envió PDF", 400

    # Nombres únicos temporales
    input_name = f"input_{uuid.uuid4().hex}.pdf"
    output_name = f"output_{uuid.uuid4().hex}.pdf"
    f.save(input_name)
    # Comprimir con Ghostscript (puedes ajustar el nivel)
    try:
        subprocess.run([
            'gs', '-sDEVICE=pdfwrite', '-dCompatibilityLevel=1.4',
            '-dPDFSETTINGS=/ebook', '-dNOPAUSE', '-dQUIET', '-dBATCH',
            f'-sOutputFile={output_name}', input_name
        ], check=True)
        with open(output_name, 'rb') as pdf_file:
            pdf_data = pdf_file.read()
        @after_this_request
        def cleanup(response):
            try:
                os.remove(input_name)
                os.remove(output_name)
            except Exception:
                pass
            return response
        return send_file(
            io.BytesIO(pdf_data),
            download_name="pdf_comprimido.pdf",
            as_attachment=True
        )
    except Exception as e:
        # Limpia archivos si hubo error
        try:
            if os.path.exists(input_name):
                os.remove(input_name)
            if os.path.exists(output_name):
                os.remove(output_name)
        except Exception:
            pass
        return f"Error al comprimir PDF: {e}", 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
