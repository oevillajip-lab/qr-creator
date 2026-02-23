import os
import io
import qrcode
from PIL import Image, ImageDraw, ImageOps, ImageFilter
from flask import Flask, request, send_file
import tempfile

app = Flask(__name__)

# ============================================================================
# VARIABLES GLOBALES DEL CÓDIGO PADRE (INTACTAS)
# ============================================================================
qr_body_c1 = (0, 0, 0)
qr_body_c2 = (33, 150, 243)
eye_ext_color = (0, 0, 0)
eye_int_color = (0, 0, 0)
bg_c1 = (255, 255, 255) 
bg_c2 = (240, 240, 240)

# ============================================================================
# FUNCIONES SAGRADAS DEL CÓDIGO PADRE (SIN MODIFICAR NI UNA LETRA)
# ============================================================================
def crear_fondo(w, h, mode, c1, c2, direction):
    if mode == "Transparente":
        return Image.new("RGBA", (w, h), (0, 0, 0, 0))
    elif mode == "Blanco (Default)":
        return Image.new("RGBA", (w, h), (255, 255, 255, 255))
    elif mode == "Sólido (Color)":
        return Image.new("RGBA", (w, h), c1 + (255,)) 
    elif mode == "Degradado":
        base = Image.new("RGB", (w, h), c1)
        draw = ImageDraw.Draw(base)
        if direction == "Vertical":
            for y in range(h):
                r = y / h
                col = tuple(int(c1[j] * (1 - r) + c2[j] * r) for j in range(3))
                draw.line([(0, y), (w, y)], fill=col)
        elif direction == "Horizontal":
            for x in range(w):
                r = x / w
                col = tuple(int(c1[j] * (1 - r) + c2[j] * r) for j in range(3))
                draw.line([(x, 0), (x, h)], fill=col)
        elif direction == "Diagonal":
            steps = w + h
            for i in range(steps):
                r = i / steps
                col = tuple(int(c1[j] * (1 - r) + c2[j] * r) for j in range(3))
                x0, y0 = 0, i; x1, y1 = i, 0
                if y0 > h: x0 = y0 - h; y0 = h
                if x1 > w: y1 = x1 - w; x1 = w
                draw.line([(x0, y0), (x1, y1)], fill=col, width=2)
        return base.convert("RGBA")
    return Image.new("RGBA", (w, h), (255, 255, 255, 255))

