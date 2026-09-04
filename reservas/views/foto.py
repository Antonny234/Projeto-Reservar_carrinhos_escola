import json
import base64
import io

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from PIL import Image, ImageDraw, ImageFont, ImageOps

from .helpers import IMGSZ, IOU_THRESHOLD, modelo_yolo, CONFIANCA_MINIMA




CORES_CLASSES = {}
PALETA = [
    (255, 0, 0),
    (0, 255, 0),
    (0, 0, 255),
    (255, 255, 0),
    (255, 0, 255),
    (0, 255, 255),
    (255, 128, 0),
    (128, 0, 255),
]


def _get_cor_classe(classe_id):
    if classe_id not in CORES_CLASSES:
        CORES_CLASSES[classe_id] = PALETA[classe_id % len(PALETA)]
    return CORES_CLASSES[classe_id]


def _corrigir_orientacao_exif(imagem):
    """Corrige a orientação da imagem baseada nos metadados EXIF."""
    try:
        imagem_corrigida = ImageOps.exif_transpose(imagem)
        if imagem_corrigida is not None:
            return imagem_corrigida
    except Exception:
        pass
    return imagem


def _rodar_inferencia(imagem, tipo_carrinho, confianca_minima=None):
    """Executa a inferência do YOLO na imagem fornecida e retorna contagens e objetos."""
    conf = confianca_minima if confianca_minima is not None else CONFIANCA_MINIMA

    resultados = modelo_yolo.predict(
        source=imagem,
        conf=conf,
        iou=IOU_THRESHOLD,
        imgsz=IMGSZ,
        verbose=False,
        augment=False,
    )

    deteccoes = resultados[0]
    contagens = {}
    objetos_detectados = []

    for box in deteccoes.boxes:
        classe_id = int(box.cls[0])
        nome_classe = modelo_yolo.names[classe_id]
        confianca = float(box.conf[0])
        x1, y1, x2, y2 = [int(v) for v in box.xyxy[0]]

        if tipo_carrinho and tipo_carrinho.lower() not in nome_classe.lower():
            continue

        contagens[nome_classe] = contagens.get(nome_classe, 0) + 1
        objetos_detectados.append({
            "classe": nome_classe,
            "confianca": round(confianca, 2),
            "x1": x1, "y1": y1, "x2": x2, "y2": y2,
        })

    total_detectado = sum(contagens.values())
    return contagens, objetos_detectados, total_detectado


def _tentar_rotacoes(imagem_original, tipo_carrinho):
    """
    Tenta detectar objetos rotacionando a imagem em 90°, 180° e 270°.
    Retorna o melhor resultado (com mais detecções).
    """
    melhor_total = 0
    melhor_contagens = {}
    melhor_objetos = []
    melhor_rotacao = 0
    melhor_imagem = imagem_original

    # Tenta as 3 rotações
    for angulo in [90, 180, 270]:
        img_rotacionada = imagem_original.rotate(angulo, expand=True, resample=Image.BICUBIC)
        contagens, objetos, total = _rodar_inferencia(img_rotacionada, tipo_carrinho)

        if total > melhor_total:
            melhor_total = total
            melhor_contagens = contagens
            melhor_objetos = objetos
            melhor_rotacao = angulo
            melhor_imagem = img_rotacionada

    return melhor_contagens, melhor_objetos, melhor_total, melhor_rotacao, melhor_imagem


