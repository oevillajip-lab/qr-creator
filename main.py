import os, io, base64, qrcode
from flask import Flask, request, send_file, jsonify
from PIL import Image, ImageDraw, ImageOps, ImageFilter

app = Flask(__name__)

def crear_fondo(w, h, mode, c1, c2):
    if mode == "Transparente": return Image.new("RGBA", (w, h), (0, 0, 0, 0))
    if mode == "Blanco (Default)": return Image.new("RGBA", (w, h), (255, 255, 255, 255))
    return Image.new("RGBA", (w, h), (255, 255, 255, 255)) # Por defecto blanco

def generar_qr_v53_core(data_string, estilo, logo_bytes=None):
    qr_temp = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=40, border=0)
    qr_temp.add_data(data_string)
    qr_temp.make(fit=True)
    matrix = qr_temp.get_matrix()
    modules = len(matrix)
    size = modules * 40

    # Lógica de Logo (si existe)
    if logo_bytes:
        logo_src = Image.open(io.BytesIO(logo_bytes)).convert("RGBA")
        logo_res = ImageOps.contain(logo_src, (int(size * 0.23), int(size * 0.23)))
        l_pos = ((size - logo_res.width) // 2, (size - logo_res.height) // 2)
        # Crear Aura para que el QR no toque el logo (Tu lógica original)
        base_mask = Image.new("L", (size, size), 0)
        base_mask.paste(logo_res.split()[3], l_pos)
        ImageDraw.floodfill(base_mask, (0, 0), 128)
        solid_mask = base_mask.point(lambda p: 0 if p == 128 else 255)
        aura_mask = solid_mask.filter(ImageFilter.MaxFilter((40 * 2) + 1))
        aura_pixels = aura_mask.load()
    else:
        logo_res = None
        aura_pixels = None

    def get_m(r, c):
        if 0 <= r < modules and 0 <= c < modules:
            if aura_pixels and aura_pixels[c * 40 + 20, r * 40 + 20] > 20: return False
            return matrix[r][c]
        return False

    def es_ojo_general(r, c): return (r<7 and c<7) or (r<7 and c>=modules-7) or (r>=modules-7 and c<7)

    mask_body = Image.new("L", (size, size), 0)
    draw_b = ImageDraw.Draw(mask_body)
    RAD = 18; PAD = 2

    for r in range(modules):
        for c in range(modules):
            x, y = c * 40, r * 40
            if es_ojo_general(r, c):
                if matrix[r][c]: draw_b.rectangle([x, y, x+40, y+40], fill=255)
                continue
            
            if estilo == "Liquid Pro (Gusano)":
                if get_m(r, c):
                    draw_b.rounded_rectangle([x+PAD, y+PAD, x+40-PAD, y+40-PAD], radius=RAD, fill=255)
                    if get_m(r, c+1): draw_b.rounded_rectangle([x+PAD, y+PAD, x+80-PAD, y+40-PAD], radius=RAD, fill=255)
                    if get_m(r+1, c): draw_b.rounded_rectangle([x+PAD, y+PAD, x+40-PAD, y+80-PAD], radius=RAD, fill=255)
                    if get_m(r, c+1) and get_m(r+1, c) and get_m(r+1, c+1): draw_b.rectangle([x+20, y+20, x+60, y+60], fill=255)
            elif estilo == "Circular (Puntos)":
                if get_m(r, c): draw_b.ellipse([x+1, y+1, x+39, y+39], fill=255)
            else: # Normal
                if get_m(r, c): draw_b.rectangle([x, y, x+40, y+40], fill=255)

    canvas = Image.new("RGBA", (size + 80, size + 80), (255,255,255,255))
    qr_layer = Image.new("RGBA", (size, size), (0,0,0,0))
    qr_layer.paste((0,0,0,255), (0,0), mask=mask_body)
    if logo_res: qr_layer.paste(logo_res, l_pos, logo_res)
    canvas.paste(qr_layer, (40, 40), mask=qr_layer)

    out = io.BytesIO()
    canvas.save(out, format="PNG")
    out.seek(0)
    return out

@app.route('/generate', methods=['POST'])
def generate():
    # Usamos multipart/form-data para poder recibir el logo
    texto = request.form.get('texto', '')
    estilo = request.form.get('estilo', 'Normal (Cuadrado)')
    logo_file = request.files.get('logo')
    logo_bytes = logo_file.read() if logo_file else None
    
    try:
        img_buffer = generar_qr_v53_core(texto, estilo, logo_bytes)
        return send_file(img_buffer, mimetype='image/png')
    except Exception as e:
        return str(e), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
