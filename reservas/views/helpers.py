from ..models import PerfilAdm, PerfilAdmEscola, BloqueioEquipamento


def _professor_requer_aprovacao(user, escola=None):
    """Retorna a regra de aprovação do usuário no contexto da escola."""
    try:
        perfil = user.perfil_adm
    except (PerfilAdm.DoesNotExist, AttributeError):
        perfil = None

    if perfil is not None and (escola is None or perfil.escola_id == escola.id):
        return perfil.requer_aprovacao

    try:
        perfil_multi = user.perfil_adm_escola
    except (PerfilAdmEscola.DoesNotExist, AttributeError):
        perfil_multi = None

    if perfil_multi is not None and escola is not None:
        if perfil_multi.escolas.filter(pk=escola.pk).exists():
            return perfil_multi.requer_aprovacao

    return False


def enviar_telegram(mensagem, escola=None):
    """Compatibilidade para módulos legados; usa o serviço Telegram por escola."""
    from ..telegram import enviar_telegram as _enviar_telegram
    return _enviar_telegram(mensagem, escola=escola)


def _requer_aprovacao_para_reserva(professor, equipamento):
    """Combina a regra global com a lista de professores liberados."""
    if _professor_requer_aprovacao(professor, escola=equipamento.escola):
        return True

    liberados_ids = set(
        equipamento.professores_liberados.values_list('professor_id', flat=True)
    )
    if liberados_ids and professor.id not in liberados_ids:
        return True

    return False


def _equipamentos_bloqueados(data, horario_inicio, horario_fim, escola=None):
    """IDs de equipamentos com bloqueio ativo que colide com o horário informado."""
    qs = BloqueioEquipamento.objects.filter(
        data=data,
        horario_inicio__lt=horario_fim,
        horario_fim__gt=horario_inicio,
    )
    if escola is not None:
        qs = qs.filter(equipamento__escola=escola)
    return set(qs.values_list('equipamento_id', flat=True))
