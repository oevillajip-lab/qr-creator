import os, io, qrcode
from flask import Flask, request, send_file
from PIL import Image, ImageDraw, ImageOps, ImageFilter

app = Flask(__name__)

def generar_qr_v53_total(data_string, estilo, logo_bytes=None):
    qr_temp = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=40, border=0)
    qr_temp.add_data(data_string)
    qr_temp.make(fit=True)
    matrix = qr_temp.get_matrix()
    modules = len(matrix); size = modules * 40

    # Lógica de Logo y Aura (Tu código original)
    aura_pixels = None; logo_res = None
    if logo_bytes:
        logo_src = Image.open(io.BytesIO(logo_bytes)).convert("RGBA")
        logo_res = ImageOps.contain(logo_src, (int(size * 0.23), int(size * 0.23)))
        l_pos = ((size - logo_res.width) // 2, (size - logo_res.height) // 2)
        base_mask = Image.new("L", (size, size), 0)
        base_mask.paste(logo_res.split()[3], l_pos)
        ImageDraw.floodfill(base_mask, (0, 0), 128)
        aura_mask = base_mask.point(lambda p: 0 if p == 128 else 255).filter(ImageFilter.MaxFilter(81))
        aura_pixels = aura_mask.load()

    def get_m(r, c):
        if 0 <= r < modules and 0 <= c < modules:
            if aura_pixels and aura_pixels[c * 40 + 20, r * 40 + 20] > 20: return False
            return matrix[r][c]
        return False

    def es_ojo(r, c): return (r<7 and c<7) or (r<7 and c>=modules-7) or (r>=modules-7 and c<7)

    mask_body = Image.new("L", (size, size), 0); draw_b = ImageDraw.Draw(mask_body)
    RAD = 18; PAD = 2

    for r in range(modules):
        for c in range(modules):
            x, y = c * 40, r * 40
            if es_ojo(r, c):
                if matrix[r][c]: draw_b.rectangle([x, y, x+40, y+40], fill=255)
                continue
            
            if estilo == "Liquid Pro (Gusano)":
                if get_m(r, c):
                    draw_b.rounded_rectangle([x+PAD, y+PAD, x+40-PAD, y+40-PAD], radius=RAD, fill=255)
                    if get_m(r, c+1): draw_b.rounded_rectangle([x+PAD, y+PAD, x+80-PAD, y+40-PAD], radius=RAD, fill=255)
                    if get_m(r+1, c): draw_b.rounded_rectangle([x+PAD, y+PAD, x+40-PAD, y+80-PAD], radius=RAD, fill=255)
            elif estilo == "Circular (Puntos)":
                if get_m(r, c): draw_b.ellipse([x+4, y+4, x+36, y+36], fill=255)
            else: # Normal
                if get_m(r, c): draw_b.rectangle([x, y, x+40, y+40], fill=255)

    canvas = Image.new("RGBA", (size + 80, size + 80), (255,255,255,255))
    qr_layer = Image.new("RGBA", (size, size), (0,0,0,0))
    qr_layer.paste((0,0,0,255), (0,0), mask=mask_body)
    if logo_res: qr_layer.paste(logo_res, l_pos, logo_res)
    canvas.paste(qr_layer, (40, 40), mask=qr_layer)

    out = io.BytesIO(); canvas.save(out, format="PNG"); out.seek(0)
    return out

@app.route('/generate', methods=['POST'])
def generate():
    texto = request.form.get('texto', ''); estilo = request.form.get('estilo', 'Normal (Cuadrado)')
    logo_file = request.files.get('logo'); logo_bytes = logo_file.read() if logo_file else None
    try:
        return send_file(generar_qr_v53_total(texto, estilo, logo_bytes), mimetype='image/png')
    except Exception as e: return str(e), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
