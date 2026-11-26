from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, quote
from html import escape


# ==========================================
# 1. PRODUCTOS Y PRECIOS
# ==========================================

PRODUCTOS = {
    "brisa-grande": ("Sombrilla Brisa Grande", 289000),
    "brisa-pequena": ("Sombrilla Brisa Pequeña", 95000),
    "ventilador": ("Ventilador nebulizador portátil", 59000),
    "toalla": ("Toalla refrescante", 35000),
    "kit-verano": ("Kit de Verano", 344700)
}

CODIGO_NEGOCIO = "100PREFRESCO"
DESCUENTO_NEGOCIO = 0.25

WHATSAPP = "573000000000"


# ==========================================
# 2. FUNCIONES AUXILIARES
# ==========================================

def formato_pesos(valor):
    return "$" + format(round(valor), ",").replace(",", ".")


def obtener_valor(datos, campo, predeterminado=""):
    valores = datos.get(campo, [predeterminado])
    return valores[0] if valores else predeterminado


def obtener_cantidad(datos, producto):
    valor = obtener_valor(datos, "q_" + producto, "0")

    try:
        cantidad = int(valor)
    except ValueError:
        raise ValueError("La cantidad de los productos debe ser un número entero.")

    if cantidad < 0:
        raise ValueError("Las cantidades no pueden ser negativas.")

    return cantidad


def obtener_precio_venta(datos, producto):
    valor = obtener_valor(datos, "venta_" + producto, "")

    if not valor:
        raise ValueError(
            "Debes ingresar el precio de venta de todos los productos "
            "seleccionados para calcular las ganancias del negocio."
        )

    try:
        precio = float(valor)
    except ValueError:
        raise ValueError("Los precios de venta deben ser números válidos.")

    if precio <= 0:
        raise ValueError("Los precios de venta deben ser mayores que cero.")

    return precio


# ==========================================
# 3. PROCESAR EL PEDIDO
# ==========================================

def calcular_pedido(datos):

    modo = obtener_valor(datos, "modo", "cliente")
    codigo = obtener_valor(datos, "codigo").strip().upper()

    if modo not in ("cliente", "negocio"):
        raise ValueError("Selecciona un modo de cálculo válido.")

    items = []
    subtotal = 0
    ingresos = 0
    unidades = 0

    for producto_id, producto_info in PRODUCTOS.items():

        nombre, precio_base = producto_info
        cantidad = obtener_cantidad(datos, producto_id)

        if cantidad == 0:
            continue

        precio_venta = None

        if modo == "negocio":
            precio_venta = obtener_precio_venta(datos, producto_id)
            ingresos += precio_venta * cantidad

        total_linea = precio_base * cantidad
        subtotal += total_linea
        unidades += cantidad

        items.append({
            "id": producto_id,
            "nombre": nombre,
            "cantidad": cantidad,
            "precio": precio_base,
            "total": total_linea,
            "precio_venta": precio_venta
        })

    if not items:
        raise ValueError("Debes seleccionar al menos un producto.")

    # ======================================
    # 4. APLICAR DESCUENTO
    # ======================================

    descuento = 0
    mensaje_codigo = ""

    if codigo == CODIGO_NEGOCIO:

        if modo == "negocio":
            descuento = subtotal * DESCUENTO_NEGOCIO
            mensaje_codigo = "¡Código aplicado! Se otorgó un descuento del 25%."

        else:
            mensaje_codigo = (
                "El código 100PREFRESCO es exclusivo para clientes "
                "con un negocio. No se aplicó descuento."
            )

    elif codigo:
        mensaje_codigo = (
            "El código ingresado no es válido. No se aplicó descuento."
        )

    total = subtotal - descuento

    # ======================================
    # 5. CALCULAR GANANCIA Y MARGEN
    # ======================================

    ganancia = 0
    margen = 0

    if modo == "negocio":

        ganancia = ingresos - total

        if ingresos > 0:
            margen = (ganancia / ingresos) * 100

    # ======================================
    # 6. CONSTRUIR RESULTADO
    # ======================================

    resultado = {
        "modo": modo,
        "items": items,
        "unidades": unidades,
        "subtotal": subtotal,
        "descuento": descuento,
        "total": total,
        "ingresos": ingresos,
        "ganancia": ganancia,
        "margen": margen,
        "mensaje_codigo": mensaje_codigo
    }

    return resultado


# ==========================================
# 7. GENERAR MENSAJE PARA WHATSAPP
# ==========================================

