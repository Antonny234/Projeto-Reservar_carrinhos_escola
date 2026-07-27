from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('criar/', views.CriarConta, name='index'),
    path('entrar/', views.Entrar, name='longa'),
    path('Logar/', views.mural, name='mural'),
    path('exportar-excel/', views.exportar_reservas_excel, name='exportar_excel'),
    path('ajax/mural-filtrado/', views.carregar_mural, name='ajax_mural'),
    path('carregar-mural-publico/', views.carregar_mural_publico, name='carregar_mural_publico'),
    path('ajax/disponiveis/', views.listar_disponiveis, name='ajax_disponiveis'),
    #mural publico
    path('painel/', views.carrinho_principal, name='mural_consulta'),
    path('carregar-mural/', views.carregar_mural, name='carregar_mural'),
    path('excluir-reserva/<int:reserva_id>/', views.excluir_reserva, name='excluir_reserva'),
    path('atualizar-quantidade/', views.atualizar_quantidade, name='atualizar_quantidade'),
    path('tablet/<int:equipamento_id>/', views.view_tablet, name='tablet_checkin'),
    # Fichas
    path('fichas/', views.painel_fichas, name='painel_fichas'),
    path('fichas/<int:reserva_id>/json/', views.ficha_detalhe_json, name='ficha_detalhe_json'),
    path('fichas/<int:reserva_id>/excel/', views.exportar_ficha_excel, name='exportar_ficha_excel'),
    path('fichas/excel-tudo/', views.exportar_todas_fichas, name='exportar_todas_excel'),
    # Aprovação de reservas
    path('reserva/<int:reserva_id>/aprovar/', views.aprovar_reserva, name='aprovar_reserva'),
    path('reserva/<int:reserva_id>/recusar/', views.recusar_reserva, name='recusar_reserva'),
    # Notificações fichas ausentes
    path('ajax/fichas-ausentes/', views.verificar_fichas_ausentes, name='fichas_ausentes'),
    #aparecer nomes dos profesores e as turmas salvas no banco de dados
    path('select2/', include('django_select2.urls')),
    path('tablet/<int:equipamento_id>/status/', views.status_tablet, name='tablet_status'),
    #verificação da numeração dos notebooks
    path('verificar-carrinho/', views.verificar_carrinho, name='verificar_carrinho'),
    path('verificar-carrinho/alternar-status/', views.alternar_status_notebook, name='alternar_status_notebook'),

    path('verificar-carrinho/atualizar-faixa/', views.atualizar_faixa_numeracao, name='atualizar_faixa_numeracao'),
    #painel de reservas
    path('painel-reservas/', views.painel_reservas_dia, name='painel_reservas_dia'),
    path('fichas/analisar-foto/', views.analisar_foto, name='analisar_foto'),
    path('camera/', views.camera_contagem, name='camera_contagem'),
    #numeração dos notebooks
    path('ajax/numeros-disponiveis/', views.numeros_disponiveis, name='numeros_disponiveis'),
    path('unico/', views.pagina_unico, name='unico'),
    path('reserva-quantidade/', views.reserva_quantidade, name='reserva_quantidade'),
    path('reserva/<int:reserva_id>/numeracao/', views.preencher_numeracao_quantidade, name='preencher_numeracao_quantidade'),
    path('painel/pendentes-numeracao/', views.pendentes_numeracao, name='pendentes_numeracao'),
    path('painel/reservas-quantidade/', views.painel_reservas_quantidade, name='painel_reservas_quantidade'),
    path("ajax/menu/",views.menu_ajax,name="menu_ajax"),
    path('criar-pin/', views.criar_pin, name='criar_pin'),
]
