function adicionarAoMural() {
    const professor = document.getElementById('nome-professor').innerText;
    const carrinho = document.getElementById('carrinho').value;
    const sala = document.getElementById('sala').value;
    const horario = document.getElementById('id_periodo').value;

    if (!carrinho || !sala || !horario) {
        alert("Por favor, preencha todos os campos!");
        return;
    }

    const mural = document.getElementById('grid-mural');
    const card = document.createElement('div');
    card.className = 'card';
    card.innerHTML = `
        <strong>${professor}</strong><br>
        <small>ID Equipamento: ${carrinho}</small><br>
        <strong>Local:</strong> ${sala}<br>
        <strong>Horário:</strong> ${horario}
    `;
    mural.appendChild(card);

    document.getElementById('sala').value = '';
    document.getElementById('id_periodo').value = '';
}

document.addEventListener('DOMContentLoaded', function () {
    const campoData = document.getElementById('id_data');
    const campoPeriodo = document.getElementById('id_periodo');
    const selectCarrinho = document.getElementById('carrinho');
    const gridMural = document.getElementById('grid-mural');
    const infoQuantidade = document.getElementById('quantidade-info');

    // ✅ FUNÇÃO ÚNICA (sem duplicação)
    function desabilitarHorariosPassados() {
        const dataInput = campoData.value;
        
        // Obter data e hora atuais em Brasília
        const agoraBrasil = new Date().toLocaleString("en-US", {timeZone: "America/Sao_Paulo"});
        const dataAtualBrasil = new Date(agoraBrasil);
        
        const hoje = dataAtualBrasil.toISOString().split('T')[0];
        const horaAtual = dataAtualBrasil.getHours();
        const minAtual = dataAtualBrasil.getMinutes();

        const options = campoPeriodo.querySelectorAll('option');
        options.forEach(opt => {
            if (opt.value && opt.value.includes('|')) {
                const [hInicio, hFim] = opt.value.split('|');
                const [hI, mI] = hInicio.split(':').map(Number);
                const [hF, mF] = hFim.split(':').map(Number);
                
                // ✅ CORRETO: Bloqueia se o FIM do horário já passou
                if (dataInput === hoje && (hF < horaAtual || (hF === horaAtual && mF <= minAtual))) {
                    opt.disabled = true;
                } else {
                    opt.disabled = false;
                }
            }
        });
    }

    function atualizarMural() {
        const dataSelecionada = campoData.value;
        const periodo = campoPeriodo.value; // ex: "07:00|07:50"
        let url = `/ajax/mural-filtrado/?data=${dataSelecionada}`;
        if (periodo && periodo.includes('|')) {
            const [inicio, fim] = periodo.split('|');
            url += `&inicio=${inicio}&fim=${fim}`;
        }

        if (dataSelecionada) {
            fetch(url)
                .then(response => response.text())
                .then(html => {
                    gridMural.innerHTML = html;
                })
                .catch(error => console.error('Erro ao carregar o mural:', error));
        }
    }
    gridMural.addEventListener('submit',function (e){
        const form = e.target.closest('.form-excluir');
        if (!form) return;
        e.preventDefault();
        if (!confirm('Excluir esta reserva')) return;

        fetch(form.action, { method: 'POST', body: new FormData(form) })
            .then(() => atualizarMural())
            .catch(err => console.error('Erro ao Excluir', err));
    })
   function definirHorarios() {
        let valor = document.getElementById("id_periodo").value;
        if (valor) {
            let partes = valor.split("|");
            document.getElementById("horario_inicio").value = partes[0];
            document.getElementById("horario_fim").value = partes[1];
        }
    }

    function atualizarCarrinhos() {
        const data = campoData.value;
        const periodo = campoPeriodo.value;

        infoQuantidade.innerHTML = 'Quantidade Atual:-';

        if (data && periodo) {
            let partes = periodo.split("|");
            let horario_inicio = partes[0];
            let horario_fim = partes[1];

            // Envia o estado da "aula seguida" para o backend filtrar
            // carrinhos livres nos DOIS horários seguidos.
            const aulaSeguidaInput = document.getElementById('aula_seguida');
            const aulaSeguida = aulaSeguidaInput && aulaSeguidaInput.value === 'sim' ? 'sim' : 'nao';

            let url = `/ajax/disponiveis/?data=${data}&horario_inicio=${horario_inicio}&horario_fim=${horario_fim}`;
            if (aulaSeguida === 'sim') url += `&aula_seguida=sim`;

            fetch(url)
                .then(response => response.json())
                .then(dados => {
                    selectCarrinho.innerHTML = '<option value="">Qual carrinho?</option>';
                    dados.equipamentos.forEach(item => {
                        const option = new Option(`${item.nome}`, item.id);
                        option.dataset.quantidade = item.quantidade;
                        selectCarrinho.add(option);
                    });
                    selectCarrinho.disabled = false;

                    // Mostra qual é o próximo horário real considerado na aula dupla,
                    // ou avisa se não existe próximo horário válido.
                    if (aulaSeguida === 'sim') {
                        if (dados.proximo_horario) {
                            infoQuantidade.innerHTML =
                                `Aula dupla: ${dados.proximo_horario.inicio}–${dados.proximo_horario.fim} será reservado também.`;
                        } else if (!dados.aula_dupla_valida) {
                            infoQuantidade.innerHTML =
                                `⚠️ Não existe próximo horário de aula depois de ${horario_inicio}–${horario_fim}. Só este horário será reservado.`;
                        }
                    }
                })
                .catch(error => console.error('Erro ao buscar equipamentos:', error));
        } else {
            selectCarrinho.disabled = true;
            selectCarrinho.innerHTML = '<option value="">Selecione data e período...</option>';
        }
    }

    selectCarrinho.addEventListener('change', function () {
        const valorSelecionado = selectCarrinho.value;

        if (valorSelecionado === "") {
            infoQuantidade.innerHTML = `-`;
            return;
        }

        const opcaoSelecionada = selectCarrinho.options[selectCarrinho.selectedIndex];
        const quantidade = opcaoSelecionada.dataset.quantidade;

        if (quantidade !== undefined && quantidade !== null) {
            infoQuantidade.innerHTML = `Quantidade Atual: <strong>${quantidade}</strong>`;
        } else {
            infoQuantidade.innerHTML = `Quantidade Atual: -`;
        }
    });

    campoPeriodo.addEventListener('change', () => {
        definirHorarios();
        atualizarCarrinhos();
        atualizarMural(); // Agora dispara o filtro no mural
    });

    // Quando ligar/desligar "aula seguida", refaz a busca de carrinhos
    // (o backend passa a exigir disponibilidade nos dois horários).
    const btnAulaSeguida = document.getElementById('btn-aula-seguida');
    if (btnAulaSeguida) {
        btnAulaSeguida.addEventListener('click', () => {
            atualizarCarrinhos();
        });
    }

    //desabilitarHorariosPassados();
   campoData.addEventListener('change', () => {
        atualizarMural();
        atualizarCarrinhos();
        //desabilitarHorariosPassados();
    });

    window.definirHorarios = definirHorarios;
    atualizarMural();
});