@require_POST
@csrf_protect
def analisar_foto(request):
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"erro": "JSON inválido."}, status=400)

    imagem_base64 = body.get("imagem")
    tipo_carrinho = body.get("tipo_carrinho", "")

    if not imagem_base64:
        return JsonResponse({"erro": "Nenhuma imagem enviada."}, status=400)

    try:
        if "," in imagem_base64:
            imagem_base64 = imagem_base64.split(",", 1)[1]
        imagem_bytes = base64.b64decode(imagem_base64)
        imagem = Image.open(io.BytesIO(imagem_bytes)).convert("RGB")
    except Exception:
        return JsonResponse({"erro": "Não foi possível processar a imagem."}, status=400)

    # 1. Corrigir orientação EXIF automaticamente
    imagem = _corrigir_orientacao_exif(imagem)

    # 2. Primeira tentativa de inferência na imagem corrigida
    contagens, objetos_detectados, total_detectado = _rodar_inferencia(imagem, tipo_carrinho)

    rotacao_aplicada = 0
    imagem_para_anotacao = imagem

    # 3. Se não detectou nada, tenta com confiança reduzida
    if total_detectado == 0:
        contagens, objetos_detectados, total_detectado = _rodar_inferencia(
            imagem, tipo_carrinho, confianca_minima=0.25
        )

    # 4. Se ainda não detectou nada, tenta rotacionar a imagem
    if total_detectado == 0:
        (contagens, objetos_detectados, total_detectado,
         rotacao_aplicada, imagem_para_anotacao) = _tentar_rotacoes(imagem, tipo_carrinho)

    draw = ImageDraw.Draw(imagem_para_anotacao)

    try:
        font_large = ImageFont.truetype("arial.ttf", 20)
        font_small = ImageFont.truetype("arial.ttf", 14)
    except (IOError, OSError):
        try:
            font_large = ImageFont.truetype("DejaVuSans-Bold.ttf", 20)
            font_small = ImageFont.truetype("DejaVuSans.ttf", 14)
        except (IOError, OSError):
            font_large = ImageFont.load_default()
            font_small = ImageFont.load_default()

    for obj in objetos_detectados:
        cor = _get_cor_classe(list(modelo_yolo.names.keys())[
            list(modelo_yolo.names.values()).index(obj["classe"])
        ] if obj["classe"] in modelo_yolo.names.values() else 0)

        x1, y1, x2, y2 = obj["x1"], obj["y1"], obj["x2"], obj["y2"]

        for offset in range(-2, 3):
            draw.rectangle(
                [x1 + offset, y1 + offset, x2 + offset, y2 + offset],
                outline=cor, width=3
            )

        label = f"{obj['classe']} {obj['confianca']:.2f}"

        try:
            bbox_texto = draw.textbbox((0, 0), label, font=font_small)
            largura_texto = bbox_texto[2] - bbox_texto[0]
            altura_texto = bbox_texto[3] - bbox_texto[1]
        except Exception:
            largura_texto = len(label) * 8
            altura_texto = 16

        label_x1 = x1
        label_y1 = y1 - altura_texto - 6 if y1 - altura_texto - 6 > 0 else y1
        label_x2 = x1 + largura_texto + 10
        label_y2 = label_y1 + altura_texto + 6

        draw.rectangle([label_x1, label_y1, label_x2, label_y2], fill=cor)

        try:
            cor_texto = (255, 255, 255)
            luminancia = 0.299 * cor[0] + 0.587 * cor[1] + 0.114 * cor[2]
            if luminancia > 180:
                cor_texto = (0, 0, 0)
            draw.text((label_x1 + 5, label_y1 + 3), label, fill=cor_texto, font=font_small)
        except Exception:
            draw.text((label_x1 + 5, label_y1 + 3), label, fill=(255, 255, 255))

    header_text = f"Total: {total_detectado}"
    if contagens:
        detalhes = " | ".join([f"{k}: {v}" for k, v in contagens.items()])
        header_text = f"{header_text} | {detalhes}"

    img_w, img_h = imagem_para_anotacao.size
    try:
        bbox_header = draw.textbbox((0, 0), header_text, font=font_large)
        h_header = bbox_header[3] - bbox_header[1] + 20
    except Exception:
        h_header = 40

    draw.rectangle([0, 0, img_w, h_header], fill=(0, 0, 0, 180))
    try:
        draw.text((10, 10), header_text, fill=(255, 255, 255), font=font_large)
    except Exception:
        draw.text((10, 10), header_text, fill=(255, 255, 255))

    buffer = io.BytesIO()
    imagem_para_anotacao.save(buffer, format="JPEG", quality=85)
    imagem_anotada_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    imagem_anotada_data_uri = f"data:image/jpeg;base64,{imagem_anotada_base64}"

    return JsonResponse({
        "contagens": contagens,
        "total_detectado": total_detectado,
        "tipo_carrinho": tipo_carrinho,
        "imagem_anotada": imagem_anotada_data_uri,
        "objetos": objetos_detectados,
    })

