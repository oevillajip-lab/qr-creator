import os
import io
import base64
from flask import Flask, request, jsonify, send_file
import qrcode
from PIL import Image, ImageDraw, ImageOps, ImageFilter

app = Flask(__name__)

def generar_qr_motor(texto, estilo, qr_color="#000000", bg_color="#FFFFFF"):
    # Configuración básica del QR
    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=40, border=0)
    qr.add_data(texto)
    qr.make(fit=True)
    matrix = qr.get_matrix()
    modules = len(matrix)
    size = modules * 40
    
    # Creamos la máscara del cuerpo según el estilo
    mask_body = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask_body)
    
    for r in range(modules):
        for c in range(modules):
            if matrix[r][c]:
                x, y = c * 40, r * 40
                if estilo == "Liquid Pro (Gusano)":
                    draw.rounded_rectangle([x+2, y+2, x+38, y+38], radius=18, fill=255)
                elif estilo == "Circular (Puntos)":
                    draw.ellipse([x+2, y+2, x+38, y+38], fill=255)
                else: # Normal
                    draw.rectangle([x, y, x+40, y+40], fill=255)

    # Coloreado
    img_final = Image.new("RGBA", (size, size), bg_color)
    qr_color_layer = Image.new("RGBA", (size, size), qr_color)
    img_final.paste(qr_color_layer, (0,0), mask=mask_body)
    
    # Guardar en memoria para enviar a la App
    img_io = io.BytesIO()
    img_final.save(img_io, 'PNG')
    img_io.seek(0)
    return img_io

@app.route('/generate', methods=['POST'])
def generate():
    data = request.json
    texto = data.get('texto', 'Comagro QR')
    estilo = data.get('estilo', 'Normal (Cuadrado)')
    qr_color = data.get('color', '#000000')
    
    try:
        buffer = generar_qr_motor(texto, estilo, qr_color)
        return send_file(buffer, mimetype='image/png')
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)