let menuCarregado = false;

async function toggleSidebar() {

    const sidebar = document.getElementById("sidebar");

    const overlay = document.getElementById("sidebar-overlay");

    if (!menuCarregado) {

        const resposta = await fetch("/ajax/menu/");

        const html = await resposta.text();

        sidebar.innerHTML = html;

        menuCarregado = true;
    }

    sidebar.classList.add("aberta");

    overlay.classList.add("ativo");

}

function fecharSidebar() {

    document
        .getElementById("sidebar")
        .classList.remove("aberta");

    document
        .getElementById("sidebar-overlay")
        .classList.remove("ativo");

}

function abrirFicha(reservaId, turma, professor) {
            document.getElementById('modal-titulo').textContent = `Turma ${turma}`;
            document.getElementById('modal-loading').style.display = 'block';
            document.getElementById('modal-tabela').style.display = 'none';
            document.getElementById('modal-info').textContent = '';
            document.getElementById('modal-btn-excel').href = `/fichas/${reservaId}/excel/`;
            document.getElementById('modal-ficha').classList.add('ativo');

            fetch(`/fichas/${reservaId}/json/`)
                .then(r => r.json())
                .then(data => {
                    document.getElementById('modal-info').textContent =
                        `${data.professor} · ${data.data} · ${data.horario} · ${data.sala} · ${data.equipamento}`;

                    const tbody = document.getElementById('modal-tbody');
                    tbody.innerHTML = '';
                    data.registros.forEach((reg, i) => {
                        tbody.innerHTML += `
                            <tr>
                                <td>${i + 1}</td>
                                <td>${reg.aluno}</td>
                                <td>${reg.turma}</td>
                                <td>${reg.notebook}</td>
                            </tr>`;
                    });

                    document.getElementById('modal-loading').style.display = 'none';
                    document.getElementById('modal-tabela').style.display = 'table';
                });
        }

        function fecharModal() {
            document.getElementById('modal-ficha').classList.remove('ativo');
        }

        document.addEventListener('keydown', e => {
            if (e.key === 'Escape') fecharModal();
        });