def generar_qr_clasico_engine(params, data_string):
    logo_path = params['logo_path']; estilo = params['estilo']
    modo_color_qr = params['modo_color_qr']; grad_dir_qr = params['grad_dir_qr']
    usar_ojos_custom = params['usar_ojos_custom']; modo_fondo = params['modo_fondo']
    grad_dir_bg = params['grad_dir_bg']
    
    is_intelligent_jpg = False
    if logo_path and logo_path.lower().endswith(('.jpg', '.jpeg', '.bmp')):
        is_intelligent_jpg = True

    usar_logo = True
    if not logo_path or not os.path.exists(logo_path): usar_logo = False

    try:
        OUTPUT_DIR = "output_qr"
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        qr_temp = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=40, border=0)
        qr_temp.add_data(data_string); qr_temp.make(fit=True)
        matrix = qr_temp.get_matrix(); modules = len(matrix); size = modules * 40
        
        if usar_logo:
            logo_src = Image.open(logo_path).convert("RGBA")
            if is_intelligent_jpg:
                gray = logo_src.convert("L"); inverted = ImageOps.invert(gray); bbox = inverted.getbbox()
                if bbox:
                    pad = 10; l, u, r, d = bbox; w_i, h_i = logo_src.size
                    logo_src = logo_src.crop((max(0, l-pad), max(0, u-pad), min(w_i, r+pad), min(h_i, d+pad)))
                datas = logo_src.getdata(); new_data = []
                for item in datas:
                    if item[0]>240 and item[1]>240 and item[2]>240: new_data.append((255, 255, 255, 0))
                    else: new_data.append(item)
                logo_src.putdata(new_data)

            w_orig, h_orig = logo_src.size
            es_rectangular = w_orig > (h_orig * 1.4)
            if es_rectangular: logo_res = ImageOps.contain(logo_src, (int(size * 0.45), int(size * 0.20)))
            else: logo_res = ImageOps.contain(logo_src, (int(size * 0.23), int(size * 0.23)))
            l_pos = ((size - logo_res.width) // 2, (size - logo_res.height) // 2)
        else:
            logo_res = Image.new("RGBA", (1,1), (0,0,0,0)); l_pos = (0,0)

        base_mask = Image.new("L", (size, size), 0)
        if usar_logo:
            base_mask.paste(logo_res.split()[3], l_pos); ImageDraw.floodfill(base_mask, (0, 0), 128)
            solid_mask = base_mask.point(lambda p: 0 if p == 128 else 255)
            aura_mask = solid_mask.filter(ImageFilter.MaxFilter((40 * 2) + 1)); aura_pixels = aura_mask.load()
        else: aura_pixels = base_mask.load()

        def get_m(r, c):
            if 0 <= r < modules and 0 <= c < modules:
                if usar_logo and aura_pixels[c * 40 + 20, r * 40 + 20] > 20: return False
                return matrix[r][c]
            return False

        def es_ojo_general(r, c): return (r<7 and c<7) or (r<7 and c>=modules-7) or (r>=modules-7 and c<7)
        def es_ojo_externo(r, c):
            if not es_ojo_general(r, c): return False
            if r<7 and c<7: lr,lc=r,c
            elif r<7 and c>=modules-7: lr,lc=r,c-(modules-7)
            else: lr,lc=r-(modules-7),c
            if 2<=lr<=4 and 2<=lc<=4: return False 
            return True 
        def es_ojo_interno(r, c):
            if not es_ojo_general(r, c): return False
            if r<7 and c<7: lr,lc=r,c
            elif r<7 and c>=modules-7: lr,lc=r,c-(modules-7)
            else: lr,lc=r-(modules-7),c
            if 2<=lr<=4 and 2<=lc<=4: return True
            return False

        mask_body = Image.new("L", (size, size), 0); mask_eye_ext = Image.new("L", (size, size), 0); mask_eye_int = Image.new("L", (size, size), 0)
        draw_b = ImageDraw.Draw(mask_body); draw_ext = ImageDraw.Draw(mask_eye_ext); draw_int = ImageDraw.Draw(mask_eye_int)
        RAD_LIQUID = 18; PAD = 2

        # --- BUCLE DE DIBUJO ---
        for r in range(modules):
            for c in range(modules):
                x, y = c * 40, r * 40
                
                # SELECCIÓN DE DRAW Y LÓGICA DE SALTO PARA OJOS CIRCULARES
                if es_ojo_interno(r, c): draw = draw_int
                elif es_ojo_externo(r, c): draw = draw_ext
                elif es_ojo_general(r, c): continue # Espacio vacio del ojo
                else: draw = draw_b
                
                if estilo == "Liquid Pro (Gusano)":
                    if get_m(r, c):
                        draw.rounded_rectangle([x+PAD, y+PAD, x+40-PAD, y+40-PAD], radius=RAD_LIQUID, fill=255)
                        if get_m(r, c+1): draw.rounded_rectangle([x+PAD, y+PAD, x+80-PAD, y+40-PAD], radius=RAD_LIQUID, fill=255)
                        if get_m(r+1, c): draw.rounded_rectangle([x+PAD, y+PAD, x+40-PAD, y+80-PAD], radius=RAD_LIQUID, fill=255)
                        if get_m(r, c+1) and get_m(r+1, c) and get_m(r+1, c+1): draw.rectangle([x+20, y+20, x+60, y+60], fill=255)
                
                elif estilo == "Normal (Cuadrado)":
                    if get_m(r, c): draw.rectangle([x, y, x+40, y+40], fill=255)
                
                elif estilo == "Barras (Vertical)":
                    if get_m(r, c):
                        if es_ojo_general(r,c): draw.rectangle([x, y, x+40, y+40], fill=255)
                        else:
                            draw.rounded_rectangle([x+4, y, x+36, y+40], radius=10, fill=255)
                            if get_m(r+1, c) and not es_ojo_general(r+1, c): draw.rectangle([x+4, y+20, x+36, y+60], fill=255)
                
                # --- CORRECCIÓN AQUÍ PARA CIRCULAR ---
                elif estilo == "Circular (Puntos)":
                    # Si es ojo, NO DIBUJAMOS PUNTOS AQUÍ (Lo hacemos geometrico despues)
                    if es_ojo_general(r, c):
                        continue
                    
                    # Si es cuerpo, dibujamos el punto normal
                    if get_m(r, c): 
                        draw_b.ellipse([x+1, y+1, x+39, y+39], fill=255)

        # --- DIBUJO GEOMÉTRICO DE OJOS (SOLO PARA ESTILO CIRCULAR) ---
        if estilo == "Circular (Puntos)":
            def draw_geo_eye(r_start, c_start):
                x = c_start * 40
                y = r_start * 40
                eye_size = 7 * 40
                
                # 1. Anillo Externo (En mascara Externa)
                draw_ext.ellipse([x, y, x + eye_size, y + eye_size], fill=255)
                draw_ext.ellipse([x + 40, y + 40, x + eye_size - 40, y + eye_size - 40], fill=0)
                
                # 2. Punto Interno (En mascara Interna)
                draw_int.ellipse([x + 80, y + 80, x + eye_size - 80, y + eye_size - 80], fill=255)

            # Dibujar los 3 ojos
            draw_geo_eye(0, 0)              # Arriba Izquierda
            draw_geo_eye(0, modules-7)      # Arriba Derecha
            draw_geo_eye(modules-7, 0)      # Abajo Izquierda

        # --- COLOREADO FINAL ---
        img_body_color = Image.new("RGBA", (size, size), (0,0,0,0)); draw_grad = ImageDraw.Draw(img_body_color)
        if modo_color_qr == "Automático (Logo)" and usar_logo:
            try: c_s = logo_res.resize((1,1)).getpixel((0,0))[:3]
            except: c_s = (0,0,0)
            for i in range(size):
                r = i/size; col = tuple(int(c_s[j]*(1-r)) for j in range(3)) + (255,); draw_grad.line([(0,i),(size,i)], fill=col)
        elif modo_color_qr == "Sólido (Un Color)": draw_grad.rectangle([0,0,size,size], fill=qr_body_c1 + (255,))
        elif modo_color_qr == "Degradado Custom":
            for i in range(size):
                r = i/size; col = tuple(int(qr_body_c1[j]*(1-r)+qr_body_c2[j]*r) for j in range(3)) + (255,)
                if grad_dir_qr == "Vertical": draw_grad.line([(0,i),(size,i)], fill=col)
                elif grad_dir_qr == "Horizontal": draw_grad.line([(i,0),(i,size)], fill=col)
        else: draw_grad.rectangle([0,0,size,size], fill=(0,0,0,255))

        if usar_ojos_custom:
            img_ext_color = Image.new("RGBA", (size, size), eye_ext_color + (255,))
            img_int_color = Image.new("RGBA", (size, size), eye_int_color + (255,))
        else: img_ext_color = img_body_color; img_int_color = img_body_color

        BORDER = 40; full_size = size + (BORDER * 2)
        canvas_final = crear_fondo(full_size, full_size, modo_fondo, bg_c1, bg_c2, grad_dir_bg)
        qr_layer = Image.new("RGBA", (size, size), (0,0,0,0))
        qr_layer.paste(img_body_color, (0,0), mask=mask_body)
        qr_layer.paste(img_ext_color, (0,0), mask=mask_eye_ext)
        qr_layer.paste(img_int_color, (0,0), mask=mask_eye_int)
        
        if usar_logo: qr_layer.paste(logo_res, l_pos, logo_res)
        canvas_final.paste(qr_layer, (BORDER, BORDER), mask=qr_layer)

        suffix = "Inteligente" if is_intelligent_jpg else "Clasico"
        name = f"QR_{suffix}_{estilo.split()[0]}.png"
        full_path = os.path.join(OUTPUT_DIR, name)
        canvas_final.save(full_path, quality=100)
        
        return True, f"QR Generado:\n{name}", os.path.abspath(OUTPUT_DIR)
        
    except Exception as e:
        return False, str(e), ""


# ============================================================================
# EL PUENTE: CONECTA LA APP DEL CELULAR CON TU CÓDIGO PADRE
# ============================================================================
@app.route('/generate', methods=['POST'])
def generate():
    texto = request.form.get('texto', '')
    estilo = request.form.get('estilo', 'Normal (Cuadrado)')
    logo_file = request.files.get('logo')

    # Guardar logo temporalmente si se subió
    temp_logo_path = ""
    if logo_file:
        temp_logo_path = "temp_logo.png"
        logo_file.save(temp_logo_path)

    # Forzamos Blanco y Negro como se solicitó para el celular, llamando al Código Padre
    params_padre = {
        'logo_path': temp_logo_path,
        'estilo': estilo,
        'modo_color_qr': "Sólido (Un Color)",
        'grad_dir_qr': "Vertical",
        'usar_ojos_custom': False,
        'modo_fondo': "Blanco (Default)",
        'grad_dir_bg': "Vertical"
    }

    success, msg, path = generar_qr_clasico_engine(params_padre, texto)

    if success:
        # Extraer el nombre de archivo del mensaje y enviarlo al celular
        name = msg.split('\n')[1]
        full_path = os.path.join(path, name)
        return send_file(full_path, mimetype='image/png')
    else:
        return str(msg), 500

@app.route('/', methods=['GET'])
def home():
    return "Motor CÓDIGO PADRE V53 activado y escuchando."

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