def texto_whatsapp(resultado):

    mensaje = "Hola AquaSombra, quiero cotizar este pedido:\n\n"

    for item in resultado["items"]:
        mensaje += (
            f"- {item['nombre']} x {item['cantidad']}: "
            f"{formato_pesos(item['total'])}\n"
        )

    mensaje += f"\nSubtotal: {formato_pesos(resultado['subtotal'])}"

    if resultado["descuento"] > 0:
        mensaje += (
            f"\nDescuento: {formato_pesos(resultado['descuento'])}"
        )

    mensaje += f"\nTotal: {formato_pesos(resultado['total'])}"

    if resultado["modo"] == "negocio":
        mensaje += (
            f"\nIngresos estimados: {formato_pesos(resultado['ingresos'])}"
            f"\nGanancia estimada: {formato_pesos(resultado['ganancia'])}"
            f"\nMargen: {resultado['margen']:.2f}%"
        )

    return mensaje


# ==========================================
# 8. GENERAR PÁGINA DE RESULTADOS
# ==========================================

def generar_pagina(resultado):

    filas = ""

    for item in resultado["items"]:

        filas += f"""
            <tr>
                <td>{escape(item['nombre'])}</td>
                <td>{item['cantidad']}</td>
                <td>{formato_pesos(item['precio'])}</td>
                <td>{formato_pesos(item['total'])}</td>
            </tr>
        """

    descuento_html = ""

    if resultado["descuento"] > 0:
        descuento_html = f"""
            <div class="fila">
                <span>Descuento (25%)</span>
                <strong>- {formato_pesos(resultado['descuento'])}</strong>
            </div>
        """

    negocio_html = ""

    if resultado["modo"] == "negocio":

        negocio_html = f"""
            <div class="seccion-negocio">
                <h2>Resumen de tu negocio</h2>

                <div class="fila">
                    <span>Ingresos estimados</span>
                    <strong>{formato_pesos(resultado['ingresos'])}</strong>
                </div>

                <div class="fila">
                    <span>Ganancia estimada</span>
                    <strong>{formato_pesos(resultado['ganancia'])}</strong>
                </div>

                <div class="fila">
                    <span>Margen de ganancia</span>
                    <strong>{resultado['margen']:.2f}%</strong>
                </div>
            </div>
        """

        if resultado["ganancia"] > 0:
            mensaje = "¡Excelente! Tu negocio tendría una ganancia estimada positiva."
        elif resultado["ganancia"] == 0:
            mensaje = "Tu negocio recuperaría la inversión, pero no tendría ganancia."
        else:
            mensaje = "El cálculo muestra una pérdida estimada. Revisa tus precios de venta."

    else:
        mensaje = "Este es el valor estimado de tu pedido. ¡Gracias por elegir AquaSombra!"

    mensaje_codigo_html = ""

    if resultado["mensaje_codigo"]:
        mensaje_codigo_html = f"""
            <p class="mensaje-codigo">
                {escape(resultado['mensaje_codigo'])}
            </p>
        """

    mensaje_whatsapp = quote(texto_whatsapp(resultado))
    enlace_whatsapp = (
        f"https://wa.me/{WHATSAPP}?text={mensaje_whatsapp}"
    )

    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Resultado de tu pedido | AquaSombra</title>
        <link rel="stylesheet" href="/css/styles.css">

        <style>
            body {{
                margin: 0;
                padding: 30px 15px;
                background: #f1f8fc;
                font-family: Arial, sans-serif;
                color: #173b55;
            }}

            .resultado-pagina {{
                max-width: 850px;
                margin: 30px auto;
                padding: 30px;
                background: white;
                border-radius: 18px;
                box-shadow: 0 5px 25px rgba(0,0,0,.08);
            }}

            .resultado-pagina h1 {{
                color: #087e9b;
                text-align: center;
            }}

            .resultado-pagina h2 {{
                margin-top: 28px;
                color: #087e9b;
            }}

            .tabla-pedido {{
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
            }}

            .tabla-pedido th,
            .tabla-pedido td {{
                padding: 12px 8px;
                border-bottom: 1px solid #e2edf2;
                text-align: left;
            }}

            .tabla-pedido th {{
                background: #eaf6fa;
            }}

            .fila {{
                display: flex;
                justify-content: space-between;
                gap: 15px;
                padding: 12px 0;
                border-bottom: 1px solid #e2edf2;
            }}

            .total {{
                margin-top: 15px;
                padding: 18px;
                background: #eaf6fa;
                border-radius: 10px;
                font-size: 1.25rem;
            }}

            .seccion-negocio {{
                margin-top: 25px;
                padding: 20px;
                background: #f5fafc;
                border-radius: 12px;
            }}

            .mensaje {{
                margin: 20px 0;
                padding: 15px;
                background: #f0f8f4;
                border-radius: 10px;
                line-height: 1.6;
            }}

            .mensaje-codigo {{
                padding: 12px;
                background: #fff8e8;
                border-radius: 8px;
            }}

            .botones {{
                display: flex;
                flex-wrap: wrap;
                justify-content: center;
                gap: 12px;
                margin-top: 25px;
            }}

            .botones a {{
                display: inline-block;
                padding: 13px 20px;
                border-radius: 8px;
                text-decoration: none;
                font-weight: bold;
            }}

            .boton-volver {{
                background: #087e9b;
                color: white;
            }}

            .boton-whatsapp {{
                background: #25d366;
                color: white;
            }}

            @media(max-width: 600px) {{
                .resultado-pagina {{
                    padding: 18px;
                }}

                .tabla-pedido {{
                    font-size: 13px;
                }}

                .tabla-pedido th,
                .tabla-pedido td {{
                    padding: 8px 4px;
                }}
            }}
        </style>
    </head>

    <body>

        <main class="resultado-pagina">

            <h1>¡Tu cálculo está listo!</h1>

            <p style="text-align:center;">
                AquaSombra | Vive fresco. Vive mejor.
            </p>

            <h2>Resumen de tu pedido</h2>

            <table class="tabla-pedido">
                <thead>
                    <tr>
                        <th>Producto</th>
                        <th>Cantidad</th>
                        <th>Precio unidad</th>
                        <th>Total</th>
                    </tr>
                </thead>

                <tbody>
                    {filas}
                </tbody>
            </table>

            <div class="fila">
                <span>Unidades seleccionadas</span>
                <strong>{resultado['unidades']}</strong>
            </div>

            <div class="fila">
                <span>Subtotal</span>
                <strong>{formato_pesos(resultado['subtotal'])}</strong>
            </div>

            {descuento_html}

            <div class="fila total">
                <strong>Total</strong>
                <strong>{formato_pesos(resultado['total'])}</strong>
            </div>

            {negocio_html}

            {mensaje_codigo_html}

            <div class="mensaje">
                {escape(mensaje)}
            </div>

            <div class="botones">

                <a class="boton-volver" href="/#calculadora">
                    Volver a AquaSombra
                </a>

                <a class="boton-whatsapp"
                   href="{enlace_whatsapp}"
                   target="_blank"
                   rel="noopener">
                    Enviar cotización por WhatsApp
                </a>

            </div>

        </main>

    </body>
    </html>
    """


# ==========================================
# 9. CONEXIÓN CON VERCEL
# ==========================================

class handler(BaseHTTPRequestHandler):

    def do_GET(self):

        contenido = """
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <title>AquaSombra</title>
        </head>
        <body>
            <h2>Calculadora AquaSombra</h2>
            <p>Para realizar un cálculo, vuelve a la página principal
            y envía el formulario.</p>
            <a href="/">Volver al inicio</a>
        </body>
        </html>
        """

        self.enviar_respuesta(contenido)

    def do_POST(self):

        try:
            longitud = int(self.headers.get("Content-Length", 0))
            cuerpo = self.rfile.read(longitud).decode("utf-8")

            datos = parse_qs(cuerpo, keep_blank_values=True)

            resultado = calcular_pedido(datos)

            contenido = generar_pagina(resultado)

            self.enviar_respuesta(contenido)

        except ValueError as error:

            contenido = f"""
            <!DOCTYPE html>
            <html lang="es">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Error en el cálculo | AquaSombra</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        background: #f1f8fc;
                        padding: 30px;
                        text-align: center;
                    }}
                    .caja {{
                        max-width: 550px;
                        margin: 50px auto;
                        padding: 30px;
                        background: white;
                        border-radius: 15px;
                    }}
                    a {{
                        display: inline-block;
                        margin-top: 20px;
                        padding: 12px 20px;
                        background: #087e9b;
                        color: white;
                        border-radius: 8px;
                        text-decoration: none;
                    }}
                </style>
            </head>
            <body>
                <div class="caja">
                    <h1>No pudimos realizar el cálculo</h1>
                    <p>{escape(str(error))}</p>
                    <a href="/#calculadora">Volver a la calculadora</a>
                </div>
            </body>
            </html>
            """

            self.enviar_respuesta(contenido, 400)

        except Exception:

            contenido = """
            <html lang="es">
            <head><meta charset="UTF-8"><title>Error</title></head>
            <body>
                <h2>Ocurrió un error al procesar tu pedido.</h2>
                <a href="/#calculadora">Volver a la calculadora</a>
            </body>
            </html>
            """

            self.enviar_respuesta(contenido, 500)

    def enviar_respuesta(self, contenido, estado=200):

        respuesta = contenido.encode("utf-8")

        self.send_response(estado)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(respuesta)))
        self.end_headers()

        self.wfile.write(respuesta)