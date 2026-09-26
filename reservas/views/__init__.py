from .area_usuario import (
    home, CriarConta, Entrar, sair, confirmar_cadastro, reenviar_codigo_cadastro,
    listar_disponiveis, mural, todos_horarios, excluir_reserva, numeros_disponiveis,
    carregar_mural, carregar_mural_publico, carrinho_principal, atualizar_quantidade,
    criar_pin, buscar_reserva_ativa, reportar_notebook_quebrado, escolher_carrinho,
    login_ajax, view_tablet, status_tablet, pagina_unico, reserva_quantidade,
    preencher_numeracao_quantidade,
)
from .cadastro import (
    cadastros, adicionar_sala, adicionar_aluno, importar_alunos,
    confirmar_importacao_alunos, adicionar_equipamento, editar_equipamento,
    remover_liberacao, remover_bloqueio, excluir_equipamento, adicionar_horario,
    editar_horario, excluir_horario,
)
from .are_admin import (
    exportar_todas_fichas, exportar_ficha_excel, exportar_reservas_excel,
    painel_fichas, ficha_detalhe_json, verificar_fichas_ausentes,
    notebooks_quebrados, reativar_notebook, verificar_carrinho,
    atualizar_faixa_numeracao, alternar_status_notebook, painel_reservas_dia,
    pendentes_numeracao, painel_reservas_quantidade, menu_ajax, aprovar_reserva,
    recusar_reserva, reserva_fixas_web, lista_reservas_fixas, excluir_reserva_fixa,
    analise_sistema,
)
from .inventario import (
    inventario_lista, configurar_campos_inventario, grupo_equipamentos,
    inventario_detalhe, equipamento_novo, grupo_novo, transferir_equipamento,
    equipamento_editar, equipamento_excluir, grupo_excluir,
)
from .redefinir_senha import redefinir_senha_usuario, redefinir_senha_confirmar
from .escola import trocar_escola_ativa
from .superadmin import (
    superadmin_painel, cadastrar_escola, gerenciar_escola, adicionar_administrador,
    listar_escolas, listar_usuarios, listar_administradores, listar_professores,
)

__all__ = [name for name in globals() if not name.startswith('_')]
from .telegram import telegram_painel, telegram_webhook
from .transferencias_escola import transferencias_pendentes, iniciar_transferencia_escola, receber_transferencia_escola, checklist_transferencia_escola, comprovante_transferencia_escola
