Dropzone.autoDiscover = false;

// Elementos da UI
const dropzoneForm = document.getElementById("myDropzone");
const uploadedFilesContainer = document.getElementById("uploadedFilesContainer"); // Novo container para múltiplos arquivos
const conversionOptionsDisplay = document.getElementById("conversionOptionsDisplay"); // Substitui fileInfoDisplay
const formatSelect = document.getElementById("formatSelect");
const convertButton = document.getElementById("convertButton");
const conversionResultDiv = document.getElementById("conversionResult");

// Novos elementos para a tela de sucesso
const conversionSuccessDisplay = document.getElementById("conversionSuccessDisplay");
const loadAnotherFileBtn = document.getElementById("loadAnotherFileBtn");
const finalDownloadLink = document.getElementById("finalDownloadLink");

let uploadedFiles = []; // Array para armazenar informações de todos os arquivos enviados
let availableFormats = new Set(); // Para coletar formatos disponíveis de todos os arquivos

// Função para resetar a interface para o estado inicial (Dropzone visível)
function resetUI() {
  dropzoneForm.style.display = 'flex'; // Mostra o Dropzone
  uploadedFilesContainer.style.display = 'none'; // Esconde o container de arquivos
  conversionOptionsDisplay.style.display = 'none'; // Esconde a interface de configuração
  conversionSuccessDisplay.style.display = 'none'; // Esconde a tela de sucesso

  uploadedFilesContainer.innerHTML = ''; // Limpa os arquivos exibidos
  formatSelect.innerHTML = ''; // Limpa as opções de formato
  conversionResultDiv.innerHTML = '';
  finalDownloadLink.href = '#'; // Limpa o link de download

  uploadedFiles = []; // Reseta o array de arquivos
  availableFormats = new Set(); // Reseta os formatos disponíveis

  // Garante que o Dropzone esteja pronto para um novo upload
  myDropzone.removeAllFiles(true); // Limpa arquivos internos do Dropzone
  myDropzone.hiddenFileInput.value = null; // Reseta o input de arquivo
}

// Função para criar e adicionar a caixa de arquivo ao DOM
function addFileBoxToUI(fileData) {
  const fileBox = document.createElement('div');
  fileBox.classList.add('uploaded-file-box', 'd-flex', 'justify-content-between', 'align-items-center');
  fileBox.dataset.serverId = fileData.filename; // Armazena o ID do servidor para fácil remoção/conversão

  fileBox.innerHTML = `
    <span class="file-name-display text-truncate me-2">${fileData.originalName}</span>
    <button type="button" class="remove-file-btn btn-close" aria-label="Close"></button>
  `;

  uploadedFilesContainer.appendChild(fileBox);

  // Adiciona evento para o botão de remover
  fileBox.querySelector('.remove-file-btn').addEventListener('click', function() {
    removeFile(fileBox, fileData.filename);
  });
}

// Função para remover um arquivo da UI e da lista de arquivos
function removeFile(fileBoxElement, serverFileName) {
  fileBoxElement.remove(); // Remove o elemento HTML

  // Remove o arquivo do array `uploadedFiles`
  uploadedFiles = uploadedFiles.filter(file => file.filename !== serverFileName);

  // Reavaliar formatos disponíveis e visibilidade da UI
  updateConversionOptions();
  
  if (uploadedFiles.length === 0) {
    resetUI(); // Volta para o estado inicial se não houver mais arquivos
  }
}

// Função para atualizar as opções de conversão e a visibilidade da UI
function updateConversionOptions() {
  // Limpa as opções de formato existentes
  formatSelect.innerHTML = '';
  availableFormats.clear();

  // Coleta todas as opções de formato de todos os arquivos enviados
  uploadedFiles.forEach(fileData => {
    fileData.opcoes.forEach(option => availableFormats.add(option));
  });

  if (availableFormats.size > 0) {
    // Adiciona as opções de formato ao select, ordenando-as
    Array.from(availableFormats).sort().forEach(op => {
      const option = document.createElement("option");
      option.value = op;
      option.textContent = op;
      formatSelect.appendChild(option);
    });
    convertButton.disabled = false;
    conversionOptionsDisplay.style.display = 'block'; // Mostra as opções de conversão
  } else if (uploadedFiles.length > 0) {
    // Se há arquivos mas nenhuma opção de conversão comum
    formatSelect.innerHTML = '<option value="">Nenhuma opção comum disponível</option>';
    convertButton.disabled = true;
    conversionOptionsDisplay.style.display = 'block';
  } else {
    // Se não há arquivos, esconde as opções de conversão
    conversionOptionsDisplay.style.display = 'none';
  }
}


