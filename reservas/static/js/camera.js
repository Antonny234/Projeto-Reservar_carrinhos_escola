const video = document.getElementById('video');
  const canvas = document.getElementById('canvas');
  const preview = document.getElementById('preview');
  const btnCapturar = document.getElementById('btn-capturar');
  const btnRefazer = document.getElementById('btn-refazer');
  const btnEnviar = document.getElementById('btn-enviar');
  const statusEl = document.getElementById('status');
  const selectCarrinho = document.getElementById('select-carrinho');
  const resultadoBox = document.getElementById('resultado');
  const resultadoConteudo = document.getElementById('resultado-conteudo');

  let stream = null;
  let fotoBase64 = null;

  function setStatus(msg, tipo) {
    statusEl.textContent = msg || '';
    statusEl.className = 'status' + (tipo ? ' ' + tipo : '');
  }

  async function iniciarCamera() {
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: 'environment' } }, // câmera traseira
        audio: false
      });
      video.srcObject = stream;
      setStatus('');
    } catch (err) {
      setStatus('Não foi possível acessar a câmera: ' + err.message, 'erro');
    }
  }

  function pararCamera() {
    if (stream) {
      stream.getTracks().forEach(track => track.stop());
      stream = null;
    }
  }

  btnCapturar.addEventListener('click', () => {
    const ctx = canvas.getContext('2d');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    fotoBase64 = canvas.toDataURL('image/jpeg', 0.9);
    preview.src = fotoBase64;

    video.style.display = 'none';
    preview.style.display = 'block';

    btnCapturar.style.display = 'none';
    btnRefazer.style.display = 'block';
    btnEnviar.style.display = 'block';

    pararCamera();
  });

  btnRefazer.addEventListener('click', () => {
    fotoBase64 = null;
    preview.style.display = 'none';
    video.style.display = 'block';

    btnCapturar.style.display = 'block';
    btnRefazer.style.display = 'none';
    btnEnviar.style.display = 'none';

    resultadoBox.style.display = 'none';
    setStatus('');

    iniciarCamera();
  });

  btnEnviar.addEventListener('click', async () => {
    if (!fotoBase64) return;

    btnEnviar.disabled = true;
    setStatus('Analisando imagem, aguarde...', '');

    try {
      const resp = await fetch("{% url 'analisar_foto' %}", {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
          imagem: fotoBase64,
          tipo_carrinho: selectCarrinho.value
        })
      });

      if (!resp.ok) {
        throw new Error('Erro no servidor (status ' + resp.status + ')');
      }

      const data = await resp.json();
      mostrarResultado(data);
      setStatus('Análise concluída.', 'ok');

    } catch (err) {
      setStatus('Erro ao enviar imagem: ' + err.message, 'erro');
    } finally {
      btnEnviar.disabled = false;
    }
  });

  function mostrarResultado(data) {
    resultadoConteudo.innerHTML = '';

    const totalDetectado = data.total_detectado ?? data.total ?? 0;

    if (totalDetectado === 0) {
      const aviso = document.createElement('div');
      aviso.className = 'resultado-item';
      aviso.style.color = '#f87171';
      aviso.style.justifyContent = 'center';
      aviso.innerHTML = `<strong>⚠️ Nenhum item detectado</strong>`;
      resultadoConteudo.appendChild(aviso);

      const dica = document.createElement('div');
      dica.className = 'resultado-item';
      dica.style.justifyContent = 'center';
      dica.style.fontSize = '0.85rem';
      dica.style.color = '#fbbf24';
      dica.innerHTML = `💡 Tente fotografar de outro ângulo ou rotacione o celular`;
      resultadoConteudo.appendChild(dica);

      const dica2 = document.createElement('div');
      dica2.className = 'resultado-item';
      dica2.style.justifyContent = 'center';
      dica2.style.fontSize = '0.85rem';
      dica2.style.color = '#94a3b8';
      dica2.innerHTML = `📱 Se estiver de <strong>paisagem</strong>, tente <strong>retrato</strong> (ou vice-versa)`;
      resultadoConteudo.appendChild(dica2);
    } else {
      Object.entries(data.contagens || {}).forEach(([classe, qtd]) => {
        const linha = document.createElement('div');
        linha.className = 'resultado-item';
        linha.innerHTML = `<span>${classe}</span><strong>${qtd}</strong>`;
        resultadoConteudo.appendChild(linha);
      });
    }

    const total = document.createElement('div');
    total.className = 'resultado-item';
    total.innerHTML = `<span>Total detectado</span><strong>${totalDetectado}</strong>`;
    resultadoConteudo.appendChild(total);

    resultadoBox.style.display = 'block';
  }

  // Função utilitária para pegar o token CSRF do cookie (necessário pro Django aceitar o POST)
  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let cookie of cookies) {
        cookie = cookie.trim();
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  iniciarCamera();