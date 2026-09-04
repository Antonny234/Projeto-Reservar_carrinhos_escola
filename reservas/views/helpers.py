from django.conf import settings
from ultralytics import YOLO
from ..models import PerfilAdm,BloqueioEquipamento
import requests

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

def enviar_telegram(mensagem):
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        requests.post(url, data={
            "chat_id": chat_id,
            "text": mensagem,
            "parse_mode": "HTML"
        }, timeout=5)
    except requests.RequestException as e:
        print(f"Erro ao enviar Telegram: {e}")

def _requer_aprovacao_para_reserva(professor, equipamento):
    """Combina a regra global (PerfilAdm) com a lista de liberados do próprio equipamento."""
    if _professor_requer_aprovacao(professor):
        return True

    liberados_ids = set(equipamento.professores_liberados.values_list('professor_id', flat=True))
    if liberados_ids and professor.id not in liberados_ids:
        return True

    return False


def _equipamentos_bloqueados(data, horario_inicio, horario_fim):
    """IDs de equipamentos com bloqueio ativo que colide com o horário informado."""
    return set(
        BloqueioEquipamento.objects.filter(
            data=data,
            horario_inicio__lt=horario_fim,
            horario_fim__gt=horario_inicio,
        ).values_list('equipamento_id', flat=True)
    )