const myDropzone = new Dropzone(dropzoneForm, {
  url: "http://localhost:5000/upload",
  maxFiles: 8, // Limite de 8 arquivos
  autoProcessQueue: true,
  addRemoveLinks: false, // Gerenciamos a remoção manualmente
  dictDefaultMessage: "",
  previewsContainer: null, // Não queremos previews do Dropzone, vamos renderizar o nosso

  init: function () {
    const self = this;

    self.on("addedfile", function (file) {
      // Esconder Dropzone e mostrar o container de arquivos e a interface de configuração
      dropzoneForm.style.display = 'none';
      uploadedFilesContainer.style.display = 'block';
      conversionSuccessDisplay.style.display = 'none'; // Apenas para garantir que não está visível
      conversionResultDiv.innerHTML = ''; // Limpa mensagens de erro anteriores

      // O Dropzone já adiciona o arquivo à sua lista interna.
      // O sucesso do upload adicionará à nossa lista `uploadedFiles`.
    });

    self.on("success", function (file, response) {
      try {
        // Dropzone pode enviar string, então parse se necessário
        if (typeof response === "string") {
          response = JSON.parse(response);
        }

        if (response.success && response.filename && response.opcoes) {
          uploadedFiles.push(response); // Adiciona o arquivo à nossa lista
          addFileBoxToUI(response); // Adiciona o arquivo à UI

          updateConversionOptions(); // Atualiza as opções de conversão
          
        } else {
          conversionResultDiv.innerHTML = `<p class="text-danger">Erro no upload para ${file.name}: ${response.error || 'Resposta inválida do servidor.'}</p>`;
          // Se houver um erro no upload de um arquivo, Dropzone já o remove da fila.
          // Não chamamos resetUI aqui para não apagar outros uploads bem-sucedidos.
        }
      } catch (e) {
        console.error("Erro ao processar resposta do servidor para", file.name, ":", e);
        conversionResultDiv.innerHTML = `<p class="text-danger">Erro ao processar resposta do servidor para ${file.name}.</p>`;
      }
    });

    self.on("error", function(file, message) {
        console.error("Erro no upload para", file.name, ":", message);
        conversionResultDiv.innerHTML = `<p class="text-danger">Erro no upload para ${file.name}: ${message}</p>`;
        // Dropzone automaticamente remove arquivos que falham o upload.
        // Não removemos da nossa lista `uploadedFiles` aqui porque ele nunca foi adicionado com sucesso.
    });

    self.on("queuecomplete", function() {
        // Esta função é chamada quando todos os arquivos da fila foram processados (sucesso ou falha)
        // Você pode usar isso para fazer ajustes finais na UI ou habilitar o botão de conversão
        // Se a fila estiver vazia e não houver arquivos na lista, resetar a UI
        if (uploadedFiles.length === 0 && self.getQueuedFiles().length === 0 && self.getUploadingFiles().length === 0) {
            resetUI();
        }
    });
  }
});

// Event listener para o botão de Converter
convertButton.addEventListener("click", function() {
  if (uploadedFiles.length === 0) {
    conversionResultDiv.innerHTML = `<p class="text-danger">Nenhum arquivo para converter.</p>`;
    return;
  }

  const formato = formatSelect.value;
  if (!formato) {
    conversionResultDiv.innerHTML = `<p class="text-danger">Selecione um formato de destino.</p>`;
    return;
  }

  convertButton.disabled = true;
  conversionResultDiv.innerHTML = `<p class="text-info">Convertendo todos os arquivos...</p>`;

  let conversionsCompleted = 0;
  let successfulConversions = 0;
  let failedConversions = 0;
  let downloadLinks = []; // Para armazenar todos os links de download

  uploadedFiles.forEach((fileData, index) => {
    fetch("http://localhost:5000/convert", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        filename: fileData.filename, // Nome do arquivo no servidor
        formato_destino: formato
      })
    })
    .then(res => res.json())
    .then(data => {
      conversionsCompleted++;
      if (data.success && data.download_url) {
        successfulConversions++;
        const baseURL = "http://localhost:5000";
        downloadLinks.push(`${baseURL}${data.download_url}`); // Adiciona o link de download
      } else {
        failedConversions++;
        console.error(`Erro na conversão de ${fileData.originalName}:`, data.error || 'Desconhecido');
      }
    })
    .catch((error) => {
      conversionsCompleted++;
      failedConversions++;
      console.error(`Erro de rede na conversão de ${fileData.originalName}:`, error);
    })
    .finally(() => {
      // Quando todas as conversões estiverem concluídas
      if (conversionsCompleted === uploadedFiles.length) {
        convertButton.disabled = false;

        if (successfulConversions > 0) {
          // Esconder a interface de conversão
          conversionOptionsDisplay.style.display = 'none';
          uploadedFilesContainer.style.display = 'none';
          // Mostrar a tela de sucesso
          conversionSuccessDisplay.style.display = 'flex';

          // Se houver apenas um arquivo convertido com sucesso, o link de download é direto
          if (successfulConversions === 1 && downloadLinks.length === 1) {
            finalDownloadLink.href = downloadLinks[0];
            finalDownloadLink.textContent = "Fazer Download";
            finalDownloadLink.style.display = 'block'; // Mostra o botão de download
          } else {
            // Para múltiplos arquivos, criar um ZIP ou oferecer download individual (mais complexo)
            // Por simplicidade, vamos apenas dizer que a conversão foi feita e o usuário pode carregar outro
            // Ou, se o backend for modificado para gerar um ZIP, este link seria para o ZIP.
            // Para este exemplo, não estamos gerando um ZIP, então vamos esconder o download.
            finalDownloadLink.style.display = 'none'; // Esconde o botão de download se forem múltiplos arquivos
            conversionResultDiv.innerHTML = `<p class="text-success">Conversão finalizada para ${successfulConversions} de ${uploadedFiles.length} arquivos. ${failedConversions > 0 ? `(${failedConversions} falhas)` : ''}</p>`;
            // Resetamos a UI para que o usuário possa fazer novas conversões
            // O usuário pode clicar em "Carregar outro arquivo" ou você pode forçar o reset aqui.
            // resetUI(); // Descomente se quiser resetar automaticamente
          }
        } else {
          conversionResultDiv.innerHTML = `<p class="text-danger">Todas as conversões falharam.</p>`;
        }
      }
    });
  });
});

// Event listener para o botão "Carregar outro arquivo" na tela de sucesso
loadAnotherFileBtn.addEventListener("click", function() {
  resetUI(); // Volta para a tela inicial
});

// Inicializa a UI no estado correto ao carregar a página
resetUI();