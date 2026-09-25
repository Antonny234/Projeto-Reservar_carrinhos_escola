from django.conf import settings
from ..models import PerfilAdm,BloqueioEquipamento
import requests

# ─── YOLO otimizado para Railway ────────────────────────────────
# device='cpu'  → Força execução na CPU (Railway não tem GPU)
#   Se um dia o Railway oferecer GPU, troque para 'cuda:0'.
# half=True     → Ativa FP16 (half precision), reduzindo uso de RAM ~2x
#   com pouca perda de precisão na detecção.

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


def _equipamentos_bloqueados(data, horario_inicio, horario_fim,escola=None):
    """IDs de equipamentos com bloqueio ativo que colide com o horário informado."""
    qs = BloqueioEquipamento.objects.filter(
        data=data,
        horario_inicio__lt=horario_fim,
        horario_fim__gt=horario_inicio,
    )
    if escola is not None:
        qs = qs.filter(equipamento__escola=escola)
    return set(qs.values_list('equipamento_id', flat=True))