from django.conf import settings
from ultralytics import YOLO
from ..models import PerfilAdm

MODEL_PATH = settings.BASE_DIR / "modelos" / "best.pt"

# ─── YOLO otimizado para Railway ────────────────────────────────
# device='cpu'  → Força execução na CPU (Railway não tem GPU)
#   Se um dia o Railway oferecer GPU, troque para 'cuda:0'.
# half=True     → Ativa FP16 (half precision), reduzindo uso de RAM ~2x
#   com pouca perda de precisão na detecção.
modelo_yolo = YOLO(str(MODEL_PATH)).to('cpu')
modelo_yolo.predict(source=None, device='cpu', half=True, verbose=False)

CONFIANCA_MINIMA = 0.35
IOU_THRESHOLD = 0.45
IMGSZ = 640  # Tamanho da imagem para inferência (menor = mais rápido e menos RAM)


def _professor_requer_aprovacao(user):
    try:
        return user.perfil_adm.requer_aprovacao
    except (PerfilAdm.DoesNotExist, AttributeError):
        return